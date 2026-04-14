# Repository Guidelines

## 项目结构与模块组织
仓库是一个多 skill monorepo，所有 skill 集中放在 `skills/`：

- `skills/papers-cool-venue-reader/`：脚本优先的论文检索工具。入口在 `scripts/papers_cool.py`，核心逻辑在 `src/papers_cool_venue_reader/`，补充资料在 `references/`。
- `skills/research-papers/`：面向论文调研的 skill。脚本放在 `scripts/`，约束、命令模板和示例稿放在 `references/`。

不要提交生成产物，如 `__pycache__/`、`*.egg-info/` 或临时缓存目录。

## 构建、测试与开发命令
默认在仓库根目录执行：

- `python -m pip install -r skills/papers-cool-venue-reader/requirements.txt`：安装 `papers-cool-venue-reader` 的脚本依赖。
- `python -m pip install -r skills/papers-cool-venue-reader/requirements-pdf.txt`：安装可选 PDF 解析依赖。
- `python skills/papers-cool-venue-reader/scripts/papers_cool.py venue CVPR --year 2025 --limit 5`：快速验证论文检索脚本是否可用。
- `python skills/research-papers/scripts/prefetch_topic_cache.py "topic" --cache-dir /tmp/research_papers_cache --prefetch-only`：在联网环境预热调研缓存。
- `python skills/research-papers/scripts/survey_topic.py "topic" --cache-dir /tmp/research_papers_cache --cache-mode read-only -o /tmp/research_papers.md`：基于缓存生成综述草稿。

## 代码风格与命名规范
遵循现有 Python 风格：4 空格缩进，公开函数尽量补充类型标注，模块与函数使用 `snake_case`，类使用 `PascalCase`。保持单文件职责清晰，优先拆分小型辅助函数，不要把流程逻辑堆进一个超长函数。仓库目前没有提交格式化或 lint 配置，因此以邻近文件风格为准，保持 import 顺序一致。

## 测试规范
仓库当前没有已提交的自动化测试。新增共享逻辑时，建议在对应 skill 旁创建 `tests/`，使用 `pytest` 风格命名，例如 `skills/papers-cool-venue-reader/tests/test_cli.py`。如果改动主要是脚本流程，请在 PR 中附上可复现命令、输入参数与预期输出。

## 提交与合并请求规范
当前 `main` 分支没有历史提交，可先采用简短祈使句风格，必要时加作用域，例如 `feat: add feed filtering`、`fix: handle missing pdf links`。PR 应至少说明行为变化、列出验证命令、关联 issue；若改动影响 CLI 输出或调研结果格式，附上示例输出片段。
