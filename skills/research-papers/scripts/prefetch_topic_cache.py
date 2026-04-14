#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Prefetch research-papers cache in a networked environment.")
    parser.add_argument("topic", help="研究主题，例如：具身空间智能")
    parser.add_argument("--cache-dir", required=True, help="预热缓存目录")
    parser.add_argument("--aliases", help="逗号分隔的主题别名、英文标准表述或缩写")
    parser.add_argument("--subtopics", help="逗号分隔的子方向，覆盖自动拆题")
    parser.add_argument("--keywords", help="逗号分隔的检索关键词，覆盖自动关键词生成")
    parser.add_argument("--lookback-years", type=int, default=3)
    parser.add_argument("--venue-years", help="Venue 检索年份，逗号分隔")
    parser.add_argument("--venues", default="CVPR,ICCV,ECCV,ICML,ICLR,NeurIPS")
    parser.add_argument("--arxiv-date-from", help="ArXiv 起始日期")
    parser.add_argument("--arxiv-limit", type=int, default=200)
    parser.add_argument("--per-topic-papers", type=int, default=50)
    parser.add_argument("--min-candidates", type=int, default=120)
    parser.add_argument("--max-workers", type=int, default=8)
    args = parser.parse_args()

    survey_script = Path(__file__).with_name("survey_topic.py")
    cmd = [
        sys.executable,
        str(survey_script),
        args.topic,
        "--cache-dir",
        args.cache_dir,
        "--cache-mode",
        "read-write",
        "--prefetch-only",
        "--lookback-years",
        str(args.lookback_years),
        "--venues",
        args.venues,
        "--arxiv-limit",
        str(args.arxiv_limit),
        "--per-topic-papers",
        str(args.per_topic_papers),
        "--min-candidates",
        str(args.min_candidates),
        "--max-workers",
        str(args.max_workers),
    ]

    for flag, value in [
        ("--aliases", args.aliases),
        ("--subtopics", args.subtopics),
        ("--keywords", args.keywords),
        ("--venue-years", args.venue_years),
        ("--arxiv-date-from", args.arxiv_date_from),
    ]:
        if value:
            cmd.extend([flag, value])

    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
