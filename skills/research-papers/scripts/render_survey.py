#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def clean_text(value):
    return str(value or "").replace("\n", " ").strip()


def table_cell(value):
    text = clean_text(value)
    if not text:
        return "-"
    return text.replace("|", "\\|")


def paper_link(paper):
    title = table_cell(paper.get("title", ""))
    url = clean_text(paper.get("url", ""))
    if url and title != "-":
        return f"[{title}]({url})"
    return title


def format_published(paper):
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


def legacy_intro(subtopic, papers):
    return f"这一部分聚焦“{subtopic.get('name', '')}”。以下内容是根据现有论文列表自动整理出的基础解读，正式综述写作时仍建议补充正文精读。"


def legacy_summary(subtopic, papers):
    return f"这一 topic 当前更像是在补齐“{subtopic.get('name', '')}”相关的能力件，后续如果要写成高质量综述，关键是进一步补上正文精读后的系统判断。"


def legacy_topic_overview(subtopic, papers):
    return f"这个 topic 主要围绕“{subtopic.get('name', '')}”展开，关注该方向里的核心能力模块、系统接口和代表性方法。"


def merge_legacy_papers(subtopic):
    if subtopic.get("papers"):
        return subtopic["papers"]

    papers = []
    for paper in subtopic.get("venue_papers", []):
        papers.append(
            {
                **paper,
                "published": format_published(paper),
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


def render_topic_table(lines, papers):
    lines.append("| 论文标题 | 作者 | 发表 | 一句话概括 | 重要点 |")
    lines.append("| --- | --- | --- | --- | --- |")
    if papers:
        for paper in papers:
            lines.append(
                f"| {paper_link(paper)} | {table_cell(paper.get('authors', ''))} | "
                f"{table_cell(format_published(paper))} | {table_cell(paper.get('table_summary', ''))} | "
                f"{table_cell(paper.get('insight', paper.get('advisor_note', '')))} |"
            )
    else:
        lines.append("| 暂无结果 | - | - | - | - |")
    lines.append("")


def render_overall_summary(lines, summary):
    if not summary:
        return
    lines.append("## 整体理解与重要点")
    lines.append("")
    overview = clean_text(summary.get("overview", ""))
    if overview:
        lines.append("### 我的整体理解")
        lines.append("")
        lines.append(overview)
        lines.append("")
    trends = summary.get("trends", [])
    if trends:
        lines.append("### 已形成的主线")
        for item in trends:
            lines.append(f"- {clean_text(item)}")
        lines.append("")
    gaps = summary.get("gaps", [])
    if gaps:
        lines.append("### 关键缺口")
        for item in gaps:
            lines.append(f"- {clean_text(item)}")
        lines.append("")
    important_points = summary.get("important_points") or summary.get("opportunities", [])
    if important_points:
        lines.append("### 重要点")
        for item in important_points:
            lines.append(f"- {clean_text(item)}")
        lines.append("")
    reading_path = summary.get("reading_path", [])
    if reading_path:
        lines.append("### 建议精读顺序")
        for index, item in enumerate(reading_path, start=1):
            lines.append(f"{index}. {clean_text(item)}")
        lines.append("")


def render(data):
    lines = [f"# 论文调研：{data['main_topic']}", ""]

    parsed_subtopics = data.get("parsed_subtopics") or [sub.get("name", "") for sub in data.get("subtopics", [])]
    keywords = data.get("keywords", [])
    search_scope = data.get("search_scope", {})

    lines.append("## 研究主题解析")
    lines.append("")
    lines.append(f"- 核心主题：{data['main_topic']}")
    if parsed_subtopics:
        lines.append(f"- 子方向：{'；'.join([item for item in parsed_subtopics if item])}")
    if keywords:
        lines.append(f"- 检索关键词：{'；'.join([item for item in keywords if item])}")
    if search_scope:
        venues = " / ".join(search_scope.get("venues", []))
        years = "、".join(str(year) for year in search_scope.get("venue_years", []))
        lines.append(f"- Venue 默认范围：{venues or '-'}")
        lines.append(f"- Venue 检索年份：{years or '-'}")
        lines.append(f"- ArXiv 起始日期：{search_scope.get('arxiv_date_from', '-')}")
        lines.append(f"- ArXiv 检索上限：{search_scope.get('arxiv_limit', '-')}")
        lines.append(f"- 每个 topic 保留论文数：{search_scope.get('papers_per_topic', search_scope.get('per_source', '-'))}")
        lines.append(f"- 每个 topic 最少候选数：{search_scope.get('min_candidates_per_topic', '-')}")
        lines.append(f"- 抓取线程数：{search_scope.get('max_workers', '-')}")
    lines.append("")

    for index, subtopic in enumerate(data.get("subtopics", []), start=1):
        papers = merge_legacy_papers(subtopic)
        lines.append(f"## {index}. {subtopic['name']}")
        lines.append("")
        lines.append("### Topic 解读")
        lines.append(clean_text(subtopic.get("topic_overview", "")) or legacy_topic_overview(subtopic, papers))
        lines.append("")
        lines.append("### 主题导读")
        lines.append(clean_text(subtopic.get("intro", "")) or legacy_intro(subtopic, papers))
        lines.append("")
        lines.append("### 逐篇解读")
        lines.append("")

        for paper_index, paper in enumerate(papers, start=1):
            lines.append(f"#### {paper_index}. {paper_link(paper)}")
            lines.append(f"- 发表：{format_published(paper)}")
            lines.append(f"- 作者：{clean_text(paper.get('authors', '')) or '-'}")
            lines.append(f"- 论文内容：{clean_text(paper.get('analysis', '')) or clean_text(paper.get('abstract_summary', '')) or '-'}")
            insight = clean_text(paper.get("insight", paper.get("advisor_note", "")))
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

    render_overall_summary(lines, data.get("overall_summary", {}))
    return "\n".join(lines).rstrip() + "\n"


def main():
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
