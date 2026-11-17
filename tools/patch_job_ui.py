from pathlib import Path
p = Path("web_v2/job.html")
s = p.read_text()
s = s.replace('"><button class="ghost small">删除</button>', '"><input class="artifact" placeholder="artifact_id（可选）"><button class="ghost small">删除</button>')
s = s.replace("pages:Math.max(1,parseInt(x.querySelector('.pages').value||'1'))",
              "pages:Math.max(1,parseInt(x.querySelector('.pages').value||'1')),artifact_id:x.querySelector('.artifact').value")
s = s.replace("job=await post('/api/job/'+job.job_id+'/confirm');jobline.textContent='任务 '+job.job_id+' · '+job.stage;",
              "job=await post('/api/job/'+job.job_id+'/confirm');await post('/api/job/'+job.job_id+'/start');jobline.textContent='任务 '+job.job_id+' · 已确认并启动 worker';")
p.write_text(s)
print("artifact", 'artifact_id:x' in s, "start", '/start' in s, "input", 'placeholder="artifact_id' in s)
