"""极简分层布局：节点/边 -> 坐标；保证确定性。"""
from __future__ import annotations


def layered_positions(nodes: list[dict], edges: list[dict]) -> dict[str, tuple[float, float]]:
    ids = [str(n.get("id")) for n in nodes]
    adj = {i: [] for i in ids}
    indeg = {i: 0 for i in ids}
    for e in edges:
        if isinstance(e, (list, tuple)) and len(e) >= 2:
            a, b = str(e[0]), str(e[1])
        elif isinstance(e, dict):
            a, b = str(e.get("from") or e.get("a") or ""), str(e.get("to") or e.get("b") or "")
        else:
            continue
        if a in adj and b in adj:
            adj[a].append(b); indeg[b] += 1
    q = [i for i in ids if indeg[i] == 0] or ids[:1]
    level = {i: 0 for i in ids}
    while q:
        a = q.pop(0)
        for b in adj[a]:
            level[b] = max(level[b], level[a] + 1)
            indeg[b] -= 1
            if indeg[b] == 0:
                q.append(b)
    by = {}
    for i in ids:
        by.setdefault(level[i], []).append(i)
    out = {}
    for lv, group in by.items():
        for j, i in enumerate(group):
            out[i] = (720 * (j + 1) / (len(group) + 1), 90 + 80 * lv)
    return out
