# API Key 配置（打包版必读）

打包后的应用**不带** `.env`。密钥请放在「用户数据目录」：

| 系统 | 路径 |
|---|---|
| macOS | `~/Library/Application Support/TermFinale/.env` |
| Windows | `%APPDATA%\TermFinale\.env` |
| Linux | `~/.local/share/TermFinale/.env` |

文件内容：

```
DEEPSEEK_API_KEY=sk-xxxxxxxx
DASHSCOPE_API_KEY=sk-xxxxxxxx
```

说明：

- `DEEPSEEK_API_KEY`：文本生成（讲义、提取、组卷），必填。
- `DASHSCOPE_API_KEY`：图片识别（给图配文字说明），可选；不填时图片会标注「第 N 页配图」。
- 也可以不改文件，直接设置同名系统环境变量。
- 启动时若缺少 Key，界面右下角会弹提示，不会闪退。
- 密钥只保存在本机，不会上传；请勿把 `.env` 提交到 git。

开发期仍兼容项目根目录的 `.env`（优先级低于用户数据目录）。

## 模型选择（实测）

| 用途 | 默认 | 说明 | 覆盖变量 |
|---|---|---|---|
| 文本 | `deepseek-flash` | 推理模型；默认关闭思考模式，8192 预算可完整出卷（实测 8s/章） | `DEEPSEEK_MODEL` |
| 视觉 | `qwen3.8-max` | 实测可识图（另有 `qwen3-vl-plus` 可切换） | `QWEN_VL_MODEL` |

**踩过的坑**：`qwen-vl-max` 在本账号返回 404，`cmaas-qwen3.8-flash` 返回 403 无权限，
`deepseek-chat` 仍可用但属于旧别名。代码已默认切到实测可用的模型，并支持用环境变量覆盖。

## 生成性能

| 场景 | 耗时（32 页 / 36 图） |
|---|---|
| 串行 | 377s |
| 并发 2（默认） | 177s |

并发度可用 `TERMFINALE_CONCURRENCY=1~4` 调整；如果遇到限流可调回 1。
大纲默认缓存（同一份资料重复生成结构一致），需要重算时设 `TERMFINALE_REFRESH_OUTLINE=1`。

### 推理模型与思考开关（重要）

`deepseek-flash` / `deepseek-v4-pro` 是推理模型。**不关思考时**，复杂 prompt 会把 8192 预算
全部耗在思考上，正文返回空字符串（`finish_reason=length`、`content=""`），表现为"生成结果为空"。

代码默认发送 `thinking: {"type": "disabled"}`：
- 8192 预算即可完整写出整套试卷（实测 10,808 字 / 100 分 / 20 题）；
- 比 16384 预算更快、更省（思考 token 不计入正文）。

需要打开思考时设 `TERMFINALE_THINKING=on`；换成非推理模型时也应设为 `on`，避免传未知参数。
