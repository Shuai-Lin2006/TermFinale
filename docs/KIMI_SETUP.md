# Kimi 接入（可选）

## 1) 不要把 Key 发聊天

把 Key 写进本机 `.env`（项目根目录）或用户数据目录 `.env`：

```bash
KIMI_API_KEY=你的Key
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=moonshot-v1-8k
KIMI_MAX_TOKENS=4096
```

模型名以 Moonshot 控制台为准；默认不启用。

## 2) 自检

```bash
PYTHONPATH=. .venv/bin/python tools/check_kimi.py
```

最多一次 256 tokens 的小请求；失败不会重试。

## 3) 成本限制

- 单次输出上限 8192，默认 4096；
- 不自动重试；
- 默认不接管任何任务；
- 只在显式选择 provider 时使用。

## 4) 用途

建议只用于：
- 全局大纲；
- 跨节一致性；
- 审校。

不要用它一次生成整本 300 页。