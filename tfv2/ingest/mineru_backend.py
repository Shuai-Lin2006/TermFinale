"""本地 MinerU 解析后端：扫描件/公式页走本地模型，不烧云端 token。

为什么要它：
- 现有扫描件 OCR 走的是云端视觉模型（DashScope），每页都要花钱，而且对公式的还原依赖提示词；
- MinerU 本地 flash 档能在自己机器上把扫描 PDF 转成带结构的 Markdown，成本和隐私都更好。

设计原则：
- 只是“多一个后端”，不替换现有链路；调用方拿不到结果时必须能拿到**原因**；
- 结果按 (文件哈希, 页范围) 缓存，重复调用不再跑模型；
- 机器上没装 MinerU 时返回明确原因，不静默假装解析成功。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BIN = ROOT / ".venv_mineru" / "bin" / "mineru"
CACHE_DIR = Path(os.getenv("TFV2_DATA_ROOT", str(ROOT / "data"))) / "cache" / "mineru"


class MinerUError(RuntimeError):
    """本地 MinerU 不可用或解析失败；message 必须是能给人看的原因。"""


def mineru_bin() -> Path | None:
    raw = os.getenv("TFV2_MINERU_BIN", "").strip()
    candidate = Path(raw) if raw else DEFAULT_BIN
    return candidate if candidate.is_file() else None


def available() -> tuple[bool, str]:
    path = mineru_bin()
    if path is None:
        return False, f"没有找到本地 MinerU（默认路径 {DEFAULT_BIN}，可用 TFV2_MINERU_BIN 指定）"
    return True, str(path)


def _cache_path(pdf: Path, page_spec: str) -> Path:
    digest = hashlib.md5()
    with pdf.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    digest.update(page_spec.encode("utf-8"))
    return CACHE_DIR / f"{digest.hexdigest()}.json"


def _strip_markers(markdown: str) -> str:
    out = []
    for line in str(markdown or "").splitlines():
        if line.strip().startswith("<!-- page ") and line.strip().endswith("-->"):
            continue
        out.append(line)
    return "\n".join(out).strip()


def _ensure_server(bin_path: Path, timeout: int = 120) -> None:
    """flash 档在部分安装形态下需要本地服务；启动失败不影响后续调用（让它自己报错）。"""
    try:
        subprocess.run([str(bin_path), "server", "start"], capture_output=True,
                       text=True, timeout=timeout, check=False)
    except Exception:
        return


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_BAD_HEADING = re.compile(r"^【(答案|解析|解法|证|证明|解|提示)】|^(答案|解析|解法)[：:]|^[（(]?\d+[)）.、]?$")
_NUM_PREFIX = re.compile(r"^[一二三四五六七八九十]+\s*[、.]\s*|^\d+(?:\.\d+){0,3}\s*")


def clean_heading(text: str) -> str:
    """标题过滤：去掉“【答案】A”这类题解析标记，只留真正的章节标题。"""
    raw = re.sub(r"\s+", " ", str(text or "")).strip()
    if not raw or len(raw) > 40:
        return ""
    if _BAD_HEADING.search(raw):
        return ""
    body = _NUM_PREFIX.sub("", raw).strip()
    cjk = re.findall(r"[\u4e00-\u9fffA-Za-z]", body)
    if len(cjk) < 2:
        return ""
    return raw


_DISPLAY_MATH = re.compile(r"\$\$(.+?)\$\$", re.S)
_INLINE_MATH = re.compile(r"(?<!\$)\$([^$\n]{2,200})\$(?!\$)")


def extract_formulas(markdown: str) -> list[dict]:
    """从 MinerU Markdown 抽公式（LaTeX）：行内/独立都收，带页码由调用方补。"""
    rows: list[dict] = []
    seen: set[str] = set()
    for m in _DISPLAY_MATH.finditer(markdown or ""):
        latex = re.sub(r"\s+", " ", m.group(1)).strip()
        if len(latex) < 3 or latex in seen:
            continue
        seen.add(latex)
        rows.append({"latex": latex, "display": True})
    for m in _INLINE_MATH.finditer(markdown or ""):
        latex = re.sub(r"\s+", " ", m.group(1)).strip()
        if len(latex) < 3 or latex in seen:
            continue
        seen.add(latex)
        rows.append({"latex": latex, "display": False})
    return rows


def ocr_pdf_document(pdf: str | Path, *, timeout: int = 900, use_cache: bool = True) -> dict:
    """整本解析：返回 {"pages": {页码: 文本}, "headings": [{page, level, text}], "engine": ...}。

    标题来自 Markdown 的 # 层级——这比正则猜章节可靠，扫描件/教材都能拿到真实目录。
    """
    pages, engine = ocr_pdf_pages(pdf, timeout=timeout, use_cache=use_cache)
    ok, detail = available()
    if not ok:
        return {"pages": pages, "headings": [], "formulas": [], "engine": engine}
    bin_path = Path(detail)
    src = Path(pdf)
    cache_file = _cache_path(src, "doc")
    if use_cache and cache_file.is_file():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            # 老缓存没有 formulas 字段：需要重解析一次才能拿到公式
            if "formulas" in data:
                return {"pages": {int(k): v for k, v in (data.get("pages") or {}).items()},
                        "headings": list(data.get("headings") or []),
                        "formulas": list(data.get("formulas") or []),
                        "engine": str(data.get("engine") or "cache")}
        except Exception:
            pass

    _ensure_server(bin_path)
    headings: list[dict] = []
    formulas: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="tf_mineru_doc_") as td:
        out_file = Path(td) / "out.md"
        cmd = [str(bin_path), "parse", str(src), "-p", "all", "-o", str(out_file),
               "--tier", "flash", "--wait", str(max(30, timeout))]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60, check=False)
        except subprocess.TimeoutExpired:
            return {"pages": pages, "headings": [], "formulas": [], "engine": engine}
        if out_file.is_file():
            raw = out_file.read_text(encoding="utf-8", errors="ignore")
            current = 0
            marker = re.compile(r"<!--\s*page\s+(\d+)\s+of\s+\d+\s*-->")
            page_chunks: dict[int, list[str]] = {}
            for line in raw.splitlines():
                m = marker.search(line)
                if m:
                    current = int(m.group(1))
                    continue
                if current:
                    page_chunks.setdefault(current, []).append(line)
                h = _HEADING.match(line.strip())
                if h and current:
                    title = clean_heading(h.group(2))
                    if title:
                        headings.append({"page": current, "level": len(h.group(1)), "text": title})
            for page_no, lines in page_chunks.items():
                for item in extract_formulas("\n".join(lines)):
                    formulas.append({"page": page_no, **item})

    result = {"pages": pages, "headings": headings, "formulas": formulas, "engine": engine}
    if use_cache:
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    return result


def ocr_pdf_pages(pdf: str | Path, *, timeout: int = 900, use_cache: bool = True) -> tuple[dict[int, str], str]:
    """返回 {页码(1-based): 文本}；页码来自 MinerU 的 `<!-- page N of M -->` 标记。

    整本一次跑（比逐页快得多），失败抛 MinerUError 并带原因。
    """
    ok, detail = available()
    if not ok:
        raise MinerUError(detail)
    bin_path = Path(detail)
    src = Path(pdf)
    if not src.is_file():
        raise MinerUError(f"文件不存在：{src}")
    cache_file = _cache_path(src, "pages")
    if use_cache and cache_file.is_file():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return ({int(k): v for k, v in (data.get("pages") or {}).items()}, str(data.get("engine") or "cache"))
        except Exception:
            pass

    _ensure_server(bin_path)
    with tempfile.TemporaryDirectory(prefix="tf_mineru_pages_") as td:
        out_file = Path(td) / "out.md"
        cmd = [str(bin_path), "parse", str(src), "-p", "all", "-o", str(out_file),
               "--tier", "flash", "--wait", str(max(30, timeout))]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60, check=False)
        except subprocess.TimeoutExpired as exc:
            raise MinerUError(f"MinerU 超时（{timeout + 60}s）") from exc
        if not out_file.is_file():
            stderr = (proc.stderr or proc.stdout or "").strip().splitlines()
            raise MinerUError("MinerU 没有产出文本：" + (stderr[-1] if stderr else f"退出码 {proc.returncode}"))
        raw = out_file.read_text(encoding="utf-8", errors="ignore")

    pages: dict[int, str] = {}
    current = 0
    buf: list[str] = []
    marker = re.compile(r"<!--\s*page\s+(\d+)\s+of\s+\d+\s*-->")
    for line in raw.splitlines():
        m = marker.search(line)
        if m:
            if current and "".join(buf).strip():
                pages[current] = "\n".join(buf).strip()
            current = int(m.group(1))
            buf = []
            continue
        buf.append(line)
    if current and "".join(buf).strip():
        pages[current] = "\n".join(buf).strip()
    if not pages:
        # 没有分页标记时整段当一页，至少不丢内容
        text = _strip_markers(raw)
        if text:
            pages[1] = text
    if not pages:
        raise MinerUError("MinerU 返回空文本（可能是纯图页）")

    if use_cache:
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps({"file": src.name, "pages": pages, "engine": "mineru-local"},
                                             ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    return pages, "mineru-local"


def ocr_pdf_text(pdf: str | Path, *, page_spec: str = "all", timeout: int = 600,
                 use_cache: bool = True) -> str:
    """用本地 MinerU 把 PDF（扫描件也算）转成 Markdown 文本。

    失败时抛 MinerUError，message 带原因；调用方据此决定是否回退云端 OCR。
    """
    ok, detail = available()
    if not ok:
        raise MinerUError(detail)
    bin_path = Path(detail)
    src = Path(pdf)
    if not src.is_file():
        raise MinerUError(f"文件不存在：{src}")

    cache_file = _cache_path(src, page_spec)
    if use_cache and cache_file.is_file():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return str(data.get("text") or "")
        except Exception:
            pass

    _ensure_server(bin_path)
    with tempfile.TemporaryDirectory(prefix="tf_mineru_") as td:
        out_file = Path(td) / "out.md"
        cmd = [str(bin_path), "parse", str(src), "-p", page_spec, "-o", str(out_file),
               "--tier", "flash", "--wait", str(max(30, timeout))]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30, check=False)
        except subprocess.TimeoutExpired as exc:
            raise MinerUError(f"MinerU 超时（{timeout + 30}s）") from exc
        if not out_file.is_file():
            stderr = (proc.stderr or proc.stdout or "").strip().splitlines()
            raise MinerUError("MinerU 没有产出文本：" + (stderr[-1] if stderr else f"退出码 {proc.returncode}"))
        text = _strip_markers(out_file.read_text(encoding="utf-8", errors="ignore"))
    if not text.strip():
        raise MinerUError("MinerU 返回空文本（可能是纯图页）")

    if use_cache:
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps({"file": src.name, "pages": page_spec, "text": text},
                                             ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    return text
