"""FigureSpec v2：统一节点/边/标签/单位与硬校验。"""
from __future__ import annotations


def _collect(v, out: list[str]):
    if isinstance(v, dict):
        for k, x in v.items():
            if k in ("label", "value", "date", "title") and str(x).strip():
                out.append(str(x).strip())
            else:
                _collect(x, out)
    elif isinstance(v, list):
        for x in v:
            _collect(x, out)


def labels(spec: dict) -> list[str]:
    out: list[str] = []
    _collect(spec, out)
    return list(dict.fromkeys(out))


def validate(spec: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(spec, dict) or not spec:
        return ["spec 为空"]
    kind = str(spec.get("kind") or "").strip()
    if not kind:
        errors.append("缺 kind")
    nodes = spec.get("nodes")
    if nodes is not None:
        if not isinstance(nodes, list) or not nodes:
            errors.append("nodes 必须是非空数组")
        else:
            ids = []
            for i, n in enumerate(nodes):
                if not isinstance(n, dict):
                    errors.append(f"node {i} 不是对象"); continue
                nid = str(n.get("id") or "").strip()
                if not nid:
                    errors.append(f"node {i} 缺 id")
                elif nid in ids:
                    errors.append(f"node id 重复：{nid}")
                ids.append(nid)
                if not str(n.get("type") or "").strip():
                    errors.append(f"node {nid} 缺 type")
            degree = {str(n.get("id") or ""): 0 for n in nodes if isinstance(n, dict)}
            for j, e in enumerate(spec.get("edges") or []):
                if isinstance(e, (list, tuple)) and len(e) >= 2:
                    a, b = str(e[0]), str(e[1])
                elif isinstance(e, dict):
                    a, b = str(e.get("from") or e.get("a") or ""), str(e.get("to") or e.get("b") or "")
                else:
                    errors.append(f"edge {j} 格式非法"); continue
                if a not in ids or b not in ids:
                    errors.append(f"edge {j} 引用不存在的节点：{a}->{b}")
                else:
                    degree[a] = degree.get(a, 0) + 1
                    degree[b] = degree.get(b, 0) + 1
            if kind in ("circuit", "netlist"):
                seen_edges = set()
                batteries = 0
                for e in spec.get("edges") or []:
                    if isinstance(e, (list, tuple)) and len(e) >= 2:
                        a, b = str(e[0]), str(e[1])
                    elif isinstance(e, dict):
                        a, b = str(e.get("from") or e.get("a") or ""), str(e.get("to") or e.get("b") or "")
                    else:
                        continue
                    if a == b:
                        errors.append(f"电路自环：{a}")
                    key = tuple(sorted((a, b)))
                    if key in seen_edges:
                        errors.append(f"重复支路：{a}-{b}")
                    seen_edges.add(key)
                for n in nodes:
                    if isinstance(n, dict) and str(n.get("type") or "") == "battery":
                        batteries += 1
                if not batteries:
                    errors.append("电路缺电源")
                for n in nodes:
                    if not isinstance(n, dict):
                        continue
                    if str(n.get("type") or "") in ("battery", "resistor", "capacitor", "inductor", "switch", "lamp"):
                        nid = str(n.get("id") or "")
                        if degree.get(nid, 0) < 2:
                            errors.append(f"电路元件 {nid} 悬空（连接数 {degree.get(nid, 0)}）")
    elements = spec.get("elements")
    if elements is not None:
        if not isinstance(elements, list) or not elements:
            errors.append("elements 必须是非空数组")
        else:
            for i, el in enumerate(elements):
                if not isinstance(el, dict) or not str(el.get("type") or "").strip():
                    errors.append(f"element {i} 缺 type")
    if kind == "table" and not spec.get("rows"):
        errors.append("table 缺 rows")
    if kind in ("chart", "bar", "line", "pie"):
        if not spec.get("labels") or not spec.get("values"):
            errors.append("chart 缺 labels/values")
        elif len(spec["labels"]) != len(spec["values"]):
            errors.append("chart labels/values 长度不一致")
    return errors


def normalize(spec: dict) -> dict:
    from tfv2.render.layout import layered_positions
    out = dict(spec or {})
    nodes = out.get("nodes")
    if isinstance(nodes, list):
        clean = []
        for i, n in enumerate(nodes):
            if isinstance(n, dict):
                n = dict(n); n.setdefault("id", f"n{i}"); n.setdefault("type", "node"); clean.append(n)
        if any("x" not in n or "y" not in n for n in clean):
            pos = layered_positions(clean, out.get("edges") or [])
            for n in clean:
                if "x" not in n or "y" not in n:
                    n["x"], n["y"] = pos.get(str(n["id"]), (360, 210))
        out["nodes"] = clean
    return out
