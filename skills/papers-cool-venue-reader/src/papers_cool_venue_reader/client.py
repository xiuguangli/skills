from __future__ import annotations

import json
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote, urlencode, urljoin

import requests
from bs4 import BeautifulSoup, FeatureNotFound


BASE_URL = "https://papers.cool"
DEFAULT_TIMEOUT = 30
USER_AGENT = "papers-cool-venue-reader/0.3.1"
ATOM_NS = "http://www.w3.org/2005/Atom"
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT_CANDIDATES = (PACKAGE_ROOT.parent.parent, PACKAGE_ROOT.parent)

for candidate in PROJECT_ROOT_CANDIDATES:
    vendor_dir = candidate / "vendor"
    if vendor_dir.exists():
        sys.path.insert(0, str(vendor_dir))
        break


class PapersCoolError(RuntimeError):
    """Raised when papers.cool data cannot be retrieved or parsed."""


@dataclass(slots=True)
class PaperRecord:
    slug: str
    title: str
    authors: list[str]
    summary: str
    venue: str | None = None
    group: str | None = None
    year: int | None = None
    keywords: list[str] | None = None
    papers_cool_url: str | None = None
    official_url: str | None = None
    pdf_url: str | None = None
    pdf_stars: int | None = None
    kimi_stars: int | None = None
    index: int | None = None
    verified: bool = False
    verification_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {key: value for key, value in data.items() if value not in (None, [], "")}


def _compact(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.split())


def _maybe_int(text: str | None) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _parse_venue_parts(subject: str | None) -> tuple[str | None, str | None, int | None]:
    if not subject:
        return None, None, None
    text = _compact(subject)
    if " - " in text:
        venue_part, group = text.split(" - ", 1)
    else:
        venue_part, group = text, None
    match = re.search(r"\.(\d{4})$", venue_part)
    year = int(match.group(1)) if match else None
    return venue_part, group, year


def _safe_filename(text: str) -> str:
    normalized = re.sub(r"[^\w.\-]+", "_", text, flags=re.UNICODE)
    normalized = re.sub(r"_+", "_", normalized).strip("._")
    return normalized or "paper"


def _verification_status(official_url: str | None, pdf_url: str | None) -> tuple[bool, str]:
    if official_url and pdf_url:
        return True, "External official link and PDF link found"
    if official_url:
        return True, "External official link found"
    if pdf_url:
        return True, "PDF link found"
    return False, "papers.cool page found, but no external official link or PDF was exposed"


def _sentence_snippet(text: str, limit: int = 2, max_chars: int = 500) -> str:
    compact = _compact(text)
    if not compact:
        return ""
    pieces = re.split(r"(?<=[.!?])\s+", compact)
    snippet = " ".join(piece for piece in pieces[:limit] if piece)
    if not snippet:
        snippet = compact
    if len(snippet) > max_chars:
        snippet = snippet[: max_chars - 3].rstrip() + "..."
    return snippet


def _tokenize_query(query: str) -> list[str]:
    return [token for token in re.split(r"\W+", query.lower()) if token]


def _score_record(record: PaperRecord, query: str) -> int:
    haystacks = {
        "title": record.title.lower(),
        "summary": record.summary.lower(),
        "authors": " ".join(record.authors).lower(),
        "keywords": " ".join(record.keywords or []).lower(),
    }
    score = 0
    lowered_query = query.lower().strip()
    if lowered_query and lowered_query in haystacks["title"]:
        score += 12
    if lowered_query and lowered_query in haystacks["summary"]:
        score += 5
    for token in _tokenize_query(query):
        score += haystacks["title"].count(token) * 4
        score += haystacks["summary"].count(token) * 2
        score += haystacks["authors"].count(token)
        score += haystacks["keywords"].count(token) * 3
    return score


def _xml_child_text(node: ET.Element, tag: str) -> str:
    child = node.find(f"{{{ATOM_NS}}}{tag}")
    if child is None:
        child = node.find(tag)
    return _compact(child.text if child is not None else None)


def _xml_link_href(node: ET.Element) -> str | None:
    child = node.find(f"{{{ATOM_NS}}}link")
    if child is None:
        child = node.find("link")
    return child.get("href") if child is not None else None


def _xml_author_names(node: ET.Element) -> list[str]:
    authors: list[str] = []
    author_nodes = node.findall(f"{{{ATOM_NS}}}author") or node.findall("author")
    for author in author_nodes:
        name = _xml_child_text(author, "name")
        if name:
            authors.append(name)
    return authors


class PapersCoolClient:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _get_text(self, url: str) -> str:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def _get_bytes(self, url: str) -> bytes:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.content

    def _soup(self, url: str) -> BeautifulSoup:
        html = self._get_text(url)
        try:
            return BeautifulSoup(html, "lxml")
        except FeatureNotFound:
            return BeautifulSoup(html, "html.parser")

    def build_venue_url(self, venue: str, year: int | None = None, group: str | None = None) -> str:
        label = venue.strip()
        if label.startswith("http://") or label.startswith("https://"):
            return label
        if year is not None and not re.search(r"\.\d{4}$", label):
            label = f"{label}.{year}"
        url = urljoin(BASE_URL, f"/venue/{quote(label)}")
        if group:
            url = f"{url}?{urlencode({'group': group})}"
        return url

    def build_feed_url(self, venue: str, year: int | None = None) -> str:
        label = venue.strip()
        if year is not None and not re.search(r"\.\d{4}$", label):
            label = f"{label}.{year}"
        return urljoin(BASE_URL, f"/venue/{quote(label)}/feed")

    def build_paper_url(self, slug_or_url: str) -> str:
        raw = slug_or_url.strip()
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw
        if raw.startswith("/"):
            return urljoin(BASE_URL, raw)
        if "/" in raw and "@" not in raw:
            return urljoin(BASE_URL, raw)
        return urljoin(BASE_URL, f"/venue/{quote(raw)}")

    def list_venue(
        self,
        venue: str,
        year: int | None = None,
        *,
        group: str | None = None,
        query: str | None = None,
        limit: int | None = None,
    ) -> list[PaperRecord]:
        soup = self._soup(self.build_venue_url(venue, year=year, group=group))
        records = self._parse_venue_cards(soup)
        if query:
            scored = [(record, _score_record(record, query)) for record in records]
            scored = [item for item in scored if item[1] > 0]
            scored.sort(key=lambda item: (-item[1], item[0].index or 0))
            records = [item[0] for item in scored]
        if group:
            lowered = group.lower()
            records = [record for record in records if (record.group or "").lower() == lowered]
        if limit is not None:
            records = records[:limit]
        return records

    def list_feed(self, venue: str, year: int | None = None, *, limit: int | None = None) -> list[PaperRecord]:
        xml_text = self._get_text(self.build_feed_url(venue, year=year))
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise PapersCoolError("Could not parse the venue Atom feed returned by papers.cool") from exc

        feed_title = _xml_child_text(root, "title")
        venue_label, _, venue_year = _parse_venue_parts(feed_title)
        entries = root.findall(f"{{{ATOM_NS}}}entry") or root.findall("entry")
        records: list[PaperRecord] = []

        for entry in entries:
            title = _xml_child_text(entry, "title")
            papers_cool_url = _xml_link_href(entry)
            slug = papers_cool_url.rstrip("/").split("/")[-1] if papers_cool_url else title
            summary = _xml_child_text(entry, "summary") or _xml_child_text(entry, "content")
            authors = _xml_author_names(entry)
            records.append(
                PaperRecord(
                    slug=slug,
                    title=title,
                    authors=authors,
                    summary=summary,
                    venue=venue_label or feed_title,
                    year=venue_year,
                    papers_cool_url=papers_cool_url,
                    verification_note="Feed entry only; fetch the paper page to inspect external links and PDFs",
                )
            )

        if limit is not None:
            records = records[:limit]
        return records

    def get_paper(self, slug_or_url: str) -> PaperRecord:
        url = self.build_paper_url(slug_or_url)
        soup = self._soup(url)
        paper = soup.select_one("div.panel.paper")
        if paper is None:
            raise PapersCoolError(f"Could not locate paper details on {url}")

        slug = paper.get("id") or url.rstrip("/").split("/")[-1]
        title = _compact(self._meta_content(soup, "citation_title")) or _compact(
            paper.select_one("a.title-link").get_text(" ", strip=True) if paper.select_one("a.title-link") else None
        )
        authors = [
            _compact(node.get_text(" ", strip=True))
            for node in paper.select("p.authors a.author")
            if _compact(node.get_text(" ", strip=True))
        ]
        if not authors:
            meta_authors = self._meta_content(soup, "citation_authors")
            authors = [name.strip() for name in meta_authors.split(";") if name.strip()] if meta_authors else []

        subject = self._subject_from_card(paper)
        venue, group, year = _parse_venue_parts(subject)
        summary = _compact(paper.select_one("p.summary").get_text(" ", strip=True) if paper.select_one("p.summary") else None)
        official_url = self._external_title_link(paper)
        pdf_url = self._pdf_url_from_card(paper) or self._meta_content(soup, "citation_pdf_url")
        verified, note = _verification_status(official_url, pdf_url)

        return PaperRecord(
            slug=slug,
            title=title,
            authors=authors,
            summary=summary,
            venue=venue,
            group=group,
            year=year,
            keywords=self._keywords_from_card(paper),
            papers_cool_url=url,
            official_url=official_url,
            pdf_url=pdf_url,
            pdf_stars=self._stars_from_card(paper, "pdf"),
            kimi_stars=self._stars_from_card(paper, "kimi"),
            index=self._index_from_card(paper),
            verified=verified,
            verification_note=note,
        )

    def download_pdf(
        self,
        slug_or_url: str,
        *,
        output_dir: str | Path,
        filename: str | None = None,
    ) -> Path:
        record = self.get_paper(slug_or_url)
        if not record.pdf_url:
            raise PapersCoolError(f"No PDF url found for {record.title}")

        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        name = filename or f"{_safe_filename(record.slug)}.pdf"
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        destination = output_root / name
        destination.write_bytes(self._get_bytes(record.pdf_url))
        return destination

    def extract_pdf_text(self, pdf_path: str | Path, *, max_pages: int = 6) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise PapersCoolError(
                "PDF extraction requires the optional 'pypdf' package. Install it with: python -m pip install pypdf"
            ) from exc

        reader = PdfReader(str(pdf_path))
        pages = []
        for page in reader.pages[:max_pages]:
            pages.append(_compact(page.extract_text() or ""))
        return "\n\n".join(page for page in pages if page)

    def brief_from_record(
        self,
        record: PaperRecord,
        *,
        pdf_text: str | None = None,
    ) -> dict[str, Any]:
        basis = "abstract-only"
        snippet = _sentence_snippet(record.summary)
        pdf_preview = None
        if pdf_text:
            basis = "abstract-plus-pdf-preview"
            pdf_preview = _sentence_snippet(pdf_text, limit=4, max_chars=700)

        authors_line = ", ".join(record.authors[:6])
        if len(record.authors) > 6:
            authors_line += f", +{len(record.authors) - 6} more"

        where = record.venue or "Unknown venue"
        if record.group:
            where = f"{where} - {record.group}"
        if record.year and (record.venue is None or str(record.year) not in record.venue):
            where = f"{where} ({record.year})"

        brief_text = [
            f"Title: {record.title}",
            f"Where: {where}",
            f"Authors: {authors_line or 'Unknown authors'}",
            f"External links found: {'yes' if record.verified else 'no'}",
            f"Link status: {record.verification_note or 'No link status note'}",
            f"Abstract gist: {snippet or 'No summary available'}",
        ]
        if record.keywords:
            brief_text.append(f"Keywords: {', '.join(record.keywords[:10])}")
        if pdf_preview:
            brief_text.append(f"PDF preview: {pdf_preview}")

        return {
            "title": record.title,
            "venue": record.venue,
            "group": record.group,
            "year": record.year,
            "verified": record.verified,
            "verification_note": record.verification_note,
            "papers_cool_url": record.papers_cool_url,
            "official_url": record.official_url,
            "pdf_url": record.pdf_url,
            "basis": basis,
            "brief": "\n".join(brief_text),
        }

    def brief(self, slug_or_url: str, *, local_pdf: str | Path | None = None, max_pages: int = 6) -> dict[str, Any]:
        record = self.get_paper(slug_or_url)
        pdf_text = None
        if local_pdf:
            pdf_text = self.extract_pdf_text(local_pdf, max_pages=max_pages)
        return self.brief_from_record(record, pdf_text=pdf_text)

    def brief_with_download(
        self,
        slug_or_url: str,
        *,
        max_pages: int = 6,
    ) -> dict[str, Any]:
        record = self.get_paper(slug_or_url)
        if not record.pdf_url:
            return self.brief_from_record(record)
        with tempfile.TemporaryDirectory(prefix="papers_cool_") as temp_dir:
            pdf_path = self.download_pdf(slug_or_url, output_dir=temp_dir)
            pdf_text = self.extract_pdf_text(pdf_path, max_pages=max_pages)
        return self.brief_from_record(record, pdf_text=pdf_text)

    def _parse_venue_cards(self, soup: BeautifulSoup) -> list[PaperRecord]:
        papers: list[PaperRecord] = []
        for card in soup.select("div.panel.paper"):
            title_link = card.select_one("a.title-link")
            if title_link is None:
                continue
            subject = self._subject_from_card(card)
            venue, group, year = _parse_venue_parts(subject)
            official_url = self._external_title_link(card)
            pdf_url = self._pdf_url_from_card(card)
            verified, note = _verification_status(official_url, pdf_url)
            slug = card.get("id") or title_link.get("href", "").rstrip("/").split("/")[-1]
            papers.append(
                PaperRecord(
                    slug=slug,
                    title=_compact(title_link.get_text(" ", strip=True)),
                    authors=[
                        _compact(node.get_text(" ", strip=True))
                        for node in card.select("p.authors a.author")
                        if _compact(node.get_text(" ", strip=True))
                    ],
                    summary=_compact(card.select_one("p.summary").get_text(" ", strip=True) if card.select_one("p.summary") else None),
                    venue=venue,
                    group=group,
                    year=year,
                    keywords=self._keywords_from_card(card),
                    papers_cool_url=urljoin(BASE_URL, title_link.get("href", "")),
                    official_url=official_url,
                    pdf_url=pdf_url,
                    pdf_stars=self._stars_from_card(card, "pdf"),
                    kimi_stars=self._stars_from_card(card, "kimi"),
                    index=self._index_from_card(card),
                    verified=verified,
                    verification_note=note,
                )
            )
        return papers

    @staticmethod
    def _meta_content(soup: BeautifulSoup, name: str) -> str | None:
        node = soup.select_one(f'meta[name="{name}"]')
        return _compact(node.get("content")) if node and node.get("content") else None

    @staticmethod
    def _subject_from_card(card: BeautifulSoup) -> str | None:
        subject_node = card.select_one("p.subjects")
        if subject_node is None:
            return None
        text = _compact(subject_node.get_text(" ", strip=True))
        return re.sub(r"^Subject\s*:\s*", "", text)

    @staticmethod
    def _external_title_link(card: BeautifulSoup) -> str | None:
        for link in card.select("h2.title > a[href]"):
            href = link.get("href", "")
            if href.startswith("http"):
                return href
        return None

    @staticmethod
    def _pdf_url_from_card(card: BeautifulSoup) -> str | None:
        pdf_link = card.select_one("a.title-pdf")
        if pdf_link is None:
            return None
        for attribute in ("data", "href"):
            value = pdf_link.get(attribute)
            if value:
                return value
        return None

    @staticmethod
    def _keywords_from_card(card: BeautifulSoup) -> list[str]:
        raw = card.get("keywords", "")
        return [item.strip() for item in raw.split(",") if item.strip()]

    @staticmethod
    def _index_from_card(card: BeautifulSoup) -> int | None:
        index_node = card.select_one("span.index")
        return _maybe_int(index_node.get_text(" ", strip=True) if index_node else None)

    @staticmethod
    def _stars_from_card(card: BeautifulSoup, kind: str) -> int | None:
        node = card.select_one(f'sup[id^="{kind}-stars-"]')
        return _maybe_int(node.get_text(" ", strip=True) if node else None)


def render_records(records: Sequence[PaperRecord]) -> str:
    lines: list[str] = []
    for idx, record in enumerate(records, 1):
        where = record.venue or "Unknown venue"
        if record.group:
            where = f"{where} - {record.group}"
        lines.append(f"{idx}. {record.title}")
        lines.append(f"   Where: {where}")
        lines.append(f"   Authors: {', '.join(record.authors[:6]) or 'Unknown'}")
        lines.append(f"   Official: {record.official_url or 'N/A'}")
        lines.append(f"   PDF: {record.pdf_url or 'N/A'}")
        lines.append(f"   Papers.cool: {record.papers_cool_url or 'N/A'}")
        lines.append(f"   External links: {'yes' if record.verified else 'no'} ({record.verification_note or 'no note'})")
        lines.append(f"   Summary: {_sentence_snippet(record.summary, limit=2, max_chars=280) or 'N/A'}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_record(record: PaperRecord) -> str:
    return render_records([record])


def render_json(data: Any) -> str:
    def default(obj: Any) -> Any:
        if isinstance(obj, PaperRecord):
            return obj.to_dict()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    return json.dumps(data, indent=2, ensure_ascii=False, default=default)
