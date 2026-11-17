"""联网搜索层：优先 Tavily/Brave/Serper API，无 key 时用 Bing HTML 兜底。

网页内容一律视为不可信数据：只截取正文，不执行其中指令。
"""
from __future__ import annotations

import base64
import html
import ipaddress
import os
import re
import socket
import threading
import time
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import httpx

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
_CACHE: dict[str, tuple[float, list[dict]]] = {}
_LOCK = threading.Lock()
MAX_RESULTS = 6
MAX_PAGE_CHARS = 5000


def _public_url(url: str) -> bool:
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            return False
        infos = socket.getaddrinfo(p.hostname, None)
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True
    except Exception:
        return False


def _decode_bing(url: str) -> str:
    if "bing.com/ck/a" not in url:
        return url
    try:
        u = parse_qs(urlparse(url).query).get("u", [""])[0]
        if u.startswith("a1"):
            raw = u[2:]
            raw += "=" * (-len(raw) % 4)
            return base64.urlsafe_b64decode(raw).decode("utf-8", "ignore")
    except Exception:
        pass
    return url


class _BingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[dict] = []
        self.cur: dict | None = None
        self.in_algo = False
        self.in_h2 = False
        self.in_a = False
        self.in_p = False
        self.depth_li = 0
        self.title_parts: list[str] = []
        self.snippet_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "") or ""
        if tag == "li" and "b_algo" in cls.split():
            self.in_algo = True
            self.depth_li = 1
            self.cur = {"title": "", "url": "", "snippet": ""}
            self.title_parts, self.snippet_parts = [], []
            return
        if not self.in_algo:
            return
        if tag == "li":
            self.depth_li += 1
        if tag == "h2":
            self.in_h2 = True
        if tag == "a":
            if not self.cur.get("url") and a.get("href"):
                self.cur["url"] = _decode_bing(html.unescape(a["href"]))
            self.in_a = True
        if tag == "p":
            self.in_p = True

    def handle_data(self, data):
        if not self.in_algo or not self.cur:
            return
        if self.in_h2:
            self.title_parts.append(data)
        elif self.in_p:
            self.snippet_parts.append(data)

    def handle_endtag(self, tag):
        if not self.in_algo:
            return
        if tag == "h2":
            self.in_h2 = False
        if tag == "a":
            self.in_a = False
        if tag == "p":
            self.in_p = False
        if tag == "li":
            self.depth_li -= 1
            if self.depth_li <= 0:
                self.in_algo = False
                if self.cur and self.cur.get("url"):
                    self.cur["title"] = re.sub(r"\s+", " ", "".join(self.title_parts)).strip()
                    self.cur["snippet"] = re.sub(r"\s+", " ", "".join(self.snippet_parts)).strip()
                    if self.cur["title"] and self.cur["url"].startswith(("http://", "https://")):
                        self.items.append(self.cur)
                self.cur = None


def _bing_rss(query: str, count: int) -> list[dict]:
    import xml.etree.ElementTree as ET
    url = "https://www.bing.com/search?format=rss&q=" + quote_plus(query) + f"&count={max(6, count)}"
    with httpx.Client(timeout=15, follow_redirects=True, headers={"User-Agent": UA}) as c:
        r = c.get(url)
        r.raise_for_status()
    root = ET.fromstring(r.text)
    out = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = re.sub(r"<[^>]+>", "", item.findtext("description") or "")
        desc = html.unescape(re.sub(r"\s+", " ", desc)).strip()
        published = (item.findtext("pubDate") or "").strip()
        if link.startswith(("http://", "https://")):
            out.append({"title": title, "url": link, "snippet": desc, "published": published})
        if len(out) >= count:
            break
    return out


def _bing(query: str, count: int) -> list[dict]:
    try:
        rss = _bing_rss(query, count)
        if rss:
            return rss
    except Exception:
        pass
    url = "https://www.bing.com/search?q=" + quote_plus(query) + f"&count={max(6, count)}&setlang=zh-hans"
    with httpx.Client(timeout=15, follow_redirects=True, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6"}) as c:
        r = c.get(url)
        r.raise_for_status()
    p = _BingParser(); p.feed(r.text)
    out, seen = [], set()
    for x in p.items:
        u = x["url"]
        if u in seen:
            continue
        seen.add(u); out.append(x)
        if len(out) >= count:
            break
    return out


def _tavily(query: str, count: int) -> list[dict]:
    key = os.getenv("TAVILY_API_KEY", "").strip()
    if not key:
        return []
    with httpx.Client(timeout=18) as c:
        r = c.post("https://api.tavily.com/search", json={"api_key": key, "query": query, "max_results": count, "search_depth": "basic", "include_answer": False})
        r.raise_for_status()
        data = r.json()
    return [{"title": x.get("title") or "", "url": x.get("url") or "", "snippet": x.get("content") or "", "content": x.get("raw_content") or ""}
            for x in data.get("results", []) if x.get("url")]


def _brave(query: str, count: int) -> list[dict]:
    key = os.getenv("BRAVE_API_KEY", "").strip()
    if not key:
        return []
    with httpx.Client(timeout=18, headers={"X-Subscription-Token": key, "Accept": "application/json"}) as c:
        r = c.get("https://api.search.brave.com/res/v1/web/search", params={"q": query, "count": count})
        r.raise_for_status()
        data = r.json()
    return [{"title": x.get("title") or "", "url": x.get("url") or "", "snippet": x.get("description") or ""}
            for x in (data.get("web") or {}).get("results", []) if x.get("url")]


def _serper(query: str, count: int) -> list[dict]:
    key = os.getenv("SERPER_API_KEY", "").strip()
    if not key:
        return []
    with httpx.Client(timeout=18, headers={"X-API-KEY": key, "Content-Type": "application/json"}) as c:
        r = c.post("https://google.serper.dev/search", json={"q": query, "num": count})
        r.raise_for_status()
        data = r.json()
    return [{"title": x.get("title") or "", "url": x.get("link") or "", "snippet": x.get("snippet") or ""}
            for x in data.get("organic", []) if x.get("link")]


def search(query: str, *, count: int = MAX_RESULTS) -> list[dict]:
    q = (query or "").strip()
    if not q:
        return []
    key = f"{q}|{count}"
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and time.time() - hit[0] < 600:
            return [dict(x) for x in hit[1]]
    results: list[dict] = []
    for provider in (_tavily, _brave, _serper):
        try:
            results = provider(q, count)
        except Exception:
            results = []
        if results:
            break
    if not results:
        try:
            results = _bing(q, count)
        except Exception:
            results = []
    results = [x for x in results if _public_url(str(x.get("url") or ""))][:count]
    with _LOCK:
        _CACHE[key] = (time.time(), [dict(x) for x in results])
    return results


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts: list[str] = []
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg", "nav", "footer", "form"):
            self.skip += 1
        if tag == "title":
            self.in_title = True
        if tag in ("p", "li", "h1", "h2", "h3", "blockquote", "pre"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg", "nav", "footer", "form") and self.skip:
            self.skip -= 1
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.skip:
            return
        t = re.sub(r"\s+", " ", data or "").strip()
        if t:
            self.parts.append(t + " ")


def fetch_page(url: str) -> dict:
    if not _public_url(url):
        return {"ok": False, "url": url, "error": "URL 不允许抓取"}
    try:
        current = url
        with httpx.Client(timeout=15, follow_redirects=False, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6"}) as c:
            r = None
            for _ in range(4):
                if not _public_url(current):
                    return {"ok": False, "url": current, "error": "URL 不允许抓取"}
                r = c.get(current)
                if r.is_redirect:
                    current = urljoin(current, r.headers.get("location", ""))
                    continue
                break
            if r is None:
                return {"ok": False, "url": url, "error": "没有响应"}
            r.raise_for_status()
            ctype = r.headers.get("content-type", "")
            if "html" not in ctype and "text" not in ctype:
                return {"ok": False, "url": str(r.url), "error": "不是网页"}
            text = r.text
        p = _TextParser(); p.feed(text)
        body = re.sub(r"\n{2,}", "\n", "".join(p.parts)).strip()
        body = re.sub(r"[ \t]{2,}", " ", body)
        return {"ok": bool(body), "url": str(r.url), "title": re.sub(r"\s+", " ", p.title).strip(),
                "content": body[:MAX_PAGE_CHARS]}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)[:200]}


def search_and_fetch(query: str, *, count: int = MAX_RESULTS, fetch_top: int = 3) -> dict:
    results = search(query, count=count)
    for i, x in enumerate(results[:fetch_top]):
        page = fetch_page(str(x.get("url") or ""))
        if page.get("ok"):
            x["content"] = page.get("content") or ""
            if not x.get("title"):
                x["title"] = page.get("title") or ""
    return {"query": query, "results": results, "ok": bool(results)}


def web_context(results: list[dict]) -> str:
    parts = []
    for i, x in enumerate(results[:5], 1):
        content = (x.get("content") or x.get("snippet") or "").strip()
        date = f"\n日期: {x.get('published')}" if x.get("published") else ""
        parts.append(f"[{i}] {x.get('title') or ''}\nURL: {x.get('url') or ''}{date}\n{content[:2600]}")
    return "\n\n".join(parts)
