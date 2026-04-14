# 主题拆解清单

使用本清单从 `user_prompt` 中提取 `main_topic`、`aliases`、`subtopics` 和 `keywords`。

## 主主题

先把用户请求压缩成一个核心研究问题。

可自问：

- 用户真正关心的核心任务或科学问题是什么？
- 被改进、分析或比较的对象是什么？
- 用户关注的是方法、应用、评测，还是理论？

## Aliases

优先提取运行时可用于检索的主题别名，例如：

- 用户原始写法
- 英文标准表述
- 常用缩写
- 括号中的补充别名

要求：

- 正式执行前，尽量补出至少一个英文 canonical alias
- 如果用户只给中文主题且没有明显英文表述，先由你推断标准英文写法，再决定是否需要用少量检索结果做校准
- 这是**运行时推断**，不是把某个方向写死在代码里

## 子方向

优先从以下常见维度生成 2–4 个子方向：

- 核心方法
- 架构或表示
- 训练或适配策略
- 评测、benchmark 或数据集
- 效率、鲁棒性、安全性、可解释性
- 下游应用场景

优先选择容易独立检索的子方向名称。

## 关键词

关键词应尽量可直接用于搜索，例如：

- 标准任务名
- 常用缩写
- 模型家族名
- benchmark 名称
- 问题变体名称
- 关键技术术语

好的关键词示例：

- `retrieval-augmented generation`
- `long-context reasoning`
- `multimodal alignment`
- `<canonical alias> benchmark`
- `<canonical alias> survey`

较弱的关键词示例：

- `interesting`
- `advanced`
- `state of the art`
