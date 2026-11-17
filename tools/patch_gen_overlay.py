from pathlib import Path
p = Path("web_v2/picker.js")
s = p.read_text()
a = s.index("  window.tfGenerateSelected = async function (key) {")
b = s.index("  window.tfPickSource = async function (key) {")
new = """  window.tfGenerateSelected = async function (key) {
    var info, art, pages;
    try {
      info = await (await fetch("/api/courses/" + encodeURIComponent(key) + "/edit")).json();
      var arts = (info.artifacts || []).filter(function (a) { return a.sources && a.sources.length; });
      art = arts[0] || (info.artifacts || [])[0];
      if (!art) { window.alert("这门课还没有资料"); return; }
      pages = JSON.parse(localStorage.getItem("tf-pages-" + key + "-" + art.id) || "[]");
      if (!pages.length) { window.alert("先保存选页"); return; }
      if (pages.length > 8) { window.alert("当前单次最多 8 页，后续支持分批全量"); return; }
      var res = await fetch("/api/artifacts/" + encodeURIComponent(art.id) + "/generate-selected", {
        method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ pages: pages })
      });
      var data = await res.json();
      if (!res.ok) throw new Error(data.detail || ("HTTP " + res.status));
      runOverlay(data.job_id, art.title || "", key);
    } catch (e) { window.alert("生成失败：" + e.message); }
  };

  function runOverlay(jobId, title, key) {
    var old = document.getElementById("tfGenOverlay");
    if (old) old.remove();
    var started = Date.now();
    var root = document.createElement("div");
    root.id = "tfGenOverlay";
    root.style.cssText = "position:fixed;inset:0;z-index:10001;background:#f4f1e8;display:flex;align-items:center;justify-content:center;padding:32px";
    root.innerHTML = '<div style="width:min(880px,94vw)">' +
      '<div style="display:flex;justify-content:space-between;align-items:center"><div style="font-size:12px;letter-spacing:.12em;color:#8a8579">正在生成</div><div><button id="tfGenBack" style="height:36px;padding:0 14px;border:1px solid #d7d2c4;background:transparent;border-radius:8px;margin-right:8px;cursor:pointer">返回</button><button id="tfGenCancel" style="height:36px;padding:0 14px;border:0;background:#1f2328;color:#fff;border-radius:8px;cursor:pointer">取消</button></div></div>' +
      '<h2 style="margin:22px 0 6px;font-size:26px">' + esc(title) + '</h2>' +
      '<p id="tfGenStep" style="margin:0;color:#6d6a60;font-size:14px">准备中</p>' +
      '<div style="height:8px;background:#ded9ca;border-radius:99px;margin:26px 0 12px;overflow:hidden"><i id="tfGenBar" style="display:block;height:100%;width:0;background:#1f2328;border-radius:99px;transition:width .4s"></i></div>' +
      '<div style="display:flex;justify-content:space-between;color:#6d6a60;font-size:13px"><span id="tfGenPct">0%</span><span id="tfGenTime"></span></div>' +
      '<div id="tfGenResult" style="margin-top:32px;display:none"><a id="tfGenOpen" style="display:inline-block;background:#1f2328;color:#fff;padding:12px 22px;border-radius:9px;text-decoration:none">打开 PDF</a></div>' +
      '</div>';
    document.body.appendChild(root);
    var bar = root.querySelector("#tfGenBar"), pctEl = root.querySelector("#tfGenPct"), stepEl = root.querySelector("#tfGenStep"), timeEl = root.querySelector("#tfGenTime"), resultEl = root.querySelector("#tfGenResult"), openEl = root.querySelector("#tfGenOpen");
    var timer = null;

    function close() { if (timer) clearInterval(timer); root.remove(); }
    root.querySelector("#tfGenBack").onclick = close;
    root.querySelector("#tfGenCancel").onclick = async function () {
      try { await fetch("/api/jobs/" + encodeURIComponent(jobId) + "/cancel", { method: "POST" }); } catch (e) {}
      close();
    };
    async function poll() {
      try {
        var job = await (await fetch("/api/jobs/" + encodeURIComponent(jobId))).json();
        var pct = Math.max(0, Math.min(100, Number(job.progress) || 0));
        bar.style.width = pct + "%"; pctEl.textContent = pct + "%";
        stepEl.textContent = job.step || "生成中";
        var elapsed = Math.round((Date.now() - started) / 1000);
        var eta = pct > 2 ? Math.round(elapsed * (100 - pct) / pct) : null;
        timeEl.textContent = "已用 " + elapsed + " 秒" + (eta != null ? " · 约剩 " + eta + " 秒" : "");
        if (job.status === "done") {
          clearInterval(timer);
          var result = job.result;
          try { result = typeof result === "string" ? JSON.parse(result) : result; } catch (e) {}
          var aid = result && result.id;
          resultEl.style.display = "block";
          if (aid) openEl.href = "/artifact/" + encodeURIComponent(aid) + "/lecture.pdf";
          openEl.textContent = "打开 PDF";
          stepEl.textContent = "生成完成";
          return;
        }
        if (job.status === "failed") {
          clearInterval(timer);
          stepEl.textContent = "生成失败：" + (job.error || "请重试");
          return;
        }
        if (job.status === "cancelled") { clearInterval(timer); stepEl.textContent = "已取消"; return; }
      } catch (e) { stepEl.textContent = "进度读取失败，仍在尝试"; }
    }
    timer = setInterval(poll, 1200);
    poll();
  }

"""
p.write_text(s[:a] + new + s[b:])
print("patched")
