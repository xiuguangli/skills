#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from typing import Any

EVIDENCE_STATUS_LABELS = {
    "full_text_verified": "全文验证",
    "abstract_only": "仅摘要",
    "metadata_only": "仅元数据",
    "legacy_unlabeled": "旧版未标注",
}

RELATION_LABELS = {
    "opens": "opens（开启主线）",
    "extends": "extends（延展）",
    "benchmarks": "benchmarks（建立基准）",
    "scales": "scales（规模扩展）",
    "synthesizes": "synthesizes（综合整合）",
}


def clean_text(value: Any) -> str:
    return str(value or "").replace("\n", " ").strip()


def table_cell(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return "-"
    return text.replace("|", "\\|")


def markdown_link(label: Any, url: Any) -> str:
    text = clean_text(label)
    target = clean_text(url)
    escaped_text = text.replace("|", "\\|") if text else ""
    if target and escaped_text:
        return f"[{escaped_text}]({target})"
    return escaped_text or "-"


def paper_primary_url(paper: dict[str, Any]) -> str:
    return clean_text(paper.get("paper_url") or paper.get("access_url") or paper.get("url"))


def paper_link(paper: dict[str, Any]) -> str:
    return markdown_link(paper.get("title", "-"), paper_primary_url(paper))


def format_published(paper: dict[str, Any]) -> str:
    published = clean_text(paper.get("published", ""))
    if published:
        return published
    venue = clean_text(paper.get("venue", ""))
    year = clean_text(paper.get("year", ""))
    if venue.lower() == "arxiv":
        return f"arXiv {year}" if year else "arXiv"
    match = re.match(r"([A-Za-z]+)\.(\d{4})$", venue)
    if match:
        venue = f"{match.group(1)} {match.group(2)}"
    if venue and year and year not in venue:
        return f"{venue} {year}"
    return venue or "-"


def format_evidence_status(status: Any) -> str:
    key = clean_text(status)
    if not key:
        return "-"
    return EVIDENCE_STATUS_LABELS.get(key, key)


def format_relation_label(label: Any) -> str:
    key = clean_text(label)
    if not key:
        return "-"
    return RELATION_LABELS.get(key, key)


def format_link_line(label: str, url: Any) -> str:
    target = clean_text(url)
    if not target:
        return f"- {label}：-"
    return f"- {label}：[{label}]({target})"


def legacy_intro(subtopic: dict[str, Any], papers: list[dict[str, Any]]) -> str:
    return f"这一部分聚焦“{subtopic.get('name', '')}”。以下内容是根据现有论文列表自动整理出的基础解读，正式综述写作时仍建议补充正文精读。"


def legacy_summary(subtopic: dict[str, Any], papers: list[dict[str, Any]]) -> str:
    return f"这一 topic 当前更像是在补齐“{subtopic.get('name', '')}”相关的能力件，后续如果要写成高质量综述，关键是进一步补上正文精读后的系统判断。"


def legacy_topic_overview(subtopic: dict[str, Any], papers: list[dict[str, Any]]) -> str:
    return f"这个 topic 主要围绕“{subtopic.get('name', '')}”展开，关注该方向里的核心能力模块、系统接口和代表性方法。"


def merge_legacy_papers(subtopic: dict[str, Any]) -> list[dict[str, Any]]:
    if subtopic.get("papers"):
        return list(subtopic["papers"])

    papers: list[dict[str, Any]] = []
    for paper in subtopic.get("venue_papers", []):
        papers.append(
            {
                **paper,
                "published": paper.get("published") or format_published(paper),
                "analysis": paper.get("analysis") or paper.get("abstract_summary", ""),
                "table_summary": paper.get("table_summary") or paper.get("abstract_summary", ""),
                "insight": paper.get("insight") or paper.get("advisor_note", ""),
                "example": paper.get("example", ""),
                "diagram": paper.get("diagram", ""),
            }
        )
    for paper in subtopic.get("arxiv_papers", []):
        published = paper.get("published")
        if not published:
            year = clean_text(paper.get("year", ""))
            month_match = re.match(r"(\d{4})-(\d{2})", year)
            published = f"arXiv {month_match.group(0)}" if month_match else f"arXiv {year}".strip()
        papers.append(
            {
                **paper,
                "published": published,
                "analysis": paper.get("analysis") or paper.get("abstract_summary", ""),
                "table_summary": paper.get("table_summary") or paper.get("abstract_summary", ""),
                "insight": paper.get("insight") or paper.get("advisor_note", ""),
                "example": paper.get("example", ""),
                "diagram": paper.get("diagram", ""),
            }
        )
    return papers


def is_legacy_payload(data: dict[str, Any]) -> bool:
    schema_version = clean_text(data.get("schema_version"))
    return not schema_version or schema_version.startswith("1")


def normalize_paper(paper: dict[str, Any], legacy_mode: bool) -> dict[str, Any]:
    access_url = clean_text(paper.get("access_url") or paper.get("url") or paper.get("paper_url"))
    paper_url = clean_text(paper.get("paper_url") or paper.get("url") or access_url)
    pdf_url = clean_text(paper.get("pdf_url") or paper.get("pdf"))
    evidence_status = clean_text(paper.get("evidence_status"))
    evidence_note = clean_text(paper.get("evidence_note"))
    if legacy_mode:
        evidence_status = evidence_status or "legacy_unlabeled"
        evidence_note = evidence_note or "旧版数据未显式区分全文、摘要或元数据证据。"
    return {
        **paper,
        "paper_id": clean_text(paper.get("paper_id") or paper.get("id") or paper.get("title")),
        "title": clean_text(paper.get("title", "")),
        "authors": clean_text(paper.get("authors", "")),
        "published": clean_text(paper.get("published")) or format_published(paper),
        "paper_url": paper_url,
        "access_url": access_url or paper_url,
        "pdf_url": pdf_url,
        "evidence_status": evidence_status,
        "evidence_note": evidence_note,
        "analysis": clean_text(paper.get("analysis") or paper.get("abstract_summary", "")),
        "table_summary": clean_text(
            paper.get("table_summary") or paper.get("abstract_summary") or paper.get("analysis", "")
        ),
        "insight": clean_text(paper.get("insight") or paper.get("advisor_note", "")),
        "example": clean_text(paper.get("example", "")),
        "diagram": str(paper.get("diagram", "")).strip(),
    }


def collect_topics(data: dict[str, Any], legacy_mode: bool) -> tuple[list[tuple[dict[str, Any], list[dict[str, Any]]]], dict[str, dict[str, Any]]]:
    topics: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    paper_index: dict[str, dict[str, Any]] = {}
    for subtopic in data.get("subtopics", []):
        raw_papers = subtopic.get("papers") or merge_legacy_papers(subtopic)
        papers = [normalize_paper(paper, legacy_mode) for paper in raw_papers]
        for paper in papers:
            paper_id = clean_text(paper.get("paper_id"))
            if paper_id and paper_id not in paper_index:
                paper_index[paper_id] = paper
        topics.append((subtopic, papers))
    return topics, paper_index


def render_topic_table(lines: list[str], papers: list[dict[str, Any]]) -> None:
    lines.append("| 论文标题 | 作者 | 发表 | 证据等级 | 一句话概括 | 重要点 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    if papers:
        for paper in papers:
            lines.append(
                f"| {paper_link(paper)} | {table_cell(paper.get('authors', ''))} | "
                f"{table_cell(format_published(paper))} | {table_cell(format_evidence_status(paper.get('evidence_status', '')))} | "
                f"{table_cell(paper.get('table_summary', ''))} | {table_cell(paper.get('insight', ''))} |"
            )
    else:
        lines.append("| 暂无结果 | - | - | - | - | - |")
    lines.append("")


def render_top_warning(lines: list[str], data: dict[str, Any], legacy_mode: bool) -> None:
    selection_status = clean_text(data.get("selection_status"))
    requirement_failures = [clean_text(item) for item in data.get("requirement_failures", []) if clean_text(item)]

    if legacy_mode:
        lines.append("## 兼容性提示")
        lines.append("")
        lines.append(
            "- 当前输入缺少 `schema_version`，已按 legacy 1.x 兼容模式渲染。"
        )
        lines.append(
            "- 旧版数据未显式区分 PDF / 访问链接 / 证据等级，也没有代表论文时间线；以下展示只做字段回填，不会伪造缺失信息。"
        )
        lines.append("")

    if selection_status == "blocked_insufficient_candidates" or requirement_failures:
        lines.append("## 结果告警")
        lines.append("")
        lines.append(f"- 当前选择状态：{selection_status or 'blocked'}")
        for failure in requirement_failures or ["未满足最低总论文数要求。"]:
            lines.append(f"- {failure}")
        lines.append("")


def render_research_scope(lines: list[str], data: dict[str, Any], legacy_mode: bool, topic_count: int) -> None:
    parsed_subtopics = data.get("parsed_subtopics") or [sub.get("name", "") for sub in data.get("subtopics", [])]
    keywords = data.get("keywords", [])
    search_scope = data.get("search_scope", {})
    selection_contract = data.get("selection_contract", {})
    totals = data.get("totals", {})
    schema_version = clean_text(data.get("schema_version")) or "legacy 1.x"

    lines.append("## 研究主题解析")
    lines.append("")
    lines.append(f"- 核心主题：{data.get('main_topic', '-')}")
    lines.append(f"- Schema 版本：{schema_version}")
    if parsed_subtopics:
        items = [item for item in parsed_subtopics if item]
        if items:
            lines.append(f"- 子方向：{'；'.join(items)}")
    if keywords:
        items = [item for item in keywords if item]
        if items:
            lines.append(f"- 检索关键词：{'；'.join(items)}")
    if search_scope:
        venues = " / ".join(search_scope.get("venues", []))
        years = "、".join(str(year) for year in search_scope.get("venue_years", []))
        lines.append(f"- Venue 默认范围：{venues or '-'}")
        lines.append(f"- Venue 检索年份：{years or '-'}")
        lines.append(f"- ArXiv 起始日期：{search_scope.get('arxiv_date_from', '-')}")
        lines.append(f"- ArXiv 检索上限：{search_scope.get('arxiv_limit', '-')}")
        lines.append(f"- 抓取线程数：{search_scope.get('max_workers', '-')}")
    if selection_contract:
        lines.append(f"- 最低总保留论文数：{selection_contract.get('min_total_papers', '-')}")
        per_topic_floor = selection_contract.get("per_topic_floor")
        if per_topic_floor is not None:
            lines.append(f"- 兼容 topic floor：{per_topic_floor}")
        lines.append(f"- 分配策略：{selection_contract.get('allocation_strategy', '-')}")
        lines.append(f"- Rebalance 策略：{selection_contract.get('rebalance_strategy', '-')}")
    elif search_scope:
        lines.append(f"- 每个 topic 保留论文数：{search_scope.get('papers_per_topic', search_scope.get('per_source', '-'))}")
        lines.append(f"- 每个 topic 最少候选数：{search_scope.get('min_candidates_per_topic', '-')}")
    if totals:
        lines.append(f"- 当前候选池规模：{totals.get('candidate_pool_size', '-')}")
        lines.append(f"- 当前保留论文数：{totals.get('curated_papers', '-')}")
        lines.append(f"- Topic 数量：{totals.get('topic_count', topic_count)}")
    elif not legacy_mode:
        lines.append(f"- Topic 数量：{topic_count}")
    lines.append("")


def render_topic_metadata(lines: list[str], subtopic: dict[str, Any]) -> None:
    allocation = subtopic.get("allocation", {})
    search_stats = subtopic.get("search_stats", {})
    if not allocation and not search_stats:
        return

    lines.append("### Topic 配额与检索")
    target = allocation.get("target")
    selected = allocation.get("selected")
    rebalance_delta = allocation.get("rebalance_delta")
    if target is not None or selected is not None or rebalance_delta is not None:
        lines.append(
            f"- 配额：target={target if target is not None else '-'}，selected={selected if selected is not None else '-'}，rebalance_delta={rebalance_delta if rebalance_delta is not None else '-'}"
        )
    if search_stats:
        venue_stats = search_stats.get("venue", {})
        arxiv_stats = search_stats.get("arxiv", {})
        lines.append(
            f"- Venue 扫描：records_scanned={venue_stats.get('records_scanned', '-')}，matches={venue_stats.get('matches', '-')}"
        )
        lines.append(f"- arXiv 命中：{arxiv_stats.get('matches', '-')}")
        lines.append(f"- Topic 候选池：{search_stats.get('candidate_pool_size', '-')}")
    lines.append("")


def render_topic_sections(lines: list[str], topics: list[tuple[dict[str, Any], list[dict[str, Any]]]]) -> None:
    for index, (subtopic, papers) in enumerate(topics, start=1):
        lines.append(f"## {index}. {subtopic.get('name', f'Topic {index}')}")
        lines.append("")
        lines.append("### Topic 解读")
        lines.append(clean_text(subtopic.get("topic_overview", "")) or legacy_topic_overview(subtopic, papers))
        lines.append("")
        render_topic_metadata(lines, subtopic)
        lines.append("### 主题导读")
        lines.append(clean_text(subtopic.get("intro", "")) or legacy_intro(subtopic, papers))
        lines.append("")
        lines.append("### 逐篇解读")
        lines.append("")

        for paper_index, paper in enumerate(papers, start=1):
            lines.append(f"#### {paper_index}. {paper_link(paper)}")
            lines.append(f"- 发表：{format_published(paper)}")
            lines.append(f"- 作者：{clean_text(paper.get('authors', '')) or '-'}")
            lines.append(format_link_line("PDF", paper.get("pdf_url")))
            lines.append(format_link_line("访问链接", paper.get("access_url")))
            lines.append(f"- 证据等级：{format_evidence_status(paper.get('evidence_status', ''))}")
            evidence_note = clean_text(paper.get("evidence_note", ""))
            if evidence_note:
                lines.append(f"- 证据说明：{evidence_note}")
            lines.append(
                f"- 论文内容：{clean_text(paper.get('analysis', '')) or clean_text(paper.get('table_summary', '')) or '-'}"
            )
            insight = clean_text(paper.get("insight", ""))
            if insight:
                lines.append(f"- 我的理解：{insight}")
            example = clean_text(paper.get("example", ""))
            if example:
                lines.append(f"- 直观例子：{example}")
            diagram = str(paper.get("diagram", "")).strip()
            if diagram:
                lines.append("")
                lines.append("```mermaid")
                lines.append(diagram)
                lines.append("```")
            lines.append("")

        lines.append("### 表格汇总")
        render_topic_table(lines, papers)
        lines.append("### 本主题小结")
        lines.append(clean_text(subtopic.get("summary", "")) or legacy_summary(subtopic, papers))
        lines.append("")


def render_important_papers(lines: list[str], entries: list[Any], paper_index: dict[str, dict[str, Any]]) -> None:
    if not entries:
        lines.append("- 暂未生成。")
        lines.append("")
        return

    for entry in entries:
        if isinstance(entry, dict):
            paper_ref = clean_text(entry.get("paper_ref") or entry.get("paper_id") or entry.get("title"))
            paper = paper_index.get(paper_ref)
            title = clean_text(entry.get("title")) or (paper.get("title") if paper else paper_ref)
            published = clean_text(entry.get("published")) or (format_published(paper) if paper else "-")
            why = clean_text(entry.get("why_representative"))
        else:
            paper_ref = clean_text(entry)
            paper = paper_index.get(paper_ref)
            title = paper.get("title") if paper else paper_ref
            published = format_published(paper) if paper else "-"
            why = ""

        if paper:
            bullet = f"- {paper_link(paper)}（{published}，证据等级：{format_evidence_status(paper.get('evidence_status'))}）"
        else:
            bullet = f"- {title or '-'}"
        if why:
            bullet += f"：{why}"
        lines.append(bullet)
    lines.append("")


def render_timelines(lines: list[str], timelines: list[dict[str, Any]], paper_index: dict[str, dict[str, Any]], legacy_mode: bool) -> None:
    if not timelines:
        if legacy_mode:
            lines.append("- 旧版数据未提供 Topic 演化时间线，本次兼容渲染不会伪造代表论文关系。")
        else:
            lines.append("- 暂未生成 Topic 演化时间线。")
        lines.append("")
        return

    for timeline in timelines:
        topic_name = clean_text(timeline.get("topic_name")) or "未命名 Topic"
        lines.append(f"#### {topic_name}")
        representatives = timeline.get("representative_papers", [])
        if not representatives:
            lines.append("- 暂无代表论文。")
            lines.append("")
            continue
        for entry in representatives:
            paper_ref = clean_text(entry.get("paper_ref"))
            paper = paper_index.get(paper_ref)
            title = clean_text(entry.get("title")) or (paper.get("title") if paper else paper_ref)
            published = clean_text(entry.get("published")) or (format_published(paper) if paper else "-")
            why = clean_text(entry.get("why_representative"))
            relation = format_relation_label(entry.get("relation_label"))
            link = markdown_link(title, paper_primary_url(paper or entry))
            line = f"- {published} · {link} · {relation}"
            if why:
                line += f"：{why}"
            lines.append(line)
        lines.append("")


def render_conclusion(lines: list[str], data: dict[str, Any], paper_index: dict[str, dict[str, Any]], legacy_mode: bool) -> None:
    ending = data.get("ending", {})
    overall_summary = data.get("overall_summary", {})

    synthesis = clean_text(ending.get("synthesis") or overall_summary.get("overview"))
    trends = [clean_text(item) for item in overall_summary.get("trends", []) if clean_text(item)]
    gaps = [clean_text(item) for item in overall_summary.get("gaps", []) if clean_text(item)]
    important_points = [
        clean_text(item)
        for item in (overall_summary.get("important_points") or overall_summary.get("opportunities") or [])
        if clean_text(item)
    ]
    important_papers = ending.get("important_papers", [])
    timelines = ending.get("topic_timelines", [])
    reading_recommendations = [
        clean_text(item)
        for item in (ending.get("reading_recommendations") or overall_summary.get("reading_path") or [])
        if clean_text(item)
    ]

    lines.append("## 综合总结")
    lines.append("")
    lines.append("### 我的总体判断")
    lines.append("")
    if synthesis:
        lines.append(synthesis)
        lines.append("")
    else:
        lines.append("暂未生成总体判断。")
        lines.append("")
    for label, items in (("已形成的主线", trends), ("关键缺口", gaps), ("重要点", important_points)):
        if items:
            lines.append(f"- {label}：{'；'.join(items)}")
    if trends or gaps or important_points:
        lines.append("")

    lines.append("### 重要代表文献")
    lines.append("")
    render_important_papers(lines, important_papers, paper_index)

    lines.append("### Topic 演化时间线")
    lines.append("")
    render_timelines(lines, timelines, paper_index, legacy_mode)

    lines.append("### 后续精读建议")
    lines.append("")
    if reading_recommendations:
        for index, item in enumerate(reading_recommendations, start=1):
            lines.append(f"{index}. {item}")
    else:
        lines.append("1. 暂未生成精读建议。")
    lines.append("")


def render(data: dict[str, Any]) -> str:
    main_topic = clean_text(data.get("main_topic")) or "未命名主题"
    legacy_mode = is_legacy_payload(data)
    topics, paper_index = collect_topics(data, legacy_mode)

    lines = [f"# 论文调研：{main_topic}", ""]
    render_top_warning(lines, data, legacy_mode)
    render_research_scope(lines, data, legacy_mode, len(topics))
    render_topic_sections(lines, topics)
    render_conclusion(lines, data, paper_index, legacy_mode)
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render research-papers survey markdown from JSON.")
    parser.add_argument("input", help="Path to input JSON")
    parser.add_argument("-o", "--output", help="Write markdown to file instead of stdout")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    markdown = render(data)

    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")


if __name__ == "__main__":
    main()
