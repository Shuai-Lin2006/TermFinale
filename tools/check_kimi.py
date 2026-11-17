import time
from tfv2.llm.kimi import KimiClient

c = KimiClient()
t = time.time()
r = c.json("只输出 JSON。", '返回 {"ok": true}', max_tokens=256, temperature=0)
print({"model": c.model, "base_url": c.base_url, "max_tokens": c.max_tokens,
       "latency_s": round(time.time() - t, 1), "response": r})
