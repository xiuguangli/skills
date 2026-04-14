---
name: research-papers
description: 用于围绕用户给定研究主题生成高质量论文调研。默认先在六大会（CVPR、ICCV、ECCV、ICML、ICLR、NeurIPS）做全量关键词检索，再用 DeepXiv 补充近期 arXiv 论文；每个 topic 默认保留至少 50 篇文献并要求候选池超过 100 篇，逐篇给出中文解读、Mermaid 图和直观例子，最后输出自己的整体理解与重要点。
---

# Research Papers

围绕 `user_prompt` 生成**结构完整、信息量足够、带自己理解的中文论文综述**，而不是简单“搜几篇论文 + 堆表格”。

这个 skill 依赖同仓库中的 sibling skill `papers-cool-venue-reader`。如果是从 GitHub 仓库安装，应该同时安装：

- `skills/research-papers`
- `skills/papers-cool-venue-reader`

这份 skill 的代码框架必须保持**通用**：

- 不要把某个具体研究方向的 `subtopics`、关键词、概念链条、benchmark 名称硬编码进脚本。
- 与方向相关的参数，应该由你先根据 `user_prompt` 做运行时 `topic analysis` 推断出来，再作为参数传给脚本。
- 脚本里的自动推断只能作为 fallback，用于快速试跑；正式调研时，优先显式传入 `aliases`、`subtopics`、`keywords`。
- 固定在代码里的，只能是**通用维度**，例如：问题设定、核心方法、表示/架构、训练策略、benchmark、应用场景、理论分析。

固定顺序：

1. 解析主题与子方向
2. 先做六大会 Venue 全量扫描
3. 再做 ArXiv 补充检索
4. 先解释每个 topic 在研究什么
5. 对每个 topic 至少保留 50 篇论文并逐篇解读
6. 每个 topic 最后再给表格汇总
7. 在全文结尾给出自己的整体理解与重要点

禁止跳过 Venue。禁止只给 ArXiv。禁止直接照搬参考文件的结构或措辞。

## 风格参考

可参考：

- `references/example-survey-embodied-spatial-intelligence.md`

但只能借鉴这些方面：

- 如何先给出结论，再展开结构
- 如何把论文组织成“能力链”或“主线”
- 如何在综述最后给出自己的判断

不要照搬：

- 标题体系
- 段落措辞
- 结论表述
- 论文分组方式

你的最终输出必须比参考稿更强，尤其要更强调：

- 检索范围与筛选逻辑
- 每个 topic 的候选规模与最终保留规模
- 每篇论文的内容解读
- 每篇论文的图示和直观例子
- topic 内部的主线关系
- 你自己的总结判断

## 自动化脚本

优先用脚本完成候选收集和初稿渲染。

## 默认执行方式：两阶段缓存工作流

由于很多运行环境（尤其沙箱）不能稳定访问 `papers.cool` / `deepxiv`，这个 skill 默认采用**两阶段**：

1. **prefetch / 预热阶段**：在可联网环境把命令结果写入本地 cache
2. **survey 生成阶段**：在沙箱里用 `--cache-mode read-only` 只读 cache 生成 JSON / Markdown

### 阶段 A：在可联网环境预热 cache

```bash
python scripts/prefetch_topic_cache.py "具身空间智能" \
  --cache-dir /tmp/research_papers_cache \
  --aliases "embodied spatial intelligence,embodied intelligence" \
  --subtopics "问题设定与核心方法,表示、架构与关键机制,训练、优化与适配策略,评测基准与应用场景" \
  --keywords "embodied spatial intelligence,embodied intelligence,spatial reasoning,benchmark"
```

### 阶段 B：在沙箱里只读 cache 生成 survey

```bash
python scripts/survey_topic.py "具身空间智能" \
  --cache-dir /tmp/research_papers_cache \
  --cache-mode read-only \
  --aliases "embodied spatial intelligence,embodied intelligence" \
  --subtopics "问题设定与核心方法,表示、架构与关键机制,训练、优化与适配策略,评测基准与应用场景" \
  --keywords "embodied spatial intelligence,embodied intelligence,spatial reasoning,benchmark" \
  --json-output /tmp/research_papers.json \
  -o /tmp/research_papers.md
```

如果希望生成后立即删掉缓存，可在第二阶段追加：

```bash
--delete-cache-after-run
```

注意：

- 第二阶段必须与第一阶段使用**相同主题和同一组关键参数**，否则会出现 cache miss
- `--cache-mode read-only` 下脚本不会回退联网抓取
- 如果 cache 未预热，脚本会直接报错并提示缺哪个命令缓存

推荐流程是你先做运行时 topic plan，再调用脚本。脚本负责：

1. 接收你显式传入的 `aliases`、`subtopics`、`keywords`
2. 在未显式传参时，才做轻量 fallback 推断
3. 默认按**当前年份起往前回溯 3 年**扫描六大会
4. 用多线程并发抓取 Venue / ArXiv 候选和论文详情
5. 保证每个 topic 的候选池默认超过 100 篇，并保留至少 50 篇论文
6. 输出 topic 解读、topic 导读、逐篇解读、表格汇总、总结草稿
7. 输出中间 JSON 与最终 Markdown
8. 支持先在联网环境 `prefetch`，再在沙箱环境 `read-only` 复用缓存

常用参数：

- `--lookback-years 3`
- `--venue-years <当前年>,<当前年-1>,<当前年-2>,<当前年-3>`
- `--venues CVPR,ICCV,ECCV,ICML,ICLR,NeurIPS`
- `--arxiv-date-from <当前年-3>-01-01`
- `--arxiv-limit 200`
- `--per-topic-papers 50`
- `--min-candidates 120`
- `--max-workers 8`
- `--cache-dir <目录>`：两阶段工作流共享的缓存目录
- `--cache-mode read-only`：沙箱阶段只读缓存，不联网
- `--prefetch-only`：只预热缓存，不输出 survey 文件
- `--aliases <逗号分隔主题别名>`：优先传入英文标准表述、常用缩写
- `--subtopics <逗号分隔子方向>`：覆盖自动拆题
- `--keywords <逗号分隔关键词>`：覆盖自动关键词推断

注意：

- 对中文主题，正式运行时应尽量显式传入至少一个英文 canonical alias，而不是完全依赖 bootstrap
- 这个脚本更适合生成**大体量高质量初稿**
- 默认应优先走“两阶段缓存工作流”，不要在受限沙箱里直接裸跑联网抓取
- 真正的最终稿，仍然应该在脚本结果基础上继续精读与润色
- 论文图示、直观例子和总结判断，不能只凭标题或 abstract 粗糙生成
- 如果自动拆题不理想，优先覆盖运行时参数，而不是改代码去适配某一个方向

## 输入

输入字段固定为：

```text
user_prompt: <string>
```

将其视为用户希望调研的研究问题、方法方向或能力主题。

## 第一步：解析研究方向

从 `user_prompt` 中提取：

- `main_topic`：核心主题
- `aliases`：运行时推断出的主题别名、缩写、英文表达
- `subtopics`：2–5 个子方向
- `keywords`：后续检索要用到的关键词

要求：

- 先给出至少一个可检索的英文标准表述；如果用户原始输入是中文，这一步不能省
- `subtopics` 应该是能支撑综述结构的“能力块”，而不是松散标签
- 如果用户只给了大主题，要主动拆成可写作的子方向
- 如果用户主题很窄，也要把它放到更大的方法链条里理解
- 如果主题缺少明显英文别名，可以先用你的分析补出 canonical alias；脚本内置 bootstrap 只作为补救，不是主流程
- 这里允许使用通用拆题维度，但不允许写入某个具体方向专属的固定子方向表

必要时读取：

- `references/topic-decomposition.md`

## 第二步：Venue 先行，默认六大会全量扫描

默认 Venue 范围固定为：

- `CVPR`
- `ICCV`
- `ECCV`
- `ICML`
- `ICLR`
- `NeurIPS`

默认行为：

- 每个关键词都要在这六大会里找
- 不是“每个会议抓前 8 条”
- 而是先把对应年份的会场候选全拉下来，再做本地关键词筛选

这里的重点是：

- **检索阶段不要用小 limit 截断**
- 你需要先知道“总共有多少相关论文”
- 再从中筛出最值得解读和汇总的代表作

实践上：

- CLI 本身常要求传 `--limit`
- 如果使用 CLI 拉 feed，可以用很大的技术上限，例如 `5000`
- 这个上限只是为了把 venue-year 基本扫全，不是 top-k 排序逻辑

推荐命令模式见：

- `references/cli-recipes.md`

Venue 阶段目标：

- 先建立完整候选池
- 记录大致扫描规模、命中规模、最终入选规模
- 优先留下能代表主线的论文，而不是只留最新的几篇

## 第三步：ArXiv 作为补充，不抢主线

只有在 Venue 候选池已经建立后，才开始 ArXiv。

默认：

- `deepxiv search ... --limit 100`

ArXiv 的作用是：

- 补最近一两年的系统化尝试
- 补 World Model / Agent / VLA / 新 benchmark / 新系统接口
- 让综述看到更前沿的趋势

而不是：

- 用大量 arXiv 冲掉顶会主线
- 把 ArXiv 放在 Venue 之前

## 第四步：对入选论文做“内容级”理解

这是这版 skill 最重要的变化。

每个 topic 下，不能直接先给表格。必须先逐篇讲论文。

### ArXiv 论文

优先使用 `deepxiv` 真正看内容，而不是只看标题：

- `deepxiv paper <id> --head -f json`
- `deepxiv paper <id> --brief -f json`
- `deepxiv paper <id> --section Introduction`
- `deepxiv paper <id> --section Methods`
- `deepxiv paper <id> --section Results`

如果论文很关键，可以继续读全文或关键 section。

### Venue 论文

先用：

- `python ../papers-cool-venue-reader/scripts/papers_cool.py paper <slug> --json`
- `python ../papers-cool-venue-reader/scripts/papers_cool.py brief <slug> --json`

如果能拿到官方 HTML / PDF，优先继续看：

- 论文主页
- 官方 PDF

如果 Venue 论文只能拿到 abstract，就必须控制表述强度：

- 可以写“从摘要看，这篇工作更像是……”
- 不能把没有读到的细节写成确定结论

## 第五步：图示要建立在理解基础上

每篇论文默认都要配一个图示说明，但图示不能是装饰。

优先使用：

- Mermaid 流程图
- Mermaid 结构图
- topic 内部关系图

要求：

- 每篇论文默认都要配一个 Mermaid 图
- 只有在读过论文主要内容后，才画图
- 图要帮助读者理解论文在系统链条里的位置

图示重点不是复刻原论文 figure，而是表达你对论文结构的理解，比如：

- 问题 -> 方法 -> 输出
- 输入 -> 中间表示 -> 决策接口
- 感知 -> 记忆 -> 推理 -> 动作

## 第六步：最终输出结构

最终输出必须是**中文 Markdown 文档**，并遵循下列结构：

````markdown
# 论文调研：<Main Topic>

## 研究主题解析

## 1. <子方向名称>

### Topic 解读
先解释这个 topic 在研究什么、核心能力块是什么、为什么值得单独成章。

### 主题导读
先解释这个 topic 为什么重要、你扫描了多少候选、候选池有多大、最后保留了多少篇论文。

### 逐篇解读
#### 1. [论文标题](URL)
- 发表：CVPR 2025 / arXiv 2025-03
- 作者：...
- 论文内容：用中文解释这篇论文到底在做什么
- 我的理解：解释它真正重要的地方、边界和位置
- 直观例子：用一个场景例子说明这篇论文在干什么

```mermaid
flowchart LR
...
```

### 表格汇总
| 论文标题 | 作者 | 发表 | 一句话概括 | 重要点 |
| --- | --- | --- | --- | --- |

### 本主题小结
总结这个 topic 的主线、分叉和缺口。

## 整体理解与重要点

### 我的整体理解
### 已形成的主线
### 关键缺口
### 重要点
### 建议精读顺序
````

硬性要求：

- 每个 topic 先逐篇解读，再表格汇总
- 每个 topic 前面要先有 `Topic 解读`
- 每个 topic 默认至少保留 50 篇论文
- 每个 topic 的去重候选池默认至少超过 100 篇
- 表格中**不要有 `来源` 列**
- 表格中**不要有单独的 `年份` 列**
- `发表` 列必须直接写成：
  - `CVPR 2025`
  - `ICLR 2024`
  - `arXiv 2025-03`
- ArXiv 的年月可由 `publish_at` 或 arXiv ID 推断

## 写作要求

每篇论文的中文解读至少应覆盖大部分内容：

1. 这篇论文在解决什么问题
2. 它用了什么核心思路
3. 为什么它在当前 topic 中重要
4. 你对它的判断是什么
5. 用一个例子说明它在干什么

注意：

- 不要把论文解读写成摘要翻译
- 要把每篇论文放到该 topic 的主线里解释
- 要有“为什么值得纳入综述”的判断
- 每篇论文默认要有 Mermaid 图和直观例子

## 结尾总结要求

全文结尾不能只是“以上就是调研结果”。

必须用**你自己的理解**对整批论文给出判断，至少覆盖：

- 哪几条主线已经形成
- 哪些能力块已经成熟，哪些还不成熟
- 真正重要的研究接口在哪里
- 继续深读时应该先抓哪几篇

总结必须是你自己的组织与判断，不要只是把前文改写一遍。

## 可扩展性

后续可以继续扩展：

- 论文配图质量增强
- 更细的 topic 内部关系图
- 引用统计
- 与已有工作对比
- 推荐阅读路径自动排序

输出结构与检查清单见：

- `references/output-contract.md`
