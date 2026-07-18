# API 接口文档 v1

> 方向 A：智能数字媒体内容审核系统

## 通用约定

### 响应格式

```json
// 成功
{ "ok": true, ... }

// 失败
{ "ok": false, "error": "可读的中文错误信息" }
```

### 状态码

| 状态码 | 含义 |
|---|---|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 参数错误 |
| 404 | 资源不存在 |
| 409 | 状态冲突（操作不允许） |
| 500 | 服务器内部错误 |

---

## 公共接口

### `GET /api/health`

健康检查。

**响应**:

```json
{
  "status": "ok",
  "model_ready": true,
  "direction": "A"
}
```

---

### `POST /api/jobs`

创建任务并上传素材。

**请求**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | File | 是 | 上传文件 (jpg/jpeg/png/mp4/avi/mov/webm, ≤500MB) |
| `project_name` | String | 是 | 项目名称 |

**成功响应** (201):

```json
{
  "ok": true,
  "job_id": "20260718_101530_a1b2c3d4"
}
```

**错误响应**:

```json
// 400 — 缺少文件
{ "ok": false, "error": "缺少上传文件" }

// 400 — 文件为空
{ "ok": false, "error": "文件为空" }

// 400 — 不支持格式
{ "ok": false, "error": "不支持的文件格式: xyz。支持: jpg, jpeg, png, mp4, avi, mov, webm" }

// 400 — 缺少项目名称
{ "ok": false, "error": "缺少项目名称" }
```

---

### `GET /api/jobs`

获取所有任务列表（按创建时间倒序）。

**响应**:

```json
{
  "ok": true,
  "jobs": [
    {
      "job_id": "20260718_101530_a1b2c3d4",
      "project_name": "星港遗迹内容审核",
      "asset_name": "opening_scene.mp4",
      "status": "completed",
      "created_at": "2026-07-18T10:15:30"
    }
  ]
}
```

---

### `GET /api/jobs/<job_id>`

获取单个任务完整信息（含分析报告）。

**响应**:

```json
{
  "ok": true,
  "job": {
    "job_id": "...",
    "project_name": "...",
    "asset_name": "...",
    "status": "completed",
    "created_at": "...",
    "started_at": "...",
    "completed_at": "...",
    "settings": { ... },
    "error": null
  },
  "report": { ... }
}
```

**错误** (404):

```json
{ "ok": false, "error": "任务不存在" }
```

---

### `DELETE /api/jobs/<job_id>`

删除任务及其所有文件。

**限制**: 无法删除 `queued` 或 `running` 状态的任务。

**响应**:

```json
{ "ok": true }
```

**错误** (409):

```json
{ "ok": false, "error": "任务状态为 running，无法删除。只能删除已完成或失败的任务" }
```

---

## 方向 A 专属接口

### `POST /api/jobs/<job_id>/analyze`

触发（或重新）执行 YOLO 分析。异步执行，立即返回。

**响应**:

```json
{
  "ok": true,
  "job_id": "...",
  "status": "queued"
}
```

---

### `PATCH /api/jobs/<job_id>/review`

人工修改审核结论。

**请求** (`application/json`):

```json
{
  "verdict": "pass",
  "reviewer": "张三",
  "notes": "经人工审核，未发现违规内容"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `verdict` | String | 是 | `pass` / `review` / `reject` |
| `reviewer` | String | 否 | 审核人姓名 |
| `notes` | String | 否 | 审核备注 |

**响应**:

```json
{ "ok": true }
```

**错误** (400):

```json
{ "ok": false, "error": "无效的审核结论: xxx，必须是 pass / review / reject" }
```

---

### `GET /api/jobs/<job_id>/report`

获取审核报告。

**响应**:

```json
{
  "ok": true,
  "report": {
    "job_id": "...",
    "project_name": "...",
    "asset_name": "...",
    "analyzed_at": "...",
    "auto_verdict": "pass",
    "auto_verdict_reason": "...",
    "manual_review": null,
    "detection_summary": { ... },
    "risk_detections": [ ... ],
    "evidence_frames": [ ... ],
    "statistics": { ... },
    "applied_settings": { ... }
  }
}
```

---

## 任务状态机

```text
created → queued → running → completed
                            └→ failed (可重新 queued)
```

| 状态 | 含义 |
|---|---|
| `created` | 任务已创建 |
| `queued` | 排队等待处理 |
| `running` | 正在处理中 |
| `completed` | 处理完成 |
| `failed` | 处理失败 |
