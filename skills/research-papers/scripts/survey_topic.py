#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_VENUES = ["CVPR", "ICCV", "ECCV", "ICML", "ICLR", "NeurIPS"]
DEFAULT_VENUE_SCAN_LIMIT = 5000
DEFAULT_ARXIV_LIMIT = 200
DEFAULT_MIN_TOTAL_PAPERS = 200
DEFAULT_PAPERS_PER_TOPIC = 50
DEFAULT_MIN_CANDIDATES_PER_TOPIC = 120
DEFAULT_MAX_WORKERS = 8
DEFAULT_LOOKBACK_YEARS = 3
DEFAULT_BOOTSTRAP_LIMIT = 8
SCHEMA_VERSION = "2.0"
SOURCE_PRIORITY = {"venue": 2, "arxiv": 1}
CACHE_MODE_OFF = "off"
CACHE_MODE_READ_WRITE = "read-write"
CACHE_MODE_READ_ONLY = "read-only"
CACHE_KEY_NAMESPACE = "research-papers-v2-total-first"
SELECTION_STATUS_OK = "ok"
SELECTION_STATUS_BLOCKED = "blocked_insufficient_candidates"
REPO_ROOT = Path(__file__).resolve().parents[3]
PAPERS_COOL_SCRIPT = REPO_ROOT / "skills" / "papers-cool-venue-reader" / "scripts" / "papers_cool.py"

STOPWORDS = {
    "a",
    "an",
    "and",
    "approach",
    "approaches",
    "application",
    "applications",
    "benchmark",
    "benchmarks",
    "based",
    "dataset",
    "datasets",
    "evaluation",
    "for",
    "framework",
    "frameworks",
    "in",
    "into",
    "large",
    "learning",
    "method",
    "methods",
    "model",
    "models",
    "of",
    "on",
    "study",
    "system",
    "systems",
    "task",
    "tasks",
    "the",
    "through",
    "to",
    "towards",
    "using",
    "with",
}

GENERIC_DIMENSIONS = [
    {
        "name": "问题设定与核心方法",
        "modifiers": ["problem formulation", "method", "framework", "approach", "taxonomy"],
        "rationale": "先把问题边界、代表方法和主线起点说明白。",
    },
    {
        "name": "表示、架构与关键机制",
        "modifiers": ["representation", "architecture", "model", "mechanism", "module"],
        "rationale": "聚焦方法内部的表示、结构设计和关键机制。",
    },
    {
        "name": "训练、优化与适配策略",
        "modifiers": ["training", "optimization", "adaptation", "alignment", "learning strategy"],
        "rationale": "梳理训练目标、优化方式和适配策略的差异。",
    },
    {
        "name": "评测基准与应用场景",
        "modifiers": ["benchmark", "dataset", "evaluation", "application", "case study"],
        "rationale": "解释 benchmark、实验设置和应用落点。",
    },
]

THEORY_DIMENSION = {
    "name": "理论分析与问题边界",
    "modifiers": ["theory", "analysis", "bound", "proof", "assumption"],
    "rationale": "如果用户主题本身偏理论，就把理论边界单独成章。",
}


@dataclass
class SubtopicSpec:
    name: str
    modifiers: list[str]
    rationale: str


@dataclass
class TopicPlan:
    main_topic: str
    aliases: list[str]
    keywords: list[str]
    subtopics: list[SubtopicSpec]


@dataclass
class CacheConfig:
    mode: str = CACHE_MODE_OFF
    cache_dir: Path | None = None
    delete_after_run: bool = False


CACHE_CONFIG = CacheConfig()


def configure_cache(cache_dir: str | None, mode: str, delete_after_run: bool) -> None:
    path = Path(cache_dir).expanduser() if cache_dir else None
    if path and mode != CACHE_MODE_OFF:
        path.mkdir(parents=True, exist_ok=True)
    global CACHE_CONFIG
    CACHE_CONFIG = CacheConfig(mode=mode, cache_dir=path, delete_after_run=delete_after_run)


def cache_key(args: list[str]) -> str:
    return hashlib.sha1(json.dumps([CACHE_KEY_NAMESPACE, *args], ensure_ascii=False).encode("utf-8")).hexdigest()


def cache_path_for(args: list[str]) -> Path | None:
    if CACHE_CONFIG.mode == CACHE_MODE_OFF or CACHE_CONFIG.cache_dir is None:
        return None
    return CACHE_CONFIG.cache_dir / f"{cache_key(args)}.json"


def run_cmd(args: list[str], *, cache_args: list[str] | None = None) -> str:
    cache_lookup_args = cache_args or args
    cache_path = cache_path_for(cache_lookup_args)
    if cache_path and cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    if cache_path and CACHE_CONFIG.mode == CACHE_MODE_READ_ONLY:
        raise RuntimeError(
            f"cache miss for command: {' '.join(cache_lookup_args)}; expected cached file at {cache_path}"
        )

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        joined = stderr or stdout or f"command failed: {' '.join(args)}"
        if cache_path:
            joined = (
                f"{joined}\n未命中本地缓存：{cache_path}\n"
                "如果当前环境无法联网，请先在可联网环境预热同一个 cache-dir，再用 --cache-mode read-only 复用。"
            )
        raise RuntimeError(joined)
    output = result.stdout
    if cache_path and CACHE_CONFIG.mode == CACHE_MODE_READ_WRITE:
        cache_path.write_text(output, encoding="utf-8")
    return output


def run_json_cmd(args: list[str], *, cache_args: list[str] | None = None) -> Any:
    return json.loads(run_cmd(args, cache_args=cache_args))


def papers_cool_args(*args: str) -> tuple[list[str], list[str]]:
    exec_args = [sys.executable, str(PAPERS_COOL_SCRIPT), *args]
    cache_args = ["papers_cool.py", *args]
    return exec_args, cache_args


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9-]+", normalize_text(text))


def compact(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def unique_keep_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        value = compact(item)
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def current_year() -> int:
    return date.today().year


def default_venue_years(lookback_years: int = DEFAULT_LOOKBACK_YEARS) -> list[int]:
    year = current_year()
    return [year - offset for offset in range(max(0, lookback_years) + 1)]


def default_arxiv_date_from(lookback_years: int = DEFAULT_LOOKBACK_YEARS) -> str:
    return f"{current_year() - max(0, lookback_years):04d}-01-01"


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def is_acronym(text: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9-]{2,10}", compact(text)))


def latin_token_count(text: str) -> int:
    return len(tokenize(text))


def split_cli_csv(raw: str | None) -> list[str]:
    return [compact(piece) for piece in (raw or "").split(",") if compact(piece)]


def derive_english_variants(alias: str) -> list[str]:
    alias = compact(alias)
    if not alias:
        return []
    out = [alias]
    english_chunks = re.findall(r"[A-Za-z][A-Za-z0-9\-]*(?: [A-Za-z0-9\-]+)+", alias)
    out.extend(english_chunks)
    for chunk in english_chunks:
        tokens = chunk.split()
        if len(tokens) >= 2 and is_acronym(tokens[-1]):
            out.append(" ".join(tokens[:-1]))
    return unique_keep_order(out)


def extract_topic_aliases(topic: str) -> list[str]:
    aliases = [compact(topic)]
    aliases.extend(re.findall(r"[\u4e00-\u9fff]{2,}", topic))
    aliases.extend(re.findall(r"[A-Za-z][A-Za-z0-9\-]*(?: [A-Za-z0-9\-]+)+", topic))
    aliases.extend(re.findall(r"\b[A-Z]{2,10}\b", topic))

    inside_parens = re.findall(r"[（(]([^()（）]+)[）)]", topic)
    aliases.extend(inside_parens)

    expanded = []
    for alias in aliases:
        expanded.extend(derive_english_variants(alias))
    return unique_keep_order(expanded)


def has_strong_latin_alias(aliases: list[str]) -> bool:
    return any(latin_token_count(alias) >= 2 or is_acronym(alias) for alias in aliases)


def phrase_candidates_from_text(text: str) -> list[str]:
    tokens = tokenize(text)
    phrases = []
    for n in (3, 2):
        for index in range(len(tokens) - n + 1):
            chunk = tokens[index : index + n]
            if any(token in STOPWORDS for token in chunk):
                continue
            phrases.append(" ".join(chunk))
    return phrases


def infer_aliases_from_search(topic: str, limit: int = DEFAULT_BOOTSTRAP_LIMIT) -> list[str]:
    try:
        payload = search_deepxiv(topic, f"{current_year() - 10:04d}-01-01", limit)
    except Exception:
        return []

    counter: Counter[str] = Counter()
    for item in payload.get("results", [])[:limit]:
        title = item.get("title", "")
        counter.update(phrase_candidates_from_text(title))

    aliases = [phrase for phrase, freq in counter.most_common(8) if freq >= 2]
    return unique_keep_order(aliases[:4])


def infer_keywords(topic: str, aliases: list[str]) -> list[str]:
    keywords = list(aliases)
    if not has_strong_latin_alias(aliases):
        keywords.extend(infer_aliases_from_search(topic))

    if keywords:
        base = keywords[0]
        if latin_token_count(base) >= 2 or contains_cjk(base):
            keywords.extend([f"{base} benchmark", f"{base} dataset", f"{base} survey"])
        if is_acronym(base):
            keywords.extend([f"{base} benchmark", f"{base} dataset"])
    return unique_keep_order(keywords)[:16]


def infer_subtopics(topic: str, aliases: list[str], explicit_subtopics: list[str] | None = None) -> list[SubtopicSpec]:
    if explicit_subtopics:
        return [SubtopicSpec(name=name, modifiers=derive_modifiers_from_name(name), rationale="用户显式覆盖的子方向。") for name in explicit_subtopics]

    lowered = normalize_text(topic)
    dimensions = list(GENERIC_DIMENSIONS)
    if any(word in lowered for word in ["theory", "analysis", "proof", "bound", "理论", "分析"]):
        dimensions[0] = THEORY_DIMENSION

    return [SubtopicSpec(**item) for item in dimensions[:4]]


def derive_modifiers_from_name(name: str) -> list[str]:
    lowered = normalize_text(name)
    if any(word in lowered for word in ["benchmark", "dataset", "evaluation", "评测", "数据集", "应用"]):
        return ["benchmark", "dataset", "evaluation", "application"]
    if any(word in lowered for word in ["theory", "analysis", "proof", "bound", "理论", "分析"]):
        return ["theory", "analysis", "bound", "assumption"]
    if any(word in lowered for word in ["train", "training", "optimization", "adaptation", "适配", "训练", "优化"]):
        return ["training", "optimization", "adaptation", "alignment"]
    if any(word in lowered for word in ["representation", "architecture", "model", "机制", "架构", "表示"]):
        return ["representation", "architecture", "model", "mechanism"]
    return ["problem formulation", "method", "framework", "approach"]


def parse_topic(
    user_prompt: str,
    explicit_aliases: list[str] | None = None,
    explicit_subtopics: list[str] | None = None,
    explicit_keywords: list[str] | None = None,
) -> TopicPlan:
    topic = compact(user_prompt)
    aliases = [topic]
    if explicit_aliases:
        aliases.extend(explicit_aliases)
    else:
        aliases.extend(extract_topic_aliases(topic))
        if not has_strong_latin_alias(aliases):
            aliases.extend(infer_aliases_from_search(topic))
    aliases = unique_keep_order(aliases)
    keywords = explicit_keywords or infer_keywords(topic, aliases)
    subtopics = infer_subtopics(topic, aliases, explicit_subtopics)
    return TopicPlan(
        main_topic=topic,
        aliases=aliases[:12],
        keywords=unique_keep_order(keywords)[:16],
        subtopics=subtopics[:5],
    )


def is_high_signal_query(query: str) -> bool:
    query = compact(query)
    if not query:
        return False
    if contains_cjk(query):
        return True
    if is_acronym(query):
        return True
    return latin_token_count(query) >= 2 or len(query) >= 12


def prioritized_aliases(aliases: list[str]) -> list[str]:
    return sorted(
        unique_keep_order(aliases),
        key=lambda item: (
            is_acronym(item),
            contains_cjk(item),
            -latin_token_count(item),
            -len(item),
        ),
    )


def has_strong_latin_phrase(aliases: list[str]) -> bool:
    return any(latin_token_count(alias) >= 2 and not is_acronym(alias) for alias in aliases)


def query_ready_aliases(aliases: list[str]) -> list[str]:
    ordered = prioritized_aliases(aliases)
    strong_latin = has_strong_latin_phrase(ordered)
    filtered = []
    for alias in ordered:
        if strong_latin and contains_cjk(alias):
            continue
        if strong_latin and is_acronym(alias) and len(compact(alias)) <= 3:
            continue
        filtered.append(alias)
    return filtered or ordered


def match_ready_aliases(aliases: list[str]) -> list[str]:
    ordered = unique_keep_order(aliases)
    strong_descriptive = any(
        (latin_token_count(alias) >= 2 and not is_acronym(alias)) or contains_cjk(alias)
        for alias in ordered
    )
    filtered = []
    for alias in ordered:
        if strong_descriptive and is_acronym(alias) and len(compact(alias)) <= 3:
            continue
        filtered.append(alias)
    return filtered or ordered


def build_topic_queries(plan: TopicPlan, subtopic: SubtopicSpec) -> list[str]:
    queries = []
    aliases = query_ready_aliases(plan.aliases + plan.keywords)
    for alias in aliases[:8]:
        if is_high_signal_query(alias):
            queries.append(alias)
        for modifier in subtopic.modifiers:
            combo = f"{alias} {modifier}".strip()
            if is_high_signal_query(combo):
                queries.append(combo)
    return unique_keep_order(queries)[:24]


@lru_cache(maxsize=None)
def load_venue_feed(venue: str, year: int, scan_limit: int) -> list[dict[str, Any]]:
    exec_args, cache_args = papers_cool_args(
        "feed",
        venue,
        "--year",
        str(year),
        "--limit",
        str(scan_limit),
        "--json",
    )
    return run_json_cmd(exec_args, cache_args=cache_args)


@lru_cache(maxsize=None)
def load_papers_cool_paper(slug: str) -> dict[str, Any]:
    exec_args, cache_args = papers_cool_args("paper", slug, "--json")
    return run_json_cmd(exec_args, cache_args=cache_args)


@lru_cache(maxsize=None)
def load_deepxiv_head(arxiv_id: str) -> dict[str, Any]:
    return run_json_cmd(["deepxiv", "paper", arxiv_id, "--head", "-f", "json"])


@lru_cache(maxsize=None)
def search_deepxiv(query: str, date_from: str, limit: int) -> dict[str, Any]:
    args = ["deepxiv", "search", query, "--limit", str(limit), "--format", "json"]
    if compact(date_from):
        args.extend(["--date-from", date_from])
    return run_json_cmd(args)


def overlap_score(text: str, query: str) -> int:
    a = {token for token in tokenize(text) if token not in STOPWORDS}
    b = {token for token in tokenize(query) if token not in STOPWORDS}
    return len(a & b)


def topic_alias_score(title: str, text: str, aliases: list[str]) -> int:
    title_lower = normalize_text(title)
    text_lower = normalize_text(text)
    best = 0
    for alias in match_ready_aliases(aliases):
        alias_clean = compact(alias)
        alias_lower = normalize_text(alias_clean)
        if not alias_lower:
            continue
        if is_acronym(alias_clean):
            if re.search(rf"\b{re.escape(alias_clean)}\b", title):
                best = max(best, 12)
                continue
            if re.search(rf"\b{re.escape(alias_clean)}\b", text):
                best = max(best, 8)
                continue
        if contains_cjk(alias_clean) and alias_clean in text:
            best = max(best, 12)
            continue
        if alias_lower in title_lower:
            best = max(best, 12)
            continue
        if alias_lower in text_lower:
            best = max(best, 10)
            continue
        alias_tokens = [token for token in tokenize(alias_clean) if token not in STOPWORDS]
        overlap = overlap_score(text, alias_clean)
        min_overlap = len(alias_tokens) if len(alias_tokens) >= 2 else 1
        if overlap >= min_overlap:
            best = max(best, overlap * 2)
    return best


def query_score(text: str, query: str) -> int:
    lowered = normalize_text(text)
    normalized_query = normalize_text(query)
    score = overlap_score(text, query)
    if normalized_query and normalized_query in lowered:
        score += 8
    return score


def keyword_hits(title: str, text: str, aliases: list[str], queries: list[str]) -> tuple[list[str], int]:
    topic_score = topic_alias_score(title, text, aliases)
    if topic_score <= 0:
        return [], 0

    matched_queries = []
    best = topic_score
    for query in queries:
        score = query_score(text, query)
        if score > 0:
            matched_queries.append(query)
            best = max(best, topic_score + score)
    return matched_queries or aliases[:1], best


def fetch_venue_candidates(
    plan: TopicPlan,
    subtopic: SubtopicSpec,
    years: list[int],
    venues: list[str],
    scan_limit: int,
    max_workers: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    queries = build_topic_queries(plan, subtopic)
    scanned_records = 0
    candidates: list[dict[str, Any]] = []
    errors = []
    tasks = {}
    worker_count = max(1, min(max_workers, len(venues) * len(years)))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        for venue in venues:
            for year in years:
                tasks[executor.submit(load_venue_feed, venue, year, scan_limit)] = (venue, year)

        for future in as_completed(tasks):
            venue, year = tasks[future]
            try:
                records = future.result()
            except Exception as exc:
                errors.append(f"{venue} {year}: {exc}")
                continue
            scanned_records += len(records)
            for record in records:
                title = record.get("title", "")
                authors = " ".join(record.get("authors") or [])
                keywords = " ".join(record.get("keywords") or [])
                text = " ".join([title, record.get("summary", ""), authors, keywords])
                matched_queries, best_score = keyword_hits(title, text, plan.aliases + plan.keywords, queries)
                slug = record.get("slug") or str(record.get("papers_cool_url", "")).rstrip("/").split("/")[-1]
                if matched_queries and slug:
                    candidates.append(
                        {
                            **record,
                            "slug": slug,
                            "source": "venue",
                            "source_id": slug,
                            "matched_queries": matched_queries,
                            "query_hit_count": len(matched_queries),
                            "best_score": best_score,
                            "published": f"{venue} {year}",
                        }
                    )

    if not candidates and errors:
        raise RuntimeError(f"Venue 检索失败，示例错误：{errors[0]}")

    dedup = {}
    ordered = sorted(
        candidates,
        key=lambda item: (item.get("best_score", 0), item.get("query_hit_count", 0), item.get("year") or 0),
        reverse=True,
    )
    for item in ordered:
        dedup.setdefault(item["source_id"], item)
    stats = {
        "queries": queries,
        "venues": venues,
        "years": years,
        "records_scanned": scanned_records,
        "matches": len(dedup),
    }
    return list(dedup.values()), stats


def fetch_arxiv_candidates(
    plan: TopicPlan,
    subtopic: SubtopicSpec,
    date_from: str,
    limit: int,
    max_workers: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    queries = build_topic_queries(plan, subtopic)
    candidates = []
    errors = []
    tasks = {}
    worker_count = max(1, min(max_workers, len(queries) or 1))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        for query in queries:
            tasks[executor.submit(search_deepxiv, query, date_from, limit)] = query

        for future in as_completed(tasks):
            query = tasks[future]
            try:
                payload = future.result()
            except Exception as exc:
                errors.append(f"{query}: {exc}")
                continue
            for item in payload.get("results", []):
                title = item.get("title", "")
                text = " ".join([title, item.get("abstract", "")])
                matched_queries, best_score = keyword_hits(title, text, plan.aliases + plan.keywords, [query])
                if best_score > 0:
                    arxiv_id = item.get("arxiv_id", item.get("id", ""))
                    candidates.append(
                        {
                            **item,
                            "arxiv_id": arxiv_id,
                            "source": "arxiv",
                            "source_id": arxiv_id,
                            "query": query,
                            "matched_queries": matched_queries,
                            "query_hit_count": len(matched_queries),
                            "best_score": best_score,
                        }
                    )

    if not candidates and errors:
        raise RuntimeError(f"ArXiv 检索失败，示例错误：{errors[0]}")

    dedup = {}
    ordered = sorted(
        candidates,
        key=lambda item: (item.get("best_score", 0), item.get("publish_at", ""), item.get("citations", 0)),
        reverse=True,
    )
    for item in ordered:
        dedup.setdefault(item["source_id"], item)
    stats = {
        "queries": queries,
        "date_from": date_from,
        "limit": limit,
        "matches": len(dedup),
    }
    return list(dedup.values()), stats


def candidate_key(item: dict[str, Any]) -> str:
    normalized_title = re.sub(r"[^a-z0-9]+", "", normalize_text(item.get("title", "")))
    if normalized_title:
        return normalized_title
    return f"{item.get('source', 'paper')}::{item.get('source_id', item.get('slug', item.get('arxiv_id', 'unknown')))}"


def candidate_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    title_key = normalize_text(item.get("title", ""))
    source_id = compact(str(item.get("source_id", item.get("slug", item.get("arxiv_id", "")))))
    return (
        item.get("best_score", 0),
        item.get("query_hit_count", 0),
        SOURCE_PRIORITY.get(item.get("source", ""), 0),
        item.get("citations", 0),
        item.get("publish_at", ""),
        item.get("year") or 0,
        title_key,
        source_id,
    )


def dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dedup = {}
    for item in sorted(candidates, key=candidate_sort_key, reverse=True):
        dedup.setdefault(candidate_key(item), item)
    return list(dedup.values())


def append_unique_until(selected: list[dict[str, Any]], used_keys: set[str], candidates: list[dict[str, Any]], target_count: int) -> None:
    for item in candidates:
        if len(selected) >= target_count:
            return
        key = candidate_key(item)
        if key in used_keys:
            continue
        used_keys.add(key)
        selected.append(item)


def select_topic_candidates(
    venue_candidates: list[dict[str, Any]],
    arxiv_candidates: list[dict[str, Any]],
    target_count: int,
) -> list[dict[str, Any]]:
    if target_count <= 0:
        return []

    venue_ranked = sorted(dedupe_candidates(venue_candidates), key=candidate_sort_key, reverse=True)
    arxiv_ranked = sorted(dedupe_candidates(arxiv_candidates), key=candidate_sort_key, reverse=True)
    combined_ranked = sorted(dedupe_candidates(venue_candidates + arxiv_candidates), key=candidate_sort_key, reverse=True)

    venue_target = min(len(venue_ranked), max(target_count // 2, round(target_count * 0.6)))
    arxiv_target = min(len(arxiv_ranked), max(0, target_count - venue_target))

    selected: list[dict[str, Any]] = []
    used_keys: set[str] = set()
    append_unique_until(selected, used_keys, venue_ranked, venue_target)
    append_unique_until(selected, used_keys, arxiv_ranked, len(selected) + arxiv_target)
    append_unique_until(selected, used_keys, combined_ranked, target_count)
    return selected


def derive_topic_targets(
    candidate_pool_sizes: list[int],
    min_total_papers: int,
    per_topic_floor: int | None,
) -> tuple[list[int], list[int]]:
    if not candidate_pool_sizes:
        return [], []

    topic_count = len(candidate_pool_sizes)
    base_floor = max(per_topic_floor or 0, min_total_papers // topic_count)
    base_targets = [base_floor for _ in candidate_pool_sizes]
    targets = [min(size, base_floor) for size in candidate_pool_sizes]
    desired_total = max(min_total_papers, sum(base_targets))
    ranked_indices = sorted(
        range(topic_count),
        key=lambda index: (candidate_pool_sizes[index], -index),
        reverse=True,
    )

    remaining = max(0, desired_total - sum(targets))
    while remaining > 0:
        progressed = False
        for index in ranked_indices:
            if remaining <= 0:
                break
            if targets[index] >= candidate_pool_sizes[index]:
                continue
            targets[index] += 1
            remaining -= 1
            progressed = True
        if not progressed:
            break

    return targets, base_targets


def clean_venue_name(name: str) -> str:
    cleaned = compact(name).replace("Subjects :", "")
    cleaned = re.sub(r"\s+-.*$", "", cleaned)
    return cleaned.strip()


def format_venue_label(venue: str, year: str | int | None) -> str:
    cleaned = clean_venue_name(venue)
    match = re.match(r"([A-Za-z]+)\.(\d{4})$", cleaned)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    if year and str(year) not in cleaned:
        return f"{cleaned} {year}".strip()
    return cleaned or "-"


def infer_arxiv_month(arxiv_id: str, publish_at: str | None) -> str:
    if publish_at:
        return publish_at[:7]
    match = re.match(r"(\d{2})(\d{2})\.", arxiv_id or "")
    if not match:
        return ""
    year = 2000 + int(match.group(1))
    month = int(match.group(2))
    return f"{year:04d}-{month:02d}"


def format_arxiv_label(arxiv_id: str, publish_at: str | None) -> str:
    month = infer_arxiv_month(arxiv_id, publish_at)
    return f"arXiv {month}" if month else "arXiv"


def normalize_author_list(authors: Any) -> str:
    names = []
    for author in authors or []:
        if isinstance(author, dict):
            name = compact(author.get("name", ""))
        else:
            name = compact(str(author))
        if name:
            names.append(name)
    return ", ".join(names)


def normalize_keyword_list(raw_keywords: Any) -> list[str]:
    if isinstance(raw_keywords, list):
        items = raw_keywords
    else:
        items = re.split(r"[,;/|]", str(raw_keywords or ""))
    cleaned = []
    for item in items:
        keyword = compact(str(item))
        if not keyword:
            continue
        if latin_token_count(keyword) == 1 and normalize_text(keyword) in STOPWORDS:
            continue
        cleaned.append(keyword)
    return unique_keep_order(cleaned)


def extract_paper_concepts(text: str, keywords: list[str], topic_keywords: list[str]) -> list[str]:
    candidates = normalize_keyword_list(keywords)
    if candidates:
        return candidates[:4]

    phrase_counter: Counter[str] = Counter()
    for phrase in phrase_candidates_from_text(text):
        if phrase in STOPWORDS:
            continue
        phrase_counter[phrase] += 1
    ordered = [phrase for phrase, _ in phrase_counter.most_common(8)]
    if ordered:
        return ordered[:4]

    fallback = [keyword for keyword in topic_keywords if is_high_signal_query(keyword)]
    return fallback[:3]


def infer_paper_role(text: str) -> str:
    lowered = normalize_text(text)
    if any(term in lowered for term in ["survey", "review", "taxonomy", "overview"]):
        return "综述与框架梳理"
    if any(term in lowered for term in ["benchmark", "dataset", "leaderboard", "corpus", "evaluation protocol"]):
        return "基准与数据工作"
    if any(term in lowered for term in ["theory", "theoretical", "bound", "proof", "analysis of", "assumption"]):
        return "理论分析工作"
    if any(term in lowered for term in ["system", "architecture", "pipeline", "framework", "module"]):
        return "系统与架构工作"
    return "方法工作"


def stage_hint(role: str) -> str:
    mapping = {
        "综述与框架梳理": "概念边界与研究脉络",
        "基准与数据工作": "任务定义与评测协议",
        "理论分析工作": "理论解释与问题边界",
        "系统与架构工作": "系统组织与模块接口",
        "方法工作": "核心机制设计",
    }
    return mapping.get(role, "关键机制设计")


def build_analysis(subtopic: str, text: str, concepts: list[str], role: str) -> str:
    focus = "、".join(concepts[:3]) if concepts else subtopic
    stage = stage_hint(role)
    sentences = [
        f"这篇论文主要落在“{subtopic}”这一组。结合标题、摘要和可用 TLDR，它围绕 {focus} 展开，整体更像一篇{role}。",
        f"如果把它放回整个主题里看，它补的是 {stage} 这一环，而不是单纯替换一个 backbone。",
    ]
    if role == "基准与数据工作":
        sentences.append("它更重要的价值通常在于把数据、任务和比较协议固定下来，方便后续方法在统一设置下比较。")
    elif role == "理论分析工作":
        sentences.append("这类论文真正值得读的地方，往往是它如何解释方法为什么有效、什么时候会失效。")
    elif role == "系统与架构工作":
        sentences.append("这类工作更值得关注的是模块之间如何分工，以及这种组织方式是否能被别的任务复用。")
    elif role == "综述与框架梳理":
        sentences.append("如果把它纳入综述，更适合作为组织概念边界和方法谱系的参考点。")
    else:
        sentences.append("从综述结构上看，它更适合作为这个子方向里的代表方法，用来说明该方向当前的主流机制。")
    return "".join(sentences)


def build_table_summary(concepts: list[str], role: str) -> str:
    focus = "、".join(concepts[:2]) if concepts else role
    return f"聚焦{focus}的{role}"


def build_importance_note(subtopic: str, concepts: list[str], role: str) -> str:
    focus = concepts[0] if concepts else "关键机制"
    return (
        f"我更看重它的地方，不是单次指标，而是它把“{focus}”这一环讲得更清楚；"
        f"放在“{subtopic}”里看，这种清晰度决定了它能否作为后续阅读或比较的锚点。"
    )


def build_example(subtopic: str, concepts: list[str], role: str) -> str:
    focus = concepts[0] if concepts else subtopic
    if role == "基准与数据工作":
        return f"例如，你想比较不同方法是否真的在“{focus}”相关问题上有提升，这类工作会先把任务、数据和评分标准搭好。"
    if role == "理论分析工作":
        return f"例如，一批方法都声称能改进“{focus}”，这类论文会先解释这些方法在什么条件下成立、在哪些设置下会失效。"
    if role == "系统与架构工作":
        return f"例如，把“{focus}”拆成几个相互配合的模块后，系统可能更容易扩展到别的任务或场景。"
    if role == "综述与框架梳理":
        return f"例如，你第一次进入“{subtopic}”这个子方向时，这类论文能帮你先把概念边界、代表方法和主线关系理顺。"
    return f"例如，先把“{focus}”这一层机制做扎实，再看它如何影响下游任务表现，这通常就是这类方法论文的核心阅读路径。"


def safe_label(text: str, fallback: str) -> str:
    cleaned = compact(text) or fallback
    cleaned = cleaned.replace('"', "'").replace("\n", " ")
    return cleaned[:32]


def build_mermaid(subtopic: str, concepts: list[str], role: str) -> str:
    problem = safe_label(subtopic, "问题")
    mechanism = safe_label(" / ".join(concepts[:2]), role)
    stage = safe_label(stage_hint(role), "位置")
    value = safe_label(role, "角色")
    return "\n".join(
        [
            "flowchart LR",
            f'    A["问题场景: {problem}"] --> B["关键机制: {mechanism}"]',
            f'    B --> C["作用位置: {stage}"]',
            f'    C --> D["论文角色: {value}"]',
        ]
    )


def summarize_venue_paper(data: dict[str, Any], subtopic: SubtopicSpec, topic_keywords: list[str]) -> dict[str, Any]:
    title = data.get("title", "")
    summary = data.get("summary", "")
    keywords = normalize_keyword_list(data.get("keywords") or [])
    text = " ".join([title, summary, " ".join(keywords)])
    concepts = extract_paper_concepts(text, keywords, topic_keywords)
    role = infer_paper_role(text)
    analysis = build_analysis(subtopic.name, text, concepts, role)
    paper_id = compact(data.get("slug") or data.get("paper_id") or title)
    access_url = data.get("official_url") or data.get("papers_cool_url", "")
    pdf_url = data.get("pdf_url") or data.get("official_pdf_url") or data.get("pdf") or ""
    evidence_status = "abstract_only" if compact(summary) else "metadata_only"
    evidence_note = "基于 papers.cool 提供的题目、摘要和元数据自动整理，未直接核验 PDF 正文。"
    return {
        "paper_id": paper_id,
        "title": title,
        "authors": normalize_author_list(data.get("authors", [])),
        "venue": clean_venue_name(data.get("venue", "")),
        "year": str(data.get("year", "")),
        "published": format_venue_label(data.get("venue", ""), data.get("year", "")),
        "abstract_summary": analysis,
        "analysis": analysis,
        "table_summary": build_table_summary(concepts, role),
        "insight": build_importance_note(subtopic.name, concepts, role),
        "example": build_example(subtopic.name, concepts, role),
        "paper_url": access_url,
        "access_url": access_url,
        "pdf_url": pdf_url,
        "url": access_url,
        "source": "venue",
        "role": role,
        "keywords": concepts,
        "diagram": build_mermaid(subtopic.name, concepts, role),
        "evidence_basis": "papers.cool metadata + abstract",
        "evidence_status": evidence_status,
        "evidence_note": evidence_note,
    }


def summarize_arxiv_paper(item: dict[str, Any], subtopic: SubtopicSpec, topic_keywords: list[str]) -> dict[str, Any]:
    arxiv_id = item.get("arxiv_id", item.get("id", ""))
    head = load_deepxiv_head(arxiv_id)
    title = head.get("title", item.get("title", "")) or item.get("title", "")
    abstract = head.get("abstract", item.get("abstract", "")) or item.get("abstract", "")
    tldr = head.get("tldr") or ""
    section_tldrs = " ".join((section.get("tldr") or "") for section in head.get("sections", [])[:3])
    keywords = normalize_keyword_list(head.get("keywords") or [])
    text = " ".join([title, abstract, tldr, section_tldrs, " ".join(keywords)])
    concepts = extract_paper_concepts(text, keywords, topic_keywords)
    role = infer_paper_role(text)
    authors = normalize_author_list(head.get("authors", []))
    publish_at = head.get("publish_at", item.get("publish_at", ""))
    analysis = build_analysis(subtopic.name, text, concepts, role)
    access_url = f"https://arxiv.org/abs/{arxiv_id}"
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if compact(arxiv_id) else ""
    evidence_status = "abstract_only" if compact(abstract) or compact(tldr) or compact(section_tldrs) else "metadata_only"
    evidence_note = "基于 deepxiv head、摘要和 section TLDR 自动整理，未直接通读 PDF 正文。"
    return {
        "paper_id": compact(arxiv_id or title),
        "title": title,
        "authors": authors,
        "venue": "arXiv",
        "year": infer_arxiv_month(arxiv_id, publish_at)[:4],
        "published": format_arxiv_label(arxiv_id, publish_at),
        "abstract_summary": analysis,
        "analysis": analysis,
        "table_summary": build_table_summary(concepts, role),
        "insight": build_importance_note(subtopic.name, concepts, role),
        "example": build_example(subtopic.name, concepts, role),
        "paper_url": access_url,
        "access_url": access_url,
        "pdf_url": pdf_url,
        "url": access_url,
        "source": "arxiv",
        "role": role,
        "keywords": concepts,
        "diagram": build_mermaid(subtopic.name, concepts, role),
        "evidence_basis": "deepxiv head + abstract + section TLDRs",
        "evidence_status": evidence_status,
        "evidence_note": evidence_note,
    }


def summarize_candidate(candidate: dict[str, Any], subtopic: SubtopicSpec, topic_keywords: list[str]) -> dict[str, Any]:
    if candidate.get("source") == "venue":
        return summarize_venue_paper(load_papers_cool_paper(candidate["slug"]), subtopic, topic_keywords)
    return summarize_arxiv_paper(candidate, subtopic, topic_keywords)


def summarize_candidates(selected_candidates: list[dict[str, Any]], subtopic: SubtopicSpec, topic_keywords: list[str], max_workers: int) -> list[dict[str, Any]]:
    papers: list[dict[str, Any] | None] = [None] * len(selected_candidates)
    worker_count = max(1, min(max_workers, len(selected_candidates) or 1))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_index = {
            executor.submit(summarize_candidate, candidate, subtopic, topic_keywords): index
            for index, candidate in enumerate(selected_candidates)
        }
        for future in as_completed(future_to_index):
            papers[future_to_index[future]] = future.result()

    return [paper for paper in papers if paper]


def top_concepts_from_papers(papers: list[dict[str, Any]], limit: int = 3) -> list[str]:
    counter: Counter[str] = Counter()
    for paper in papers:
        for keyword in paper.get("keywords", [])[:4]:
            counter[keyword] += 1
    return [keyword for keyword, _ in counter.most_common(limit)]


def top_roles_from_papers(papers: list[dict[str, Any]], limit: int = 2) -> list[str]:
    counter: Counter[str] = Counter()
    for paper in papers:
        role = compact(paper.get("role", ""))
        if role:
            counter[role] += 1
    return [role for role, _ in counter.most_common(limit)]


def build_topic_overview(subtopic: SubtopicSpec, papers: list[dict[str, Any]]) -> str:
    concepts = top_concepts_from_papers(papers)
    roles = top_roles_from_papers(papers)
    focus = "、".join(concepts) if concepts else subtopic.name
    role_text = "、".join(roles) if roles else "若干代表工作"
    return (
        f"这个 topic 主要围绕 {focus} 展开。之所以把它单独成章，是因为这一组论文更集中地体现了 {role_text} 在整个主题里的分工和关系。"
    )


def build_topic_intro(
    subtopic: SubtopicSpec,
    venue_stats: dict[str, Any],
    arxiv_stats: dict[str, Any],
    candidate_pool_size: int,
    papers: list[dict[str, Any]],
) -> str:
    concepts = top_concepts_from_papers(papers)
    routes = "、".join(concepts) if concepts else subtopic.name
    return (
        f"这一部分聚焦“{subtopic.name}”。我先在默认六大会（{' / '.join(venue_stats.get('venues', []))}）中按关键词全量扫描近年会场，"
        f"共扫过约 {venue_stats.get('records_scanned', 0)} 条 venue 记录，命中 {venue_stats.get('matches', 0)} 篇候选；"
        f"随后再用近期 arXiv 检索补充，得到 {arxiv_stats.get('matches', 0)} 篇候选。"
        f"两部分合并去重后共有 {candidate_pool_size} 篇候选，最终保留 {len(papers)} 篇文献展开解读，主线大致落在 {routes} 这几条线上。"
    )


def build_topic_summary(subtopic: SubtopicSpec, papers: list[dict[str, Any]]) -> str:
    concepts = top_concepts_from_papers(papers)
    focus = "、".join(concepts) if concepts else subtopic.name
    return (
        f"“{subtopic.name}”这一组已经围绕 {focus} 形成了相对稳定的阅读主线。"
        f"继续深入时，关键是分清哪些论文在重构问题设定，哪些论文在改进已有方法，哪些论文在补足 benchmark 或理论解释。"
    )


def build_overall_summary(main_topic: str, subtopics: list[dict[str, Any]]) -> dict[str, Any]:
    all_papers = [paper for subtopic in subtopics for paper in subtopic.get("papers", [])]
    concepts = top_concepts_from_papers(all_papers, limit=5)
    roles = top_roles_from_papers(all_papers, limit=3)
    top_titles = [paper["title"] for paper in all_papers[:5]]
    focus = "、".join(concepts) if concepts else main_topic
    role_text = "、".join(roles) if roles else "方法工作"
    return {
        "overview": f"围绕“{main_topic}”，当前候选论文主要集中在 {focus} 这些主题上，并沿着 {role_text} 这几类工作展开。",
        "trends": [
            "代表论文通常会同时回答三个问题：问题怎么定义、方法核心机制是什么、实验到底在什么设定下比较。",
            "顶会论文更容易承担 benchmark、问题设定和代表方法的角色，而近期 arXiv 更容易补充扩展方向和新变体。",
            "真正有价值的综述，不是只列论文，而是解释这些论文之间在主线、分叉和评测协议上的关系。",
        ],
        "gaps": [
            "仅靠题目和摘要容易高估工作贡献，关键论文仍然需要方法和实验级精读。",
            "不同论文之间的任务设定和比较协议未必完全一致，综述时需要明确交代可比性边界。",
            "如果不先把运行时推断出的 subtopics 和关键词校准好，候选池很容易过宽或过窄。",
        ],
        "important_points": [
            "写综述时，先解释为什么选这些论文，再解释它们之间是什么关系，最后才比较指标。",
            "一个通用调研框架最重要的是运行时的 topic analysis，而不是把某个方向的先验写死在代码里。",
            "如果后续继续深入，建议沿着代表论文构造一条从问题设定到 benchmark 的渐进式阅读路径。",
        ],
        "reading_path": top_titles,
    }


def published_sort_key(paper: dict[str, Any]) -> tuple[int, int, str]:
    published = compact(paper.get("published", ""))
    match = re.search(r"(20\d{2})(?:-(\d{2}))?", published)
    if match:
        year = int(match.group(1))
        month = int(match.group(2) or 0)
    else:
        year = int(str(paper.get("year", "0")) or 0)
        month = 0
    return year, month, normalize_text(paper.get("title", ""))


def relation_label_for_paper(paper: dict[str, Any], index: int) -> str:
    role = compact(paper.get("role", ""))
    if index == 0:
        return "opens"
    if "基准" in role:
        return "benchmarks"
    if "系统" in role or "架构" in role:
        return "scales"
    if "综述" in role or "理论" in role:
        return "synthesizes"
    return "extends"


def build_ending(subtopics: list[dict[str, Any]], overall_summary: dict[str, Any]) -> dict[str, Any]:
    important_papers: list[str] = []
    topic_timelines: list[dict[str, Any]] = []

    for subtopic in subtopics:
        papers = subtopic.get("papers", [])
        if papers:
            representative = papers[0]
            paper_ref = representative.get("paper_id")
            if paper_ref and paper_ref not in important_papers:
                important_papers.append(paper_ref)

        ordered_representatives = sorted(papers[:5], key=published_sort_key)
        topic_timelines.append(
            {
                "topic_name": subtopic.get("name", ""),
                "representative_papers": [
                    {
                        "paper_ref": paper.get("paper_id"),
                        "published": paper.get("published", ""),
                        "title": paper.get("title", ""),
                        "why_representative": compact(paper.get("insight") or paper.get("table_summary") or ""),
                        "relation_label": relation_label_for_paper(paper, index),
                    }
                    for index, paper in enumerate(ordered_representatives)
                    if paper.get("paper_id")
                ],
            }
        )

    reading_recommendations = [
        compact(item)
        for item in overall_summary.get("reading_path", [])
        if compact(item)
    ]
    return {
        "synthesis": overall_summary.get("overview", ""),
        "important_papers": important_papers[:10],
        "topic_timelines": topic_timelines,
        "reading_recommendations": reading_recommendations,
    }


def build_survey(
    topic: str,
    venue_years: list[int],
    venues: list[str],
    arxiv_date_from: str,
    arxiv_limit: int,
    min_total_papers: int,
    per_topic_floor: int | None,
    min_candidates_per_topic: int,
    max_workers: int,
    aliases_override: list[str] | None = None,
    subtopics_override: list[str] | None = None,
    keywords_override: list[str] | None = None,
) -> dict[str, Any]:
    plan = parse_topic(topic, aliases_override, subtopics_override, keywords_override)
    result = {
        "schema_version": SCHEMA_VERSION,
        "main_topic": plan.main_topic,
        "parsed_subtopics": [subtopic.name for subtopic in plan.subtopics],
        "keywords": plan.keywords,
        "topic_analysis": {
            "aliases": plan.aliases,
            "subtopics": [asdict(subtopic) for subtopic in plan.subtopics],
        },
        "search_scope": {
            "venues": venues,
            "venue_years": venue_years,
            "arxiv_date_from": arxiv_date_from,
            "arxiv_limit": arxiv_limit,
            "max_workers": max_workers,
        },
        "selection_contract": {
            "min_total_papers": min_total_papers,
            "per_topic_floor": per_topic_floor,
            "allocation_strategy": "derived_topic_floor",
            "rebalance_strategy": "density_then_diversity",
        },
        "selection_status": SELECTION_STATUS_OK,
        "requirement_failures": [],
        "totals": {
            "candidate_pool_size": 0,
            "curated_papers": 0,
            "topic_count": len(plan.subtopics),
        },
        "subtopics": [],
    }

    topic_rows: list[dict[str, Any]] = []
    for subtopic in plan.subtopics:
        venue_candidates, venue_stats = fetch_venue_candidates(
            plan,
            subtopic,
            venue_years,
            venues,
            DEFAULT_VENUE_SCAN_LIMIT,
            max_workers,
        )
        arxiv_candidates, arxiv_stats = fetch_arxiv_candidates(
            plan,
            subtopic,
            arxiv_date_from,
            arxiv_limit,
            max_workers,
        )

        combined_candidates = dedupe_candidates(venue_candidates + arxiv_candidates)
        topic_rows.append(
            {
                "subtopic": subtopic,
                "venue_candidates": venue_candidates,
                "arxiv_candidates": arxiv_candidates,
                "combined_candidates": combined_candidates,
                "venue_stats": venue_stats,
                "arxiv_stats": arxiv_stats,
                "candidate_pool_size": len(combined_candidates),
                "meets_min_candidates": len(combined_candidates) >= min_candidates_per_topic,
            }
        )

    candidate_pool_sizes = [row["candidate_pool_size"] for row in topic_rows]
    target_allocations, base_allocations = derive_topic_targets(
        candidate_pool_sizes,
        min_total_papers,
        per_topic_floor,
    )

    for row, target_count, base_target in zip(topic_rows, target_allocations, base_allocations):
        subtopic = row["subtopic"]
        selected_candidates = select_topic_candidates(
            row["venue_candidates"],
            row["arxiv_candidates"],
            target_count,
        )
        papers = summarize_candidates(selected_candidates, subtopic, plan.keywords, max_workers)
        venue_papers = [paper for paper in papers if paper.get("source") == "venue"]
        arxiv_papers = [paper for paper in papers if paper.get("source") == "arxiv"]

        result["subtopics"].append(
            {
                "name": subtopic.name,
                "topic_overview": build_topic_overview(subtopic, papers),
                "intro": build_topic_intro(subtopic, row["venue_stats"], row["arxiv_stats"], row["candidate_pool_size"], papers),
                "papers": papers,
                "venue_papers": venue_papers,
                "arxiv_papers": arxiv_papers,
                "summary": build_topic_summary(subtopic, papers),
                "allocation": {
                    "target": target_count,
                    "selected": len(papers),
                    "rebalance_delta": target_count - base_target,
                },
                "search_stats": {
                    "venue": row["venue_stats"],
                    "arxiv": row["arxiv_stats"],
                    "candidate_pool_size": row["candidate_pool_size"],
                    "saved_papers": len(papers),
                    "meets_min_candidates": row["meets_min_candidates"],
                },
            }
        )

    overall_summary = build_overall_summary(plan.main_topic, result["subtopics"])
    result["overall_summary"] = overall_summary
    result["ending"] = build_ending(result["subtopics"], overall_summary)

    global_candidates = dedupe_candidates(
        [candidate for row in topic_rows for candidate in row["combined_candidates"]]
    )
    curated_total = sum(len(subtopic.get("papers", [])) for subtopic in result["subtopics"])
    result["totals"] = {
        "candidate_pool_size": len(global_candidates),
        "curated_papers": curated_total,
        "topic_count": len(result["subtopics"]),
    }

    if curated_total < min_total_papers:
        result["selection_status"] = SELECTION_STATUS_BLOCKED
        result["requirement_failures"].append(
            f"最低总保留论文数 {min_total_papers} 未满足，当前仅 {curated_total} 篇。"
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto survey papers with runtime topic analysis, global-total-first selection, arXiv enrichment, and markdown rendering.")
    parser.add_argument("topic", help="研究主题，例如：具身空间智能")
    parser.add_argument("-o", "--output", help="输出 markdown 文件路径")
    parser.add_argument("--json-output", help="输出中间 JSON 文件路径")
    parser.add_argument("--aliases", help="逗号分隔的主题别名、英文标准表述或缩写，优先作为检索主锚点")
    parser.add_argument("--subtopics", help="逗号分隔的子方向，覆盖自动拆题")
    parser.add_argument("--keywords", help="逗号分隔的检索关键词，覆盖自动关键词生成")
    parser.add_argument("--lookback-years", type=int, default=DEFAULT_LOOKBACK_YEARS, help="默认从当前年份往前回溯多少年")
    parser.add_argument("--venue-years", help="Venue 检索年份，逗号分隔；默认会按当前年份自动回溯")
    parser.add_argument("--venues", default="CVPR,ICCV,ECCV,ICML,ICLR,NeurIPS", help="默认检索的六大会，逗号分隔")
    parser.add_argument("--arxiv-date-from", help="ArXiv 起始日期；默认会按当前年份自动回溯")
    parser.add_argument("--arxiv-limit", type=int, default=DEFAULT_ARXIV_LIMIT)
    parser.add_argument("--min-total-papers", type=int, default=DEFAULT_MIN_TOTAL_PAPERS, help="最终至少保留多少篇论文（默认 200）")
    parser.add_argument("--per-topic-papers", type=int, help="兼容选项：每个 topic 的初始 floor；最终仍以 --min-total-papers 为主")
    parser.add_argument("--min-candidates", type=int, default=DEFAULT_MIN_CANDIDATES_PER_TOPIC, help="兼容提示：每个 topic 的候选池参考下限，用于记录而非硬失败")
    parser.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS, help="并发抓取和解析时使用的线程数")
    parser.add_argument("--cache-dir", help="命令级 JSON 缓存目录；可先在可联网环境预热，再在受限环境复用")
    parser.add_argument(
        "--cache-mode",
        choices=[CACHE_MODE_OFF, CACHE_MODE_READ_WRITE, CACHE_MODE_READ_ONLY],
        default=CACHE_MODE_OFF,
        help="缓存模式：off / read-write / read-only",
    )
    parser.add_argument("--delete-cache-after-run", action="store_true", help="运行结束后删除 cache-dir")
    parser.add_argument("--prefetch-only", action="store_true", help="只预热缓存，不输出 survey 文件")
    parser.add_argument("--per-source", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--diagram-count", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    configure_cache(args.cache_dir, args.cache_mode, args.delete_cache_after_run)

    try:
        venue_years = (
            [int(value) for value in args.venue_years.split(",") if value.strip()]
            if args.venue_years
            else default_venue_years(args.lookback_years)
        )
        venues = [compact(value) for value in args.venues.split(",") if compact(value)]
        arxiv_date_from = args.arxiv_date_from or default_arxiv_date_from(args.lookback_years)
        min_total_papers = max(1, args.min_total_papers)
        per_topic_floor = max(1, args.per_topic_papers) if args.per_topic_papers else None
        if args.per_source:
            derived_floor = max(1, args.per_source * 2)
            per_topic_floor = max(per_topic_floor or 0, derived_floor)
        min_candidates = max(1, args.min_candidates)
        max_workers = max(1, args.max_workers)

        survey = build_survey(
            args.topic,
            venue_years,
            venues,
            arxiv_date_from,
            args.arxiv_limit,
            min_total_papers,
            per_topic_floor,
            min_candidates,
            max_workers,
            split_cli_csv(args.aliases),
            split_cli_csv(args.subtopics),
            split_cli_csv(args.keywords),
        )
        exit_code = 2 if survey.get("selection_status") == SELECTION_STATUS_BLOCKED else 0

        if args.prefetch_only:
            cache_dir = str(CACHE_CONFIG.cache_dir) if CACHE_CONFIG.cache_dir else "(disabled)"
            print(
                json.dumps(
                    {
                        "status": "prefetch_complete",
                        "selection_status": survey.get("selection_status"),
                        "curated_papers": survey.get("totals", {}).get("curated_papers", 0),
                        "cache_dir": cache_dir,
                        "cache_mode": CACHE_CONFIG.mode,
                        "topic": args.topic,
                        "subtopics": survey.get("parsed_subtopics", []),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return exit_code

        if args.json_output:
            Path(args.json_output).write_text(json.dumps(survey, ensure_ascii=False, indent=2), encoding="utf-8")

        render_script = Path(__file__).with_name("render_survey.py")
        if args.output:
            if not args.json_output:
                tmp_json = Path(args.output).with_suffix(".json")
                tmp_json.write_text(json.dumps(survey, ensure_ascii=False, indent=2), encoding="utf-8")
                json_path = tmp_json
            else:
                json_path = Path(args.json_output)
            subprocess.run([sys.executable, str(render_script), str(json_path), "-o", args.output], check=True)
        else:
            print(json.dumps(survey, ensure_ascii=False, indent=2))
    finally:
        if CACHE_CONFIG.delete_after_run and CACHE_CONFIG.cache_dir and CACHE_CONFIG.cache_dir.exists():
            shutil.rmtree(CACHE_CONFIG.cache_dir)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
