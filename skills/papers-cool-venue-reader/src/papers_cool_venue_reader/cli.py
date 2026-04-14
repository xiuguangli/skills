from __future__ import annotations

import argparse
import sys

from .client import PapersCoolClient, PapersCoolError, render_json, render_record, render_records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find conference papers from papers.cool and verify official links."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    venue_parser = subparsers.add_parser("venue", help="List papers from a venue or venue-year page")
    venue_parser.add_argument("venue", help="Venue label such as CVPR or CVPR.2025")
    venue_parser.add_argument("--year", type=int, default=None, help="Optional year, e.g. 2025")
    venue_parser.add_argument("--group", default=None, help="Filter by group/track such as Oral")
    venue_parser.add_argument("--query", default=None, help="Keyword filter over title, summary, authors, and keywords")
    venue_parser.add_argument("--limit", type=int, default=10, help="Number of results to print")
    venue_parser.add_argument("--json", action="store_true", help="Print JSON instead of formatted text")

    feed_parser = subparsers.add_parser("feed", help="Read venue Atom feed")
    feed_parser.add_argument("venue", help="Venue label such as CVPR or CVPR.2025")
    feed_parser.add_argument("--year", type=int, default=None, help="Optional year, e.g. 2025")
    feed_parser.add_argument("--limit", type=int, default=10, help="Number of feed entries to print")
    feed_parser.add_argument("--json", action="store_true", help="Print JSON instead of formatted text")

    paper_parser = subparsers.add_parser("paper", help="Fetch one paper page from papers.cool")
    paper_parser.add_argument("paper", help="papers.cool paper url or slug")
    paper_parser.add_argument("--json", action="store_true", help="Print JSON instead of formatted text")

    download_parser = subparsers.add_parser("download-pdf", help="Download a PDF discovered through papers.cool")
    download_parser.add_argument("paper", help="papers.cool paper url or slug")
    download_parser.add_argument("--output-dir", default="output/papers", help="Directory where PDFs are saved")
    download_parser.add_argument("--filename", default=None, help="Optional custom filename")

    extract_parser = subparsers.add_parser("extract-pdf", help="Extract text from a local PDF")
    extract_parser.add_argument("pdf", help="Local PDF path")
    extract_parser.add_argument("--max-pages", type=int, default=6, help="How many pages to read")

    brief_parser = subparsers.add_parser("brief", help="Produce a deterministic brief from metadata and optional PDF text")
    brief_parser.add_argument("paper", help="papers.cool paper url or slug")
    brief_parser.add_argument("--local-pdf", default=None, help="Use an existing local PDF for extra context")
    brief_parser.add_argument(
        "--download-pdf",
        action="store_true",
        help="Temporarily download the paper PDF and include a short preview if pypdf is installed",
    )
    brief_parser.add_argument("--max-pages", type=int, default=6, help="How many PDF pages to read")
    brief_parser.add_argument("--json", action="store_true", help="Print JSON instead of text")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    client = PapersCoolClient()

    try:
        if args.command == "venue":
            records = client.list_venue(
                args.venue,
                year=args.year,
                group=args.group,
                query=args.query,
                limit=args.limit,
            )
            print(render_json(records) if args.json else render_records(records))
            return 0

        if args.command == "feed":
            records = client.list_feed(args.venue, year=args.year, limit=args.limit)
            print(render_json(records) if args.json else render_records(records))
            return 0

        if args.command == "paper":
            record = client.get_paper(args.paper)
            print(render_json(record) if args.json else render_record(record))
            return 0

        if args.command == "download-pdf":
            pdf_path = client.download_pdf(args.paper, output_dir=args.output_dir, filename=args.filename)
            print(pdf_path)
            return 0

        if args.command == "extract-pdf":
            text = client.extract_pdf_text(args.pdf, max_pages=args.max_pages)
            print(text)
            return 0

        if args.command == "brief":
            if args.download_pdf:
                payload = client.brief_with_download(args.paper, max_pages=args.max_pages)
            else:
                payload = client.brief(args.paper, local_pdf=args.local_pdf, max_pages=args.max_pages)
            print(render_json(payload) if args.json else payload["brief"])
            return 0
    except PapersCoolError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit("Run this tool via 'python scripts/papers_cool.py' from the skill directory.")
