# 输出契约（v2）

本文件是 `research-papers` 的**单一事实来源**。如果 `SKILL.md`、旧样例、旧脚本帮助文本或历史 JSON 与这里冲突，以本文件为准。

## 1. 主题解析输出

在真正检索前，先得到运行时 topic plan：

```json
{
  "main_topic": "...",
  "aliases": ["...", "..."],
  "subtopics": ["...", "..."],
  "keywords": ["...", "..."]
}
```

最低要求：

- `aliases` 必须尽量包含至少一个英文 canonical alias。
- `subtopics` 应该是 2–5 个可以支撑正文结构的能力块，而不是散乱标签。
- `keywords` 要可直接用于检索，而不是泛化词。

## 2. 检索范围与选择契约

```json
{
  "search_scope": {
    "venues": ["CVPR", "ICCV", "ECCV", "ICML", "ICLR", "NeurIPS"],
    "venue_years": [2026, 2025, 2024, 2023],
    "arxiv_date_from": "2023-01-01",
    "arxiv_limit": 200,
    "max_workers": 8
  },
  "selection_contract": {
    "min_total_papers": 200,
    "per_topic_floor": null,
    "allocation_strategy": "derived_topic_floor",
    "rebalance_strategy": "density_then_diversity"
  }
}
```

说明：

- 公开主契约是 `min_total_papers >= 200`。
- `per_topic_floor` 仅表示迁移期兼容底线；它不是主选择目标。
- `allocation_strategy = derived_topic_floor` 表示先从总量目标推导 topic 初始目标。
- `rebalance_strategy = density_then_diversity` 表示在 topic 组织不丢失的前提下，优先用高密度 topic 补足总量，再尽量保留多样性。

## 3. Canonical v2 JSON schema

```json
{
  "schema_version": "2.0",
  "main_topic": "...",
  "parsed_subtopics": ["..."],
  "topic_analysis": {
    "aliases": ["..."],
    "subtopics": [
      {
        "name": "...",
        "modifiers": ["..."],
        "rationale": "..."
      }
    ]
  },
  "search_scope": {
    "venues": ["CVPR", "ICCV", "ECCV", "ICML", "ICLR", "NeurIPS"],
    "venue_years": [2026, 2025, 2024, 2023],
    "arxiv_date_from": "2023-01-01",
    "arxiv_limit": 200,
    "max_workers": 8
  },
  "selection_contract": {
    "min_total_papers": 200,
    "per_topic_floor": null,
    "allocation_strategy": "derived_topic_floor",
    "rebalance_strategy": "density_then_diversity"
  },
  "selection_status": "ok",
  "requirement_failures": [
    {
      "code": "min_total_papers_unmet",
      "message": "Curated papers below required minimum.",
      "expected": 200,
      "actual": 173
    }
  ],
  "totals": {
    "candidate_pool_size": 0,
    "curated_papers": 0,
    "topic_count": 0
  },
  "subtopics": [
    {
      "name": "...",
      "topic_overview": "...",
      "intro": "...",
      "summary": "...",
      "allocation": {
        "target": 0,
        "selected": 0,
        "rebalance_delta": 0
      },
      "search_stats": {
        "venue": {
          "records_scanned": 0,
          "matches": 0
        },
        "arxiv": {
          "matches": 0
        },
        "candidate_pool_size": 0
      },
      "papers": [
        {
          "paper_id": "...",
          "title": "...",
          "authors": "...",
          "published": "CVPR 2026",
          "paper_url": "...",
          "access_url": "...",
          "pdf_url": "...",
          "source": "venue | arxiv",
          "evidence_status": "full_text_verified | abstract_only | metadata_only | legacy_unlabeled",
          "evidence_note": "...",
          "analysis": "...",
          "table_summary": "...",
          "insight": "...",
          "example": "...",
          "diagram": "flowchart LR ..."
        }
      ]
    }
  ],
  "ending": {
    "synthesis": "...",
    "important_papers": ["paper_id"],
    "topic_timelines": [
      {
        "topic_name": "...",
        "representative_papers": [
          {
            "paper_ref": "paper_id",
            "published": "ICLR 2025",
            "title": "...",
            "why_representative": "...",
            "relation_label": "extends"
          }
        ]
      }
    ],
    "reading_recommendations": ["..."]
  }
}
```

## 4. 字段级强约束

### 4.1 顶层字段

- `schema_version`：必须是字符串 `"2.0"`。
- `selection_status`：当前允许值：
  - `ok`
  - `blocked_insufficient_candidates`
- `requirement_failures`：
  - `selection_status = ok` 时通常为空数组。
  - 非空时，每项必须至少包含 `code`、`message`、`expected`、`actual`。
- `totals.candidate_pool_size`：全局去重候选池规模。
- `totals.curated_papers`：最终实际保留论文数。
- `totals.topic_count`：最终 topic 数量。

### 4.2 Topic 字段

每个 `subtopics[*]` 必须至少包含：

- `name`
- `topic_overview`
- `intro`
- `summary`
- `allocation.target`
- `allocation.selected`
- `allocation.rebalance_delta`
- `search_stats.venue.records_scanned`
- `search_stats.venue.matches`
- `search_stats.arxiv.matches`
- `search_stats.candidate_pool_size`
- `papers`

约束：

- `allocation.target` 是派生目标。
- `allocation.selected` 是最终实际选中数。
- `allocation.rebalance_delta` 为相对派生目标的增减量，可正可负。
- `papers` 必须保留 topic 内部顺序，以便支撑正文叙事。

### 4.3 Paper 字段

每篇论文必须至少包含：

- `paper_id`
- `title`
- `authors`
- `published`
- `paper_url`
- `access_url`
- `source`
- `evidence_status`
- `evidence_note`
- `analysis`
- `table_summary`
- `insight`
- `example`

附加规则：

- `paper_url`：标题主链接的目标地址。
- `access_url`：官方 landing page、abs page 或等价访问入口；即使 `paper_url` 存在，也不能省略。
- `pdf_url`：有则提供；没有时允许缺失或为 `null`。
- `published`：必须直接写成 `会议 + 年份` 或 `arXiv + 年月`。
- `evidence_status` 当前允许值：
  - `full_text_verified`
  - `abstract_only`
  - `metadata_only`
  - `legacy_unlabeled`
- `evidence_note`：
  - `full_text_verified` 时可简短说明全文来源。
  - 其他状态时必须解释为什么证据受限。
- `diagram`：
  - 强偏好字段。
  - 当证据允许且论文理解足够时应提供。
  - 如果缺失，必须能从 `evidence_status` / `evidence_note` 合理解释。

### 4.4 Ending 字段

- `ending.synthesis`：供 `## 综合总结` 使用的主总结正文。
- `ending.important_papers`：必须引用前文已出现的 `paper_id`，不允许凭空造新条目。
- `ending.topic_timelines`：
  - 必须是**按 topic 分线**的数据结构。
  - 每个 topic 最多 **5** 篇代表论文。
- `ending.topic_timelines[*].representative_papers[*].relation_label` 允许值仅有：
  - `opens`
  - `extends`
  - `benchmarks`
  - `scales`
  - `synthesizes`
- `ending.reading_recommendations`：是后续精读建议列表，不是前文摘要的简单重复。

## 5. 失败 / 降级策略

当重平衡后 `totals.curated_papers < selection_contract.min_total_papers` 时，必须采用**degraded blocking output**：

1. 仍然写出 partial JSON 与 partial Markdown。
2. 顶层设置：
   - `selection_status = "blocked_insufficient_candidates"`
   - `requirement_failures` 非空，至少有一项 `code = "min_total_papers_unmet"`
3. Markdown 中要有醒目的警告区块，明确说明总量硬要求未满足。
4. CLI 进程应以**非零退出码**结束；约定退出码为 `2`。

禁止的行为：

- 静默截断后仍然宣称成功
- 因为未达 200 篇而不输出任何结果
- 用空洞描述凑数掩盖不足

## 6. Legacy 1.x 渲染兼容策略

如果输入 payload 缺少 `schema_version`，渲染器必须进入显式兼容模式：

1. 将该 payload 视为 legacy `1.x`。
2. 映射 `url -> access_url` 用于展示。
3. 推断 `evidence_status = legacy_unlabeled`。
4. 在 Markdown 中输出明确的兼容性警告，说明该数据缺少 v2 的链接 / 证据 / timeline 语义。
5. **不要伪造** `topic_timelines`、`pdf_url` 或其他 v2-only 字段。

## 7. 最终 Markdown 结构

最终 Markdown 必须至少满足：

````markdown
# 论文调研：<Main Topic>

## 研究主题解析

## 1. <子方向名称>

### Topic 解读

### 主题导读

### 逐篇解读
#### 1. [论文标题](paper_url)
- 发表：CVPR 2026 / arXiv 2026-03
- 作者：...
- 访问链接：...
- PDF：...
- 证据等级：full_text_verified / abstract_only / metadata_only / legacy_unlabeled
- 说明：...
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

## 综合总结

### 我的总体判断

### 重要代表文献

### Topic 演化时间线

### 后续精读建议
````

固定要求：

- `## 综合总结` 与 4 个三级标题必须使用**完全相同的节名**。
- timeline 部分只放代表论文，不放全部论文。
- 表格里不单列 `来源` 或 `年份`。
- 每篇论文标题都必须可点击。
- `PDF：` 只有在 `pdf_url` 存在时显示；`访问链接：` 至少应显示一个。
- `证据等级：` 在 v2 输出中必须可见；legacy fallback 也必须显式标成 `legacy_unlabeled`。

## 8. 质量门槛清单

输出前至少自检：

- 是否明确说明了为什么是这些 topic，而不是平铺关键词？
- 是否能从 JSON 直接恢复出 topic 分配 / 重平衡信息？
- 是否每篇论文都具备同一组最小信息包，而不是只有少数代表作才完整？
- 是否所有证据受限论文都降低了断言强度并明确标注？
- 是否结尾真的给出了 topic-wise 的代表论文时间线，而不是全局平铺列表？
- 是否在 `<200` 时明确进入 blocking degraded output，而不是静默成功？
