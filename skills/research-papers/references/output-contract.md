# 输出契约

## 中间结构

### 主题解析结果

```json
{
  "main_topic": "...",
  "aliases": ["...", "..."],
  "subtopics": ["...", "..."],
  "keywords": ["...", "..."]
}
```

### 检索范围

```json
{
  "venues": ["CVPR", "ICCV", "ECCV", "ICML", "ICLR", "NeurIPS"],
  "venue_years": [2026, 2025, 2024, 2023],
  "arxiv_date_from": "2023-01-01",
  "arxiv_limit": 200,
  "papers_per_topic": 50,
  "min_candidates_per_topic": 120,
  "max_workers": 8,
  "diagram_policy": "per-paper",
  "current_year": 2026
}
```

说明：

- `aliases` 优先来自你在运行时对用户主题的分析；脚本内置 bootstrap 只作为 fallback
- `venue_years` 默认按当前年份起往前回溯 3 年
- `papers_per_topic` 默认至少 `50`
- `min_candidates_per_topic` 默认至少 `100+`
- `diagram_policy` 默认是每篇论文都带 Mermaid 图

### 子方向结构

```json
{
  "name": "...",
  "topic_overview": "...",
  "intro": "...",
  "summary": "...",
  "search_stats": {
    "venue": {
      "records_scanned": 0,
      "matches": 0
    },
    "arxiv": {
      "matches": 0
    },
    "candidate_pool_size": 0,
    "saved_papers": 50
  },
  "papers": [
    {
      "title": "...",
      "authors": "...",
      "published": "CVPR 2026",
      "url": "...",
      "source": "venue",
      "analysis": "...",
      "table_summary": "...",
      "insight": "...",
      "example": "...",
      "diagram": "flowchart LR ..."
    }
  ]
}
```

### 论文记录字段

每篇论文至少应有这些字段：

```json
{
  "title": "",
  "authors": "",
  "published": "CVPR 2026 / arXiv 2026-03",
  "url": "",
  "source": "venue | arxiv",
  "analysis": "",
  "table_summary": "",
  "insight": "",
  "example": "",
  "diagram": ""
}
```

说明：

- `published` 直接合并 venue 与年份，或 `arXiv + 年月`
- `analysis` 是逐篇解读区的正文，不是摘要翻译
- `table_summary` 是表格中的一句话概括
- `insight` 是你对这篇论文最重要之处的判断
- `example` 是帮助理解论文的直观场景例子
- `diagram` 默认非空，应为 Mermaid 代码

## 最终 Markdown 结构

````markdown
# 论文调研：<Main Topic>

## 研究主题解析

## 1. <子方向名称>

### Topic 解读
<解释这个 topic 在研究什么、为什么重要>

### 主题导读
<说明这个 topic 的价值、扫描规模、候选池规模、最终保留论文数>

### 逐篇解读
#### 1. [论文标题](URL)
- 发表：CVPR 2026 / arXiv 2026-03
- 作者：...
- 论文内容：...
- 我的理解：...
- 直观例子：...

```mermaid
flowchart LR
...
```

### 表格汇总
| 论文标题 | 作者 | 发表 | 一句话概括 | 重要点 |
| --- | --- | --- | --- | --- |

### 本主题小结
<总结该 topic 的主线、分叉、缺口>

## 整体理解与重要点

### 我的整体理解
### 已形成的主线
### 关键缺口
### 重要点
### 建议精读顺序
````

## 强约束

输出前务必确认：

- 先有 `Topic 解读`，再有 `主题导读`，再有 `逐篇解读`，最后才是 `表格汇总`
- 每个 topic 默认至少保留 `50` 篇论文
- 每个 topic 的去重候选池默认至少超过 `100` 篇
- 表格中没有 `来源` 列
- 表格中没有独立 `年份` 列
- `发表` 列直接写 `会议 + 年份` 或 `arXiv + 年月`
- 每篇论文标题都有可点击链接
- 每篇论文至少有中文内容解读、`我的理解`、`直观例子` 和 Mermaid 图
- 文末有明确的整体理解与重要点，而不是泛泛收尾

## 建议质量门槛

高质量输出通常应满足：

- 能解释“为什么选这些论文，而不是别的论文”
- 能解释“这一组论文之间是什么关系”
- 能解释“这一组工作补的是系统链条中的哪一块”
- 能指出“下一步真正值得继续读或继续做的方向”
