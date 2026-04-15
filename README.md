# Skill Monorepo

这个仓库用于集中管理多个独立 skill。仓库根目录只放索引和协作规则，真正的 skill 都位于 `skills/` 下；每个 skill 自己维护 `SKILL.md`、`agents/`、`scripts/` 和 `references/`。

仓库地址：[xiuguangli/skills](https://github.com/xiuguangli/skills)

## 目录结构

```text
.
├── README.md
├── AGENTS.md
└── skills/
    ├── papers-cool-venue-reader/
    └── research-papers/
```

## 收录 Skills

### `skills/papers-cool-venue-reader`

- 用途：从 `papers.cool` 拉取会场论文、核验官方链接或 PDF，并生成结构化摘要。
- 安装路径：[skills/papers-cool-venue-reader](https://github.com/xiuguangli/skills/tree/main/skills/papers-cool-venue-reader)
- 文档：[skills/papers-cool-venue-reader/SKILL.md](skills/papers-cool-venue-reader/SKILL.md)
- CLI 入口：`python skills/papers-cool-venue-reader/scripts/papers_cool.py --help`
- 依赖安装：
  - `python -m pip install -r skills/papers-cool-venue-reader/requirements.txt`
  - 如需 PDF 提取：`python -m pip install -r skills/papers-cool-venue-reader/requirements-pdf.txt`
- 快速验证：

```bash
python skills/papers-cool-venue-reader/scripts/papers_cool.py venue CVPR --year 2025 --limit 5
```

### `skills/research-papers`

- 用途：围绕研究主题先扫六大会，再补 arXiv，生成中文论文综述。
- 安装路径：[skills/research-papers](https://github.com/xiuguangli/skills/tree/main/skills/research-papers)
- 文档：[skills/research-papers/SKILL.md](skills/research-papers/SKILL.md)
- CLI 入口：`python skills/research-papers/scripts/survey_topic.py --help`
- 依赖关系：
  - 需要同仓库的 sibling skill `skills/papers-cool-venue-reader`
  - 运行时会复用 `skills/papers-cool-venue-reader/scripts/papers_cool.py`
  - 需要本地可用的 `deepxiv`
- 推荐工作流：
  - 默认使用两阶段缓存工作流
  - 先在可联网环境预热 cache，再在受限环境用 `--cache-mode read-only` 生成 survey

## 通过 GitHub 安装

这个仓库已经是可被技能安装器消费的标准多-skill 仓库形态：每个 skill 都位于 `skills/<skill-name>/`，并且目录内有自己的 `SKILL.md`。

安装器应按“仓库中的某个 skill 路径”工作，而不是把整个 repo 根目录当成单个 skill 安装。最稳妥的做法是：

- 直接提供某个 skill 子目录链接，例如 `https://github.com/xiuguangli/skills/tree/main/skills/papers-cool-venue-reader`
- 或者提供仓库链接 `https://github.com/xiuguangli/skills`，并明确要安装的路径，例如 `skills/research-papers`
- 安装 `research-papers` 时，应同时安装 `skills/papers-cool-venue-reader`

当前仓库中的 skill 可按下面的方式安装：

| Skill 名称 | 说明 | 安装方式 |
| --- | --- | --- |
| `papers-cool-venue-reader` | 从 `papers.cool` 拉取会场论文、核验官方链接或 PDF，并生成结构化摘要。 | “从这个 GitHub 链接安装 skill：`https://github.com/xiuguangli/skills/tree/main/skills/papers-cool-venue-reader`” |
| `research-papers` | 围绕研究主题先扫六大会，再补 arXiv，生成中文论文综述；依赖 `papers-cool-venue-reader`。 | “从这个 GitHub 链接安装 skill：`https://github.com/xiuguangli/skills/tree/main/skills/research-papers`” |

如果安装 `research-papers`，仍应同时安装 `papers-cool-venue-reader`。

## 更新 Skills

更新方式取决于你最初是**怎么安装**的，但先把原理说清楚：

### 更新原理

如果你是通过 GitHub 路径把 skill 安装到 `~/.codex/skills/`，安装器做的事情本质上是：

1. 取到远端仓库里某个 skill 目录的内容
2. 复制到本地 `~/.codex/skills/<skill-name>/`

因此，很多安装器更接近“**复制一份新目录**”，而不是“**在旧目录上做原地升级**”。

这也是为什么更新时最稳妥的思路通常是：

- **先删除旧的 skill 目录**
- **再重新安装最新的一份**

可以把它理解成：**不是给旧 skill 打补丁，而是用新的目录把旧的替换掉**。

默认安装目录通常是：

```text
~/.codex/skills/<skill-name>
```

### 方式 A：你是直接 clone 这个仓库来用

这种情况不需要“删掉再装”，因为你本地用的就是这个仓库本身。

更新方式就是直接更新仓库：

```bash
git pull
```

如果依赖文件有变化，再补一次依赖安装：

```bash
python -m pip install -r skills/papers-cool-venue-reader/requirements.txt
python -m pip install -r skills/papers-cool-venue-reader/requirements-pdf.txt  # 只有需要 PDF 提取时才装
```

### 方式 B：你是通过 GitHub 链接安装到 `~/.codex/skills/`

这种情况最稳妥的更新方式就是：

- 删除旧目录
- 重新从 GitHub 安装最新版本
- 必要时重启 Codex

下面用**自然语言实例**表示更新意图：

| 你想做什么 | 可以这样说 |
| --- | --- |
| 更新 `papers-cool-venue-reader` | “把我本地已经安装的 `papers-cool-venue-reader` 删掉，然后从这个 GitHub 链接重新安装最新版本：`https://github.com/xiuguangli/skills/tree/main/skills/papers-cool-venue-reader`。” |
| 更新 `research-papers` | “把我本地已经安装的 `research-papers` 删掉，然后从这个 GitHub 链接重新安装最新版本：`https://github.com/xiuguangli/skills/tree/main/skills/research-papers`。” |
| 同时更新 `research-papers` 和它依赖的 sibling skill | “把我本地的 `research-papers` 和 `papers-cool-venue-reader` 一起删掉，再从各自的 GitHub 路径重新安装最新版本。” |
| 不确定自己装的是不是最新 | “检查我本地安装的这两个 skill 是否还是旧版本；如果是，就删除旧目录并重新安装最新版本。” |

### 方式 C：你改过本地已安装 skill

如果你在 `~/.codex/skills/` 里手工改过内容，更新前建议先备份或做 diff，避免直接删目录后把自己的改动丢掉。

### 对这个仓库里的两个 skill 的建议

- 更新 `research-papers` 时，**最好同时更新** `papers-cool-venue-reader`
- 因为 `research-papers` 会直接复用 sibling 路径里的脚本和字段约定
- 如果只更新一个、不更新另一个，最容易出现脚本字段不一致或行为漂移

## 快速开始

### 1. 先验证 `papers-cool-venue-reader`

在仓库根目录安装依赖并执行：

```bash
python -m pip install -r skills/papers-cool-venue-reader/requirements.txt
python skills/papers-cool-venue-reader/scripts/papers_cool.py venue CVPR --year 2025 --limit 5
```

如果需要 PDF 提取能力，再安装：

```bash
python -m pip install -r skills/papers-cool-venue-reader/requirements-pdf.txt
```

### 2. 再使用 `research-papers`

这个 skill 依赖 `papers-cool-venue-reader` 的 sibling 路径，因此保留当前 `skills/<skill-name>/` 的并列结构最稳妥。

推荐先预热 cache，再只读生成 survey：

```bash
python skills/research-papers/scripts/prefetch_topic_cache.py "topic" \
  --cache-dir /tmp/research_papers_cache \
  --prefetch-only

python skills/research-papers/scripts/survey_topic.py "topic" \
  --cache-dir /tmp/research_papers_cache \
  --cache-mode read-only \
  -o /tmp/research_papers.md
```

更完整的参数、写作约束和示例命令见 [skills/research-papers/SKILL.md](skills/research-papers/SKILL.md)。

## 维护约定

- 新 skill 统一放到 `skills/<skill-name>/`
- skill 名称使用小写加连字符
- 仓库级说明放根目录；skill 级说明放各自的 `SKILL.md`
- 公共产物不要提交到仓库；参考资料放 `references/`，脚本放 `scripts/`
