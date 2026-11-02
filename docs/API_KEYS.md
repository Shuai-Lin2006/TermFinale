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
