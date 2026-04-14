# Skill Monorepo

这个仓库用于集中管理多个独立 skill。仓库根目录只放索引和协作规则，真正的 skill 都位于 `skills/` 下，每个 skill 保持自己的 `SKILL.md`、`agents/`、`scripts/` 和 `references/`。

## 目录结构

```text
.
├── README.md
├── AGENTS.md
└── skills/
    ├── papers-cool-venue-reader/
    └── research-papers/
```

## Skills

### `skills/papers-cool-venue-reader`

- 用途：从 `papers.cool` 拉取会场论文、核验官方链接或 PDF，并生成结构化摘要。
- 入口：`python skills/papers-cool-venue-reader/scripts/papers_cool.py --help`
- 依赖：`python -m pip install -r skills/papers-cool-venue-reader/requirements.txt`

### `skills/research-papers`

- 用途：围绕研究主题先扫六大会，再补 arXiv，生成中文论文综述。
- 入口：`python skills/research-papers/scripts/survey_topic.py --help`
- 依赖：需要 `deepxiv`，并会复用 `papers-cool-venue-reader` 的脚本入口。

## 通过 GitHub 安装

这个仓库已经是可被技能安装器消费的标准多-skill 仓库形态：每个 skill 都位于 `skills/<skill-name>/`，并且目录内有自己的 `SKILL.md`。

安装器按“仓库里的某个 skill 路径”工作，而不是直接安装整个 repo 根目录。因此最稳妥的做法是：

- 直接给某个 skill 子目录的 GitHub 链接，例如 `https://github.com/<owner>/<repo>/tree/main/skills/research-papers`
- 或者给仓库链接，并明确要安装的路径，例如 `skills/research-papers`
- 如果要安装 `research-papers`，建议同时安装 `skills/papers-cool-venue-reader`，因为前者会复用后者的脚本入口

自然语言示例：

- “从这个 GitHub 链接安装 skill：`https://github.com/<owner>/<repo>/tree/main/skills/papers-cool-venue-reader`”
- “从 `<owner>/<repo>` 安装 `skills/research-papers` 和 `skills/papers-cool-venue-reader`”
- “列出 `<owner>/<repo>` 的 `skills/` 目录下有哪些 skill，然后安装 `research-papers`”

## 使用建议

先在仓库根目录完成依赖安装，再进入目标 skill 目录执行脚本。`research-papers` 依赖 `papers-cool-venue-reader` 的 sibling 路径，因此保留当前 `skills/<skill-name>/` 的并列结构最稳妥。

## 维护约定

- 新 skill 统一放到 `skills/<skill-name>/`
- skill 名称使用小写加连字符
- 仓库级说明放根目录；skill 级说明放各自的 `SKILL.md`
- 公共产物不要直接丢在 skill 根目录，参考资料放 `references/`，脚本放 `scripts/`
