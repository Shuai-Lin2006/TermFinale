(function () {
  "use strict";
  function toast(msg) {
    var old = document.getElementById("tfPickerToast");
    if (old) old.remove();
    var el = document.createElement("div");
    el.id = "tfPickerToast";
    el.style.cssText = "position:fixed;left:50%;bottom:36px;transform:translateX(-50%);z-index:10020;max-width:min(560px,90vw);background:#141a24;color:#fff;padding:12px 16px;border-radius:10px;font-size:13px;line-height:1.6;box-shadow:0 10px 30px rgba(0,0,0,.25)";
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(function () { el.remove(); }, 5200);
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function parseRange(value, max) {
    var out = [];
    String(value || "").split(/[,，\s]+/).forEach(function (part) {
      var m = part.match(/^(\d+)\s*-\s*(\d+)$/);
      if (m) {
        var a = Math.max(1, parseInt(m[1], 10)), b = Math.min(max, parseInt(m[2], 10));
        for (var i = a; i <= b; i++) out.push(i);
      } else if (/^\d+$/.test(part)) {
        var n = parseInt(part, 10);
        if (n >= 1 && n <= max) out.push(n);
      }
    });
    return Array.from(new Set(out)).sort(function (a, b) { return a - b; });
  }
  function showBusy(msg) {
    var old = document.getElementById("tfBusy");
    if (old) old.remove();
    var root = document.createElement("div");
    root.id = "tfBusy";
    root.style.cssText = "position:fixed;inset:0;z-index:10003;background:rgba(242,246,251,.96);display:flex;align-items:center;justify-content:center;padding:24px";
    root.innerHTML = '<div style="max-width:460px;text-align:center"><div style="width:34px;height:34px;border:3px solid rgba(20,26,36,.15);border-top-color:#0e8f8d;border-radius:50%;margin:0 auto 16px;animation:tfspin .8s linear infinite"></div><div style="font-size:15px;font-weight:600;margin-bottom:6px">' + esc(msg || "处理中…") + '</div><div style="font-size:12.5px;color:#78869a">请先不要关闭窗口；首次生成可能需要 1–3 分钟。</div></div><style>@keyframes tfspin{to{transform:rotate(360deg)}}</style>';
    document.body.appendChild(root);
  }
  function hideBusy() {
    var el = document.getElementById("tfBusy");
    if (el) el.remove();
  }

  function showPreview(data, key, pages, art) {
    var old = document.getElementById("tfPreviewModal");
    if (old) old.remove();
    var root = document.createElement("div");
    root.id = "tfPreviewModal";
    root.style.cssText = "position:fixed;inset:0;z-index:10002;background:#f2f6fb;display:flex;flex-direction:column";
    root.innerHTML = '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 22px;border-bottom:1px solid rgba(20,26,36,.12)"><div><div style="font-size:12px;color:#78869a">预览 · 前 ' + pages.length + ' 页（确认后再生成全部）</div><strong style="font-size:16px">' + (art.title || "选中页") + '</strong></div><div><button id="tfPreviewAgain" style="height:34px;padding:0 14px;border:1px solid rgba(20,26,36,.18);background:#ffffff;border-radius:8px;cursor:pointer;margin-right:8px">重新选择</button><button id="tfPreviewGo" style="height:34px;padding:0 16px;border:0;background:#141a24;color:#ffffff;border-radius:8px;cursor:pointer">同意继续</button></div></div><div style="flex:1;min-height:0;background:#ddd"><iframe src="' + data.pdf_url + '" style="width:100%;height:100%;border:0;display:block"></iframe></div>';
    document.body.appendChild(root);
    root.querySelector("#tfPreviewAgain").onclick = function () { root.remove(); window.tfPickSource(key); };
    root.querySelector("#tfPreviewGo").onclick = function () { root.remove(); window.tfGenerateSelected(key); };
  }

  // 档位规则只有服务端一份真源（tfv2/product/lecture_tiers.py）；
  // 前端不再自己写一遍 50/150/500 的分档，避免两边漂移。
  var TIER_LABEL = {
    standard: "标准讲义", premium: "精品讲义", broad: "高范围讲义", normal: "普通讲义",
  };
  async function fetchPlan(artId, totalPages, pages) {
    var res = await fetch("/api/lecture/plan", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({
        merge: false,
        materials: [{ artifact_id: artId, total_pages: totalPages, pages: pages || [] }],
      }),
    });
    var data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.detail || ("HTTP " + res.status));
    return data;
  }

  async function showTierPicker(key, artId, n, pages) {
    var current = localStorage.getItem("tf-tier-" + key + "-" + artId) || "";
    var plan = null, planError = "";
    try { plan = await fetchPlan(artId, n, pages); }
    catch (e) { planError = e.message || "档位读取失败"; }
    if (!plan && !planError) planError = "档位读取失败";
    var tiers = [];
    if (plan && plan.materials && plan.materials[0]) {
      var m = plan.materials[0];
      tiers = m.tiers.map(function (t) {
        var target = (m.coverage_targets || {})[t];
        var policy = (m.detail_policies || {})[t] || "";
        return [t, TIER_LABEL[t] || t, "覆盖目标 ≥" + target + "%", policy, target >= 65];
      });
    }
    var root = document.createElement("div");
    root.id = "tfTierPicker";
    root.style.cssText = "position:fixed;inset:0;z-index:10005;background:rgba(20,22,25,.55);display:flex;align-items:center;justify-content:center";
    var html = '<div style="width:min(560px,92vw);background:#ffffff;border-radius:16px;padding:24px"><div style="font-size:12px;color:#78869a">资料共 ' + n + ' 页 · 已选 ' + ((pages && pages.length) || 0) + ' 页</div><h2 style="margin:6px 0 6px;font-size:22px">这份资料怎么讲</h2><p style="margin:0 0 16px;color:#4a5666;font-size:13px">页数多时，保证目录、摘要和基本框架；细节和配图会从简。任何档位都不允许遗漏知识点。</p>';
    if (planError) {
      html += '<p style="margin:0 0 14px;padding:10px 12px;background:#fdf3f0;border:1px solid #f0d4cb;border-radius:9px;color:#8a4a35;font-size:13px">档位没能从服务端读取（' + esc(planError) + '），先按本地估算显示，生成时会以服务端规则为准。</p>';
    }
    if (!tiers.length) {
      html += '<p style="margin:0 0 10px;color:#8a4a35;font-size:13px">这些页暂时没有可用档位；请调整选页后重试。</p>';
    }
    var textMode = localStorage.getItem("tf-textmode-" + key + "-" + artId) === "1";
    html += '<label style="display:flex;gap:8px;align-items:flex-start;margin:10px 0 4px;padding:10px 12px;border:1px solid rgba(20,26,36,.12);border-radius:10px;background:#fbfaf6;font-size:13px;cursor:pointer"><input type="checkbox" id="tfTextMode"' + (textMode ? " checked" : "") + ' style="margin-top:3px"><span><strong>文字版（可搜索）</strong><span style="display:block;color:#4a5666;font-size:12px;margin-top:2px">扫描件用本地 OCR 的文字排版，能全文搜索、能出题；代价是公式和版式不如原页清楚。</span></span></label>';
    tiers.forEach(function (t) {
      html += '<button type="button" data-tier="' + t[0] + '" style="display:block;width:100%;text-align:left;margin:8px 0;padding:13px 14px;border:1px solid ' + (current === t[0] ? "#141a24" : "rgba(20,26,36,.12)") + ';border-radius:10px;background:' + (current === t[0] ? "#f2f6fb" : "#ffffff") + ';cursor:pointer"><strong>' + t[1] + '</strong><span style="display:block;color:#4a5666;font-size:12px;margin-top:3px">' + t[2] + (t[4] ? ' · 成本高' : '') + '</span><span style="display:block;color:#78869a;font-size:12px;margin-top:2px">' + esc(t[3]) + '</span></button>';
    });
    html += '<div style="display:flex;justify-content:flex-end;margin-top:14px"><button type="button" id="tfTierBack" style="height:38px;padding:0 16px;border:1px solid rgba(20,26,36,.12);background:#ffffff;border-radius:9px;cursor:pointer">返回重选</button></div></div>';
    root.innerHTML = html;
    document.body.appendChild(root);
    var back = root.querySelector("#tfTierBack");
    if (back) back.onclick = function () { root.remove(); window.tfPickSource(key); };
    var textModeEl = root.querySelector("#tfTextMode");
    if (textModeEl) {
      textModeEl.onchange = function () {
        localStorage.setItem("tf-textmode-" + key + "-" + artId, textModeEl.checked ? "1" : "0");
      };
    }
    root.querySelectorAll("[data-tier]").forEach(function (b) {
      b.onclick = function () {
        localStorage.setItem("tf-tier-" + key + "-" + artId, b.getAttribute("data-tier"));
        var tm = root.querySelector("#tfTextMode");
        localStorage.setItem("tf-textmode-" + key + "-" + artId, tm && tm.checked ? "1" : "0");
        root.remove();
        window.dispatchEvent(new CustomEvent("tf-pages-saved", { detail: { key: key, artifact: artId, tier: b.getAttribute("data-tier") } }));
        // 选完风格直接生成 2 页预览，确认后再生成全部。
        setTimeout(function () { if (window.tfPreviewSelected) window.tfPreviewSelected(key); }, 60);
      };
    });
  }

  window.tfPreviewSelected = async function (key) {
    var info, art, pages;
    try {
      info = await (await fetch("/api/courses/" + encodeURIComponent(key) + "/edit")).json();
      var arts = (info.artifacts || []).filter(function (a) { return a.sources && a.sources.length; });
      art = arts[0] || (info.artifacts || [])[0];
      if (!art) { toast("这门课还没有资料"); return; }
      pages = JSON.parse(localStorage.getItem("tf-pages-" + key + "-" + art.id) || "[]");
      if (!pages.length) { toast("先在「选择资料页」里保存页码"); return; }
      var previewPages = pages.slice(0, 2);
      var btn = document.getElementById("tfPreviewSelected");
      if (btn) { btn.disabled = true; btn.textContent = "生成预览中…"; }
      showBusy("正在生成前 " + previewPages.length + " 页预览…");
      var ctrl = (typeof AbortController !== "undefined") ? new AbortController() : null;
      var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, 240000) : null;
      var res;
      try {
        res = await fetch("/api/artifacts/" + encodeURIComponent(art.id) + "/preview-selected", {
          method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ pages: previewPages, tier: localStorage.getItem("tf-tier-" + key + "-" + art.id) || "" }),
          signal: ctrl ? ctrl.signal : undefined,
        });
      } catch (err) {
        if (err && err.name === "AbortError") throw new Error("预览超时（4 分钟），请检查 API Key 或减少页数");
        throw err;
      } finally { if (timer) clearTimeout(timer); }
      var data = await res.json();
      if (!res.ok) throw new Error(data.detail || ("HTTP " + res.status));
      hideBusy();
      showPreview(data, key, previewPages, art);
    } catch (e) {
      hideBusy();
      toast("预览失败：" + e.message);
    } finally {
      var btn2 = document.getElementById("tfPreviewSelected");
      if (btn2) { btn2.disabled = false; btn2.textContent = "预览已选页"; }
    }
  };

  window.tfGenerateSelected = async function (key) {
    var info, art, pages;
    try {
      info = await (await fetch("/api/courses/" + encodeURIComponent(key) + "/edit")).json();
      var arts = (info.artifacts || []).filter(function (a) { return a.sources && a.sources.length; });
      art = arts[0] || (info.artifacts || [])[0];
      if (!art) { toast("这门课还没有资料"); return; }
      pages = JSON.parse(localStorage.getItem("tf-pages-" + key + "-" + art.id) || "[]");
      if (!pages.length) { toast("先保存选页"); return; }
      if (pages.length > 2000) { toast("单次最多 2000 页，更多资料请拆分"); return; }
      var res = await fetch("/api/artifacts/" + encodeURIComponent(art.id) + "/generate-selected", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({
          pages: pages,
          tier: localStorage.getItem("tf-tier-" + key + "-" + art.id) || "",
          text_mode: localStorage.getItem("tf-textmode-" + key + "-" + art.id) === "1",
        })
      });
      var data = await res.json();
      if (!res.ok) throw new Error(data.detail || ("HTTP " + res.status));
      runOverlay(data.job_id, art.title || "", key);
    } catch (e) { toast("生成失败：" + e.message); }
  };

  function runOverlay(jobId, title, key) {
    var old = document.getElementById("tfGenOverlay");
    if (old) old.remove();
    var started = Date.now();
    var root = document.createElement("div");
    root.id = "tfGenOverlay";
    root.style.cssText = "position:fixed;inset:0;z-index:10001;background:#f2f6fb;display:flex;align-items:center;justify-content:center;padding:32px";
    root.innerHTML = '<div style="width:min(880px,94vw)">' +
      '<div style="display:flex;justify-content:space-between;align-items:center"><div style="font-size:12px;letter-spacing:.12em;color:#78869a">正在生成</div><div><button id="tfGenBack" style="height:36px;padding:0 14px;border:1px solid rgba(20,26,36,.18);background:transparent;border-radius:8px;margin-right:8px;cursor:pointer">返回</button><button id="tfGenCancel" style="height:36px;padding:0 14px;border:0;background:#141a24;color:#ffffff;border-radius:8px;cursor:pointer">取消</button></div></div>' +
      '<h2 style="margin:22px 0 6px;font-size:26px">' + esc(title) + '</h2>' +
      '<p id="tfGenStep" style="margin:0;color:#4a5666;font-size:14px">准备中</p>' +
      '<div style="height:8px;background:rgba(20,26,36,.12);border-radius:99px;margin:26px 0 12px;overflow:hidden"><i id="tfGenBar" style="display:block;height:100%;width:0;background:#141a24;border-radius:99px;transition:width .4s"></i></div>' +
      '<div style="display:flex;justify-content:space-between;color:#4a5666;font-size:13px"><span id="tfGenPct">0%</span><span id="tfGenTime"></span></div>' +
      '<div id="tfGenResult" style="margin-top:32px;display:none"><a id="tfGenOpen" style="display:inline-block;background:#141a24;color:#ffffff;padding:12px 22px;border-radius:9px;text-decoration:none">打开 PDF</a></div>' +
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
          resultEl.style.display = "block";
          var href = "";
          if (result) {
            if (result.pdf_url) href = result.pdf_url;
            else if (result.id) href = "/artifact/" + encodeURIComponent(result.id) + "/lecture.pdf";
          }
          if (href) openEl.href = href;
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

  window.tfPickSource = async function (key) {
    var info, art, meta;
    try {
      info = await (await fetch("/api/courses/" + encodeURIComponent(key) + "/edit")).json();
      var arts = (info.artifacts || []).filter(function (a) { return a.sources && a.sources.length; });
      art = arts[0] || (info.artifacts || [])[0];
      if (!art) { toast("这门课还没有资料"); return; }
      meta = await (await fetch("/api/artifacts/" + encodeURIComponent(art.id) + "/pages")).json();
    } catch (e) { toast("页面读取失败：" + e.message); return; }
    var old = document.getElementById("tfPicker");
    if (old) old.remove();
    var selected = new Set();
    try {
      var saved = JSON.parse(localStorage.getItem("tf-pages-" + key + "-" + art.id) || "[]");
      saved.forEach(function (n) { if (n >= 1 && n <= meta.page_count) selected.add(n); });
    } catch (e) {}
    var root = document.createElement("div");
    root.id = "tfPicker";
    root.style.cssText = "position:fixed;inset:0;z-index:9999;background:rgba(20,22,25,.55);display:flex;align-items:center;justify-content:center;padding:24px";
    root.innerHTML = '<div style="width:min(1180px,96vw);max-height:90vh;background:#ffffff;border-radius:18px;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 24px 80px rgba(0,0,0,.28)">' +
      '<div style="display:flex;align-items:center;justify-content:space-between;padding:18px 22px;border-bottom:1px solid #e8e6df"><div><div style="font-size:12px;color:#78869a;letter-spacing:.08em">选择资料页</div><h2 style="margin:4px 0 0;font-size:20px">' + esc(art.title || art.id) + '</h2></div><button id="tfPickerClose" style="border:0;background:#f2f0e9;border-radius:99px;width:36px;height:36px;font-size:18px;cursor:pointer">×</button></div>' +
      '<div style="display:flex;gap:10px;align-items:center;padding:14px 22px;border-bottom:1px solid #eee"><input id="tfPickerRange" placeholder="范围，例如 1-12,20" style="flex:1;height:38px;border:1px solid rgba(20,26,36,.16);border-radius:8px;padding:0 12px"><button id="tfPickerRangeGo" style="height:38px;padding:0 14px;border:1px solid rgba(20,26,36,.16);background:#ffffff;border-radius:8px;cursor:pointer">应用范围</button><button id="tfPickerAll" style="height:38px;padding:0 14px;border:1px solid rgba(20,26,36,.16);background:#ffffff;border-radius:8px;cursor:pointer">全选</button><button id="tfPickerNone" style="height:38px;padding:0 14px;border:1px solid rgba(20,26,36,.16);background:#ffffff;border-radius:8px;cursor:pointer">清空</button><span id="tfPickerCount" style="font-size:13px;color:#4a5666;min-width:90px;text-align:right"></span></div>' +
      '<div id="tfPickerGrid" style="padding:18px 22px;overflow:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px"></div>' +
      '<div style="padding:14px 22px;border-top:1px solid #eee;display:flex;justify-content:space-between;align-items:center"><span style="font-size:13px;color:#78869a">只保存页码选择；生成在下一步确认。</span><button id="tfPickerSave" style="height:40px;padding:0 22px;border:0;border-radius:9px;background:#141a24;color:#ffffff;font-size:14px;cursor:pointer">保存选择</button></div></div>';
    document.body.appendChild(root);
    var grid = root.querySelector("#tfPickerGrid");
    var count = root.querySelector("#tfPickerCount");
    function paintCount() { count.textContent = "已选 " + selected.size + " 页"; }
    function toggle(n) { if (selected.has(n)) selected.delete(n); else selected.add(n); }
    for (var p = 1; p <= meta.page_count; p++) {
      var cell = document.createElement("button");
      cell.type = "button";
      cell.dataset.page = String(p);
      cell.style.cssText = "position:relative;padding:0;border:2px solid " + (selected.has(p) ? "#141a24" : "#e4e0d6") + ";background:#ffffff;border-radius:8px;overflow:hidden;cursor:pointer;height:230px";
      cell.innerHTML = '<img loading="eager" src="/api/artifacts/' + encodeURIComponent(art.id) + '/page/' + p + '.png" alt="" style="display:block;width:100%;height:210px;object-fit:contain;background:#ffffff">' +
        '<span style="position:absolute;left:6px;top:6px;background:' + (selected.has(p) ? "#141a24" : "rgba(255,255,255,.92)") + ';color:' + (selected.has(p) ? "#ffffff" : "#3b3a35") + ';border-radius:4px;padding:1px 6px;font-size:11px">' + p + '</span>';
      cell.onclick = function (e) {
        e.preventDefault();
        var n = Number(this.dataset.page);
        toggle(n);
        this.style.borderColor = selected.has(n) ? "#141a24" : "#e4e0d6";
        var badge = this.querySelector("span");
        badge.style.background = selected.has(n) ? "#141a24" : "rgba(255,255,255,.92)";
        badge.style.color = selected.has(n) ? "#ffffff" : "#3b3a35";
        paintCount();
      };
      grid.appendChild(cell);
    }
    paintCount();
    root.querySelector("#tfPickerClose").onclick = function () { root.remove(); };
    root.querySelector("#tfPickerAll").onclick = function () {
      for (var i = 1; i <= meta.page_count; i++) selected.add(i);
      root.querySelectorAll("[data-page]").forEach(function (el) { el.style.borderColor = "#141a24"; var b = el.querySelector("span"); b.style.background = "#141a24"; b.style.color = "#ffffff"; });
      paintCount();
    };
    root.querySelector("#tfPickerNone").onclick = function () {
      selected.clear();
      root.querySelectorAll("[data-page]").forEach(function (el) { el.style.borderColor = "#e4e0d6"; var b = el.querySelector("span"); b.style.background = "rgba(255,255,255,.92)"; b.style.color = "#3b3a35"; });
      paintCount();
    };
    root.querySelector("#tfPickerRangeGo").onclick = function () {
      selected = new Set(parseRange(root.querySelector("#tfPickerRange").value, meta.page_count));
      root.querySelectorAll("[data-page]").forEach(function (el) {
        var on = selected.has(Number(el.dataset.page));
        el.style.borderColor = on ? "#141a24" : "#e4e0d6";
        var b = el.querySelector("span"); b.style.background = on ? "#141a24" : "rgba(255,255,255,.92)"; b.style.color = on ? "#ffffff" : "#3b3a35";
      });
      paintCount();
    };
    root.querySelector("#tfPickerSave").onclick = function () {
      localStorage.setItem("tf-pages-" + key + "-" + art.id, JSON.stringify(Array.from(selected).sort(function (a, b) { return a - b; })));
      var label = root.querySelector("#tfPickerSave"); label.textContent = "已保存 " + selected.size + " 页";
      root.remove();
      showTierPicker(key, art.id, meta.page_count, Array.from(selected).sort(function (a, b) { return a - b; }));
    };
  };
})();