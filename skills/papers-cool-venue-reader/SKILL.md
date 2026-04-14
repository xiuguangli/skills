---
name: papers-cool-venue-reader
description: 当你需要从 papers.cool 的会场页面查找顶会论文、核验其官方链接或 PDF，并输出结构化元数据或稳定摘要时使用。
---

# Papers Cool 会场论文读取器

## 概述

这个 skill 会把 `papers.cool` 变成一个结构化的会议论文发现工具，适合查找 CVPR、ICCV、ICLR、NeurIPS、ACL、EMNLP 等会议的论文，并输出比临时网页搜索更稳定的结果。

适用场景：

- 从会议页面或会议年份页面中查找已接收论文
- 按关键词、track 或年份筛选某个会场
- 打开一篇论文并返回标题、作者、会议、摘要、官方链接和 PDF 链接
- 下载 `papers.cool` 暴露出来的 PDF
- 基于摘要生成稳定摘要，并可选结合本地 PDF 文本补充信息

不要把这个 skill 当成论文内容判断的唯一事实来源。应将 `papers.cool` 视为发现层，并尽可能对照官方外部页面或 PDF 进行核验。参见 [sources.md](references/sources.md)。

## 脚本入口

默认在 `skills/papers-cool-venue-reader/` 目录执行。

先安装脚本依赖：

```bash
python -m pip install -r requirements.txt
```

如果需要 PDF 提取能力：

```bash
python -m pip install -r requirements-pdf.txt
```

只通过下面这个命令使用：

```bash
python scripts/papers_cool.py --help
```

`python scripts/papers_cool.py` 是这个 skill 唯一支持的 CLI 入口。

## 快速开始

```bash
python scripts/papers_cool.py venue CVPR --year 2025 --limit 5
python scripts/papers_cool.py venue CVPR.2025 --query geometry --limit 5
python scripts/papers_cool.py paper "Dibene_Camera_Resection_from_Known_Line_Pencils_and_a_Radially_Distorted@CVPR2025@CVF"
python scripts/papers_cool.py download-pdf "Dibene_Camera_Resection_from_Known_Line_Pencils_and_a_Radially_Distorted@CVPR2025@CVF"
python scripts/papers_cool.py brief "Dibene_Camera_Resection_from_Known_Line_Pencils_and_a_Radially_Distorted@CVPR2025@CVF"
```

如果环境中安装了 `pypdf`，还可以读取本地 PDF 的预览内容：

```bash
python scripts/papers_cool.py brief "<slug>" --download-pdf --max-pages 4
python scripts/papers_cool.py extract-pdf output/papers/<paper>.pdf --max-pages 4
```

## 工作流程

### 1. 发现论文

当用户想获取某个会议或某一年份的论文时，使用 `venue`：

```bash
python scripts/papers_cool.py venue CVPR --year 2025 --limit 10
python scripts/papers_cool.py venue ICLR.2025 --query agent --limit 8
python scripts/papers_cool.py venue CVPR --year 2025 --group Oral --limit 10
```

使用建议：

- 当用户明确给出年份时，优先使用 `--year`
- 使用 `--query` 对标题、摘要、作者和 `keywords` 做轻量级本地排序
- 只有当会场页面明确暴露了稳定的 track 标签时，才使用 `--group`

### 2. 检查单篇论文

当用户希望获取某条论文记录的结构化元数据时，使用 `paper`：

```bash
python scripts/papers_cool.py paper "<papers-cool-url-or-slug>" --json
```

输出包含：

- `title`
- `authors`
- `summary`
- `venue`
- `group`
- `year`
- `papers_cool_url`
- `official_url`
- `pdf_url`
- `verified`
- `verification_note`

### 3. 先核验，再总结

在把某条记录拿来继续核验或总结之前：

1. 检查是否存在 `official_url`
2. 检查是否存在 `pdf_url`
3. 如果两者都缺失，就说明这条记录暂时没有可直接对照的外部材料

当前不再根据“可信域名白名单”做判定。只要存在外部 `official_url` 或 `pdf_url`，输出里的 `verified` 就会是 `true`，表示这条记录已经带有可进一步核验的外部链接。

### 4. 阅读并生成摘要

使用 `brief` 生成稳定摘要。默认基于摘要内容：

```bash
python scripts/papers_cool.py brief "<slug>"
```

如果环境里有 `pypdf`，则可以通过 `--download-pdf` 加入简短的 PDF 预览：

```bash
python scripts/papers_cool.py brief "<slug>" --download-pdf --max-pages 4
```

对于本地 PDF：

```bash
python scripts/papers_cool.py extract-pdf output/papers/<paper>.pdf --max-pages 4
python scripts/papers_cool.py brief "<slug>" --local-pdf output/papers/<paper>.pdf
```

## 说明

- `papers.cool` 很适合做会场级论文发现，并且会在 HTML 中直接暴露不少有用元数据
- 这个 skill 默认不会使用 `[Kimi]` 章节
- PDF 提取是可选能力，依赖 `pypdf`
- 这个 skill 不会尝试推断前端按钮背后的隐藏 API；它只使用会场页面、论文页面和会场 Atom feed

## 文件

- 脚本入口：`scripts/papers_cool.py`
- CLI 实现：`src/papers_cool_venue_reader/cli.py`
- 主客户端与解析器：`src/papers_cool_venue_reader/client.py`
- 来源策略：`references/sources.md`
