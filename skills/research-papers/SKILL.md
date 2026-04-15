---
name: research-papers
description: 围绕用户给定研究主题生成高质量中文论文调研：自动拆解 topic，先扫六大会再补 arXiv，默认全局保留 >=200 篇并按 topic 组织；每篇论文输出链接、证据等级、内容解读、自己的理解和直观例子，在证据允许时补图，最后给出综合总结、代表文献与 Topic 演化时间线。
---

# Research Papers

围绕 `user_prompt` 生成**研究助理式、结构完整、信息量足够、带自己理解的中文论文综述**，而不是简单“搜几篇论文 + 堆列表 / 堆表格”。

这个 skill 依赖同仓库中的 sibling skill `papers-cool-venue-reader`。如果是从 GitHub 仓库安装，应该同时安装：

- `skills/research-papers`
- `skills/papers-cool-venue-reader`

这份 skill 的代码框架必须保持**通用**：

- 不要把某个具体研究方向的 `subtopics`、关键词、概念链条、benchmark 名称硬编码进脚本。
- 与方向相关的参数，应该由你先根据 `user_prompt` 做运行时 `topic analysis` 推断出来，再作为参数传给脚本。
- 脚本里的自动推断只能作为 fallback，用于快速试跑；正式调研时，优先显式传入 `aliases`、`subtopics`、`keywords`。
- 固定在代码里的，只能是**通用维度**，例如：问题设定、核心方法、表示/架构、训练策略、benchmark、应用场景、理论分析。

## 核心公开契约

以下行为是这版 skill 的主契约：

1. 输入保持自由文本；必须先自动拆成可检索的 `main_topic / aliases / subtopics / keywords`。
2. 检索顺序固定为：**先六大会（CVPR、ICCV、ECCV、ICML、ICLR、NeurIPS），再 arXiv**。
3. 最终交付必须是**中文 Markdown 报告**。
4. 最终保留论文数的主目标是**全局不少于 200 篇**，而不是“每个 topic 默认 50 篇”。
5. 正文必须按 topic 组织，并在每个 topic 内先讲研究主线，再逐篇解读，再做表格汇总。
6. 每篇论文都要尽量达到同一组**最小信息包**：
   - 可点击主链接（`paper_url`）
   - 访问链接（`access_url`）
   - 有 PDF 时提供 `pdf_url`
   - `evidence_status` 与 `evidence_note`
   - 中文内容解读
   - 你的判断 / insight
   - 直观例子
   - 在证据允许时补图（优先 Mermaid）
7. 如果只有 abstract 或 metadata，必须明确标注证据限制，不能把不确定内容写成已核验事实。
8. 结尾必须包含固定章节：
   - `## 综合总结`
   - `### 我的总体判断`
   - `### 重要代表文献`
   - `### Topic 演化时间线`
   - `### 后续精读建议`
9. 禁止把输出退化成 flat list / 论文堆砌；也禁止默认采取“少量核心深读，其余浅写”的分层策略。

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
- 全局候选规模、总保留规模、topic 分配与重平衡结果
- 每个 topic 的主线关系与代表工作
- 每篇论文的内容解读、证据状态与直观例子
- 证据受限时的明确提示
- 你自己的综合判断与 topic 演化时间线

## 自动化脚本

优先用脚本完成候选收集和初稿渲染。

## 默认执行方式：两阶段缓存工作流

由于很多运行环境（尤其沙箱）不能稳定访问 `papers.cool` / `deepxiv`，这个 skill 默认采用**两阶段**：

1. **prefetch / 预热阶段**：在可联网环境把命令结果写入本地 cache
2. **survey 生成阶段**：在沙箱里用 `--cache-mode read-only` 只读 cache 生成 JSON / Markdown

### 阶段 A：在可联网环境预热 cache

```bash
python scripts/prefetch_topic_cache.py "具身空间智能"   --cache-dir /tmp/research_papers_cache   --aliases "embodied spatial intelligence,embodied intelligence"   --subtopics "问题设定与核心方法,表示、架构与关键机制,训练、优化与适配策略,评测基准与应用场景"   --keywords "embodied spatial intelligence,embodied intelligence,spatial reasoning,benchmark"   --min-total-papers 200
```

### 阶段 B：在沙箱里只读 cache 生成 survey

```bash
python scripts/survey_topic.py "具身空间智能"   --cache-dir /tmp/research_papers_cache   --cache-mode read-only   --aliases "embodied spatial intelligence,embodied intelligence"   --subtopics "问题设定与核心方法,表示、架构与关键机制,训练、优化与适配策略,评测基准与应用场景"   --keywords "embodied spatial intelligence,embodied intelligence,spatial reasoning,benchmark"   --min-total-papers 200   --json-output /tmp/research_papers.json   -o /tmp/research_papers.md
```

如果希望生成后立即删掉缓存，可在第二阶段追加：

```bash
--delete-cache-after-run
```

注意：

- 第二阶段必须与第一阶段使用**相同主题和同一组关键参数**，否则会出现 cache miss。
- `--cache-mode read-only` 下脚本不会回退联网抓取。
- 如果 cache 未预热，脚本会直接报错并提示缺哪个命令缓存。
- `--min-total-papers` 是主契约；`--per-topic-papers` 仅作为迁移期兼容的 topic 初始底线，不改变全局总量优先级。

推荐流程是你先做运行时 topic plan，再调用脚本。脚本负责：

1. 接收你显式传入的 `aliases`、`subtopics`、`keywords`
2. 在未显式传参时，才做轻量 fallback 推断
3. 默认按**当前年份起往前回溯 3 年**扫描六大会
4. 用多线程并发抓取 Venue / ArXiv 候选和论文详情
5. 以 `>=200` 总保留为主目标，按 topic 推导初始配额并做重平衡
6. 输出 topic 解读、topic 导读、逐篇解读、表格汇总、总结草稿与 topic 时间线数据
7. 输出中间 JSON 与最终 Markdown
8. 支持先在联网环境 `prefetch`，再在沙箱环境 `read-only` 复用缓存

常用参数：

- `--lookback-years 3`
- `--venue-years <当前年>,<当前年-1>,<当前年-2>,<当前年-3>`
- `--venues CVPR,ICCV,ECCV,ICML,ICLR,NeurIPS`
- `--arxiv-date-from <当前年-3>-01-01`
- `--arxiv-limit 200`
- `--min-total-papers 200`
- `--per-topic-papers <deprecated compatibility floor>`
- `--max-workers 8`
- `--cache-dir <目录>`：两阶段工作流共享的缓存目录
- `--cache-mode read-only`：沙箱阶段只读缓存，不联网
- `--prefetch-only`：只预热缓存，不输出 survey 文件
- `--aliases <逗号分隔主题别名>`：优先传入英文标准表述、常用缩写
- `--subtopics <逗号分隔子方向>`：覆盖自动拆题
- `--keywords <逗号分隔关键词>`：覆盖自动关键词推断

注意：

- 对中文主题，正式运行时应尽量显式传入至少一个英文 canonical alias，而不是完全依赖 bootstrap。
- 这个脚本更适合生成**大体量高质量初稿**。
- 默认应优先走“两阶段缓存工作流”，不要在受限沙箱里直接裸跑联网抓取。
- 真正的最终稿，仍然应该在脚本结果基础上继续精读与润色。
- 图示、直观例子和总结判断，不能只凭标题或 abstract 粗糙生成。
- 如果自动拆题不理想，优先覆盖运行时参数，而不是改代码去适配某一个方向。
- 字段与章节的最终权威定义见 `references/output-contract.md`；如果旧样例或旧脚本说明与它冲突，以 output-contract 为准。

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

- 先给出至少一个可检索的英文标准表述；如果用户原始输入是中文，这一步不能省。
- `subtopics` 应该是能支撑综述结构的“能力块”，而不是松散标签。
- 如果用户只给了大主题，要主动拆成可写作的子方向。
- 如果用户主题很窄，也要把它放到更大的方法链条里理解。
- 如果主题缺少明显英文别名，可以先用你的分析补出 canonical alias；脚本内置 bootstrap 只作为补救，不是主流程。
- 这里允许使用通用拆题维度，但不允许写入某个具体方向专属的固定子方向表。

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

- 每个关键词都要在这六大会里找。
- 不是“每个会议抓前 8 条”。
- 而是先把对应年份的会场候选全拉下来，再做本地关键词筛选。

这里的重点是：

- **检索阶段不要用小 limit 截断**。
- 你需要先知道“总共有多少相关论文”。
- 再从中筛出最值得解读和汇总的代表作。

实践上：

- CLI 本身常要求传 `--limit`。
- 如果使用 CLI 拉 feed，可以用很大的技术上限，例如 `5000`。
- 这个上限只是为了把 venue-year 基本扫全，不是 top-k 排序逻辑。

原始抓取命令模式见：

- `references/cli-recipes.md`

但请记住：`cli-recipes.md` 主要提供**检索动作模板**，不定义这版 skill 的主契约；总量目标、证据字段和最终章节结构以本文件和 `references/output-contract.md` 为准。

Venue 阶段目标：

- 先建立完整候选池
- 记录大致扫描规模、命中规模、最终入选规模
- 优先留下能代表主线的论文，而不是只留最新的几篇

## 第三步：ArXiv 作为补充，不抢主线

只有在 Venue 候选池已经建立后，才开始 ArXiv。

ArXiv 的作用是：

- 补最近一两年的系统化尝试
- 补 World Model / Agent / VLA / 新 benchmark / 新系统接口
- 让综述看到更前沿的趋势

而不是：

- 用大量 arXiv 冲掉顶会主线
- 把 ArXiv 放在 Venue 之前

## 第四步：按全局总量目标筛选，并在 topic 内逐篇理解

这是这版 skill 的关键要求。

- 主选择目标是**全局总保留 >= 200**。
- topic 仍然是正文组织和候选聚类的骨架。
- 不要把“每个 topic 50 篇”当成主约束；topic 的初始目标数应该由总量、topic 数和候选密度推导，再做 rebalance。
- 如果最终总量仍然 `< 200`，也必须输出结果，但要明确标记 `selection_status = blocked_insufficient_candidates` 并解释 `requirement_failures`，而不是静默成功。

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
- 必须通过 `evidence_status` / `evidence_note` 明说证据边界

## 第五步：图示是强偏好，不是虚假承诺

优先使用：

- Mermaid 流程图
- Mermaid 结构图
- topic 内部关系图

要求：

- 图示默认是强偏好，但前提是你真的看懂了论文，且证据足够支撑图示。
- 只有在读过论文主要内容后，才画图。
- 图要帮助读者理解论文在系统链条里的位置，而不是装饰。
- 如果因为证据不足不画图，必须让 `evidence_status` / `evidence_note` 足以解释缺失原因。

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
先解释这个 topic 为什么重要、你扫描了多少候选、候选池有多大、最后保留了多少篇论文，以及该 topic 的目标分配与实际分配。

### 逐篇解读
#### 1. [论文标题](paper_url)
- 发表：CVPR 2025 / arXiv 2025-03
- 作者：...
- 访问链接：...
- PDF：...
- 证据等级：full_text_verified / abstract_only / metadata_only
- 说明：若证据受限，在这里解释
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

## 综合总结

### 我的总体判断
### 重要代表文献
### Topic 演化时间线
### 后续精读建议
````

硬性要求：

- 每个 topic 先逐篇解读，再表格汇总。
- 每个 topic 前面要先有 `Topic 解读`。
- 公开契约是全局总量 `>=200`，topic 内部配额只是派生执行策略，不得反客为主。
- 表格中**不要有 `来源` 列**。
- 表格中**不要有单独的 `年份` 列**。
- `发表` 列必须直接写成：
  - `CVPR 2025`
  - `ICLR 2024`
  - `arXiv 2025-03`
- ArXiv 的年月可由 `publish_at` 或 arXiv ID 推断。
- 每篇论文标题都必须有可点击主链接。
- 每篇论文都必须显式呈现证据状态；有 PDF 时显示 PDF，没有 PDF 时至少给访问链接。
- 结尾必须使用固定节名，不要再退回“整体理解与重要点”的旧结构。

## 写作要求

每篇论文的中文解读至少应覆盖大部分内容：

1. 这篇论文在解决什么问题
2. 它用了什么核心思路
3. 为什么它在当前 topic 中重要
4. 你对它的判断是什么
5. 用一个例子说明它在干什么

注意：

- 不要把论文解读写成摘要翻译。
- 要把每篇论文放到该 topic 的主线里解释。
- 要有“为什么值得纳入综述”的判断。
- 证据受限时，要降低断言强度并明确说明。
- 不要默认“代表作写长一点，其余论文写一句带过”；目标是保持相对均匀的最小信息包，而不是做层级化敷衍。

## 结尾总结要求

全文结尾不能只是“以上就是调研结果”。

必须用**你自己的理解**对整批论文给出判断，至少覆盖：

- 哪些主线已经形成
- 哪些能力块已经成熟，哪些还不成熟
- 真正重要的研究接口在哪里
- 每个 topic 下哪些代表论文最值得精读，为什么
- topic 之间的演化脉络如何衔接

总结必须是你自己的组织与判断，不要只是把前文改写一遍。

## 可扩展性

后续可以继续扩展：

- 更稳定的 topic 分配 / rebalance 策略
- 更高质量的论文图示
- 更细的 topic 内部关系图
- 引用统计
- 与已有工作对比
- 推荐阅读路径自动排序

输出结构、字段定义与失败策略见：

- `references/output-contract.md`
