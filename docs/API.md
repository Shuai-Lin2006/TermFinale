# TermFinale HTTP API

共 112 个路径。自动生成：`python scripts/export_openapi.py`。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | Index |
| GET | `/api/agent/goals` | Agent Goals |
| POST | `/api/agent/goals` | Save Agent Goal |
| GET | `/api/agent/goals/due` | Agent Goals Due |
| POST | `/api/agent/goals/run-due` | Run Due Agent Goals |
| POST | `/api/agent/goals/{gid}/advance` | Advance Agent Goal |
| POST | `/api/agent/goals/{gid}/plan` | Plan Agent Goal |
| POST | `/api/agent/jobs` | Agent Job |
| GET | `/api/agent/memories` | Agent Memories |
| POST | `/api/agent/plan` | Agent Plan |
| POST | `/api/agent/run` | Agent Run |
| GET | `/api/agent/runs` | Agent Runs |
| POST | `/api/agent/runs/{job_id}/replan` | Replan Agent Run |
| POST | `/api/agent/runs/{job_id}/resume` | Resume Agent Run |
| GET | `/api/agent/tools` | Agent Tools |
| GET | `/api/agent/workflows` | Agent Workflows |
| POST | `/api/agent/workflows` | Save Agent Workflow |
| GET | `/api/agent/workflows/{wid}` | Get Agent Workflow |
| GET | `/api/agent/workflows/{wid}/diff` | Diff Agent Workflow |
| GET | `/api/artifacts` | Artifacts |
| GET | `/api/artifacts/{aid}` | Artifact |
| POST | `/api/artifacts/{aid}/audit` | Artifact Audit |
| GET | `/api/artifacts/{aid}/backups` | Artifact Backups |
| GET | `/api/artifacts/{aid}/export.html` | Artifact Export Html |
| POST | `/api/artifacts/{aid}/generate-selected` | Artifact Generate Selected |
| GET | `/api/artifacts/{aid}/metrics` | Artifact Metrics |
| GET | `/api/artifacts/{aid}/page/{page_no}.png` | Artifact Page Png |
| GET | `/api/artifacts/{aid}/pages` | Artifact Pages |
| POST | `/api/artifacts/{aid}/preview-selected` | Artifact Preview Selected |
| POST | `/api/artifacts/{aid}/restore` | Restore Artifact |
| POST | `/api/artifacts/{aid}/review` | Review Artifact |
| POST | `/api/artifacts/{aid}/rewrite` | Rewrite Artifact |
| POST | `/api/artifacts/{aid}/save` | Save Artifact To Desktop |
| GET | `/api/artifacts/{aid}/units` | Artifact Units |
| DELETE | `/api/artifacts/{draft_id}` | Discard Draft |
| POST | `/api/artifacts/{draft_id}/accept` | Accept Rewrite |
| POST | `/api/ask` | Ask |
| POST | `/api/ask/stream` | Ask Stream |
| POST | `/api/attempts` | Attempt |
| GET | `/api/backup` | Create Backup |
| GET | `/api/bank` | Bank List |
| GET | `/api/bank/counts` | Bank Counts |
| DELETE | `/api/bank/{question_id}` | Bank Delete |
| DELETE | `/api/chat/{aid}` | Delete Chat |
| GET | `/api/chat/{aid}` | Get Chat |
| PUT | `/api/course-prefs/{key}` | Put Course Prefs |
| GET | `/api/courses` | Courses |
| POST | `/api/courses/save-sources` | Save Course Sources |
| DELETE | `/api/courses/{key}` | Archive Course |
| GET | `/api/courses/{key}` | Course |
| DELETE | `/api/courses/{key}/artifacts/{artifact_id}` | Archive Course Artifact |
| GET | `/api/courses/{key}/edit` | Course Edit Info |
| POST | `/api/courses/{key}/generate-edit` | Course Generate Edit |
| POST | `/api/courses/{key}/save-edit` | Course Save Edit |
| GET | `/api/documents` | Documents |
| DELETE | `/api/documents/{did}` | Remove Document |
| GET | `/api/documents/{did}` | Document |
| PATCH | `/api/documents/{did}` | Rename Document |
| GET | `/api/documents/{did}/docx` | Document Docx |
| GET | `/api/documents/{did}/export.csv` | Export Questions Csv |
| GET | `/api/documents/{did}/pdf` | Document Pdf |
| POST | `/api/documents/{did}/save` | Save Document To Desktop |
| POST | `/api/documents/{doc_id}/bank` | Import Bank |
| POST | `/api/exam` | Create Exam |
| POST | `/api/exam/attempts` | Submit Exam Attempt |
| POST | `/api/exam/jobs` | Create Exam Job |
| POST | `/api/exam/jobs/{job_id}/resume` | Resume Exam Job |
| POST | `/api/exam/units` | Exam Units |
| POST | `/api/exclusions/preview` | Exclusions Preview |
| POST | `/api/feedback` | Ai Feedback |
| GET | `/api/figures/subjects` | Figure Subjects |
| POST | `/api/generate` | Create Generation |
| POST | `/api/generate-multi` | Create Multi Generation |
| GET | `/api/health` | Health |
| GET | `/api/home` | Home |
| POST | `/api/job/create` | Job Create |
| POST | `/api/job/estimate` | Job Estimate |
| GET | `/api/job/{job_id}` | Job Get |
| POST | `/api/job/{job_id}/cancel` | Job Cancel |
| POST | `/api/job/{job_id}/confirm` | Job Confirm |
| GET | `/api/job/{job_id}/events` | Job Events |
| GET | `/api/job/{job_id}/events/stream` | Job Events Stream |
| POST | `/api/job/{job_id}/preview` | Job Preview |
| GET | `/api/job/{job_id}/preview.pdf` | Job Preview Pdf |
| POST | `/api/job/{job_id}/start` | Job Start |
| GET | `/api/jobs` | List Recent Jobs |
| GET | `/api/jobs/{job_id}` | Job Status |
| POST | `/api/jobs/{job_id}/cancel` | Cancel Job |
| POST | `/api/jobs/{job_id}/retry` | Retry Job |
| POST | `/api/lecture/combine` | Lecture Combine |
| POST | `/api/lecture/fuse-jobs` | Create Fuse Job |
| POST | `/api/lecture/plan` | Lecture Plan |
| POST | `/api/lectures/jobs/{job_id}/resume` | Resume Lecture Job |
| GET | `/api/mastery` | Mastery |
| GET | `/api/modules` | Modules Summary |
| GET | `/api/notes` | Notes |
| POST | `/api/notes` | Add Note |
| DELETE | `/api/notes/{note_id}` | Remove Note |
| POST | `/api/practice` | Practice |
| POST | `/api/practice/bank` | Practice Bank |
| POST | `/api/practice/source` | Practice Source |
| GET | `/api/previews/{job_id}.pdf` | Preview Selected Pdf |
| GET | `/api/quality/tiers` | Quality Tiers |
| GET | `/api/review` | Review |
| GET | `/api/review/due` | Review Due |
| POST | `/api/review/{mistake_id}` | Review Item |
| POST | `/api/save-html` | Save Html To Desktop |
| GET | `/api/search` | Library Search |
| GET | `/api/settings` | Settings |
| POST | `/api/settings` | Save Settings |
| GET | `/api/settings/keys` | Key Settings |
| POST | `/api/settings/keys` | Save Keys |
| POST | `/api/settings/test` | Test Keys |
| POST | `/api/tasks` | Run Task |
| POST | `/api/tasks/jobs` | Create Task Job |
| POST | `/api/tasks/units` | Run Units Task |
| GET | `/api/usage` | Token Usage |
| GET | `/artifact/{aid}/lecture.docx` | Artifact Docx |
| GET | `/artifact/{aid}/{rel}` | Artifact File |
| GET | `/job` | Job Page |
| GET | `/modules` | Modules Page |
