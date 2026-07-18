# 系统设计文档 — ContentGuard

## 1. 架构概览

```text
┌────────────────────────────────────────────────────────────────────┐
│                        浏览器 (Chrome/Edge)                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              templates/index.html (单页应用)                   │  │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │  │
│  │  │ 上传组件 │  │ 任务列表  │  │ 结果展示  │  │ 人工审核组件  │  │  │
│  │  └─────────┘  └──────────┘  └──────────┘  └──────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                    static/app.js  │  static/style.css               │
└────────────────────────┬───────────────────────────────────────────┘
                         │  HTTP (Fetch API)
                         │  GET/POST/PATCH/DELETE
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│                     Flask 应用服务器 (app.py)                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     routes/ (路由层)                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │   │
│  │  │ jobs.py   │  │review.py │  │validators.py│                │   │
│  │  │ 任务 CRUD │  │ 审核接口  │  │ 参数校验   │                │   │
│  │  └──────────┘  └──────────┘  └──────────┘                   │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│  ┌──────────────────────────▼──────────────────────────────────┐   │
│  │                    services/ (服务层)                         │   │
│  │  ┌────────────────┐  ┌────────────────────┐                  │   │
│  │  │ detector.py     │  │ review_engine.py   │                  │   │
│  │  │ YOLO 检测封装   │  │ 审核规则引擎        │                  │   │
│  │  │ - 图片检测      │  │ - evaluate()        │                  │   │
│  │  │ - 视频采样检测  │  │ - format_report()   │                  │   │
│  │  └───────┬────────┘  └─────────┬──────────┘                  │   │
│  │          │                     │                              │   │
│  │          ▼                     │                              │   │
│  │  ┌────────────────┐           │                              │   │
│  │  │ Ultralytics     │           │                              │   │
│  │  │ YOLO11n         │           │                              │   │
│  │  └────────────────┘           │                              │   │
│  └───────────────────────────────┴──────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    数据层 (文件系统)                           │   │
│  │  outputs/<job_id>/                                            │   │
│  │  ├── input/              ← 上传的原始文件                      │   │
│  │  ├── keyframes/          ← 证据帧 jpg                         │   │
│  │  ├── result/             ← 中间结果                           │   │
│  │  ├── job.json            ← 任务状态和元数据                    │   │
│  │  └── analysis_report.json ← 完整审核报告                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

### 架构说明

- **三层结构**：路由层（请求处理）→ 服务层（业务逻辑）→ 数据层（文件系统）
- **后台线程**：耗时的 YOLO 检测在独立线程中执行，不阻塞 HTTP 响应
- **前后端分离**：前端纯静态页面，通过 Fetch API 与后端通信
- **无状态 API**：每次请求独立，任务状态持久化在 `job.json` 中

---

## 2. 技术选型

| 层 | 技术 | 版本 | 理由 |
|---|---|---|---|
| **后端框架** | Flask | 3.x | 任务书指定，轻量够用 |
| **目标检测** | Ultralytics YOLO11n | latest | 预训练模型，速度快，开箱即用 |
| **图像处理** | OpenCV (cv2) | 4.x | 视频解码、帧采样、图像保存 |
| **视频编码** | FFmpeg | 系统安装 | 方向 A 不强制，仅加分功能用 |
| **前端** | Vanilla HTML/CSS/JS | — | 任务书指定，无框架 |
| **数据存储** | JSON + 本地文件系统 | — | 任务书指定 |
| **Python** | CPython | 3.10+ | Conda yolo 环境 |

---

## 3. 模块设计

### 3.1 路由层 (`routes/`)

```text
routes/
├── __init__.py        ← 蓝图注册
├── jobs.py            ← 任务 CRUD + 文件上传
├── review.py          ← 审核相关接口
└── validators.py      ← 参数校验函数
```

#### 蓝图注册

```python
# routes/__init__.py
from flask import Blueprint

jobs_bp = Blueprint('jobs', __name__)
review_bp = Blueprint('review', __name__)

from routes import jobs, review  # 导入路由定义

def register_routes(app):
    app.register_blueprint(jobs_bp)
    app.register_blueprint(review_bp)
```

#### jobs.py 路由

```python
# 所有路由前缀: /api
@jobs_bp.route('/api/health', methods=['GET'])
def health(): ...

@jobs_bp.route('/api/jobs', methods=['POST'])
def create_job(): ...

@jobs_bp.route('/api/jobs', methods=['GET'])
def list_jobs(): ...

@jobs_bp.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id): ...

@jobs_bp.route('/api/jobs/<job_id>', methods=['DELETE'])
def delete_job(job_id): ...
```

#### review.py 路由

```python
@review_bp.route('/api/jobs/<job_id>/analyze', methods=['POST'])
def analyze_job(job_id): ...

@review_bp.route('/api/jobs/<job_id>/review', methods=['PATCH'])
def review_job(job_id): ...

@review_bp.route('/api/jobs/<job_id>/report', methods=['GET'])
def get_report(job_id): ...
```

### 3.2 服务层 (`services/`)

```text
services/
├── __init__.py
├── detector.py        ← YOLO 检测封装（Detector 单例类）
└── review_engine.py   ← 审核规则引擎（纯函数）
```

#### detector.py 职责

- 封装 Ultralytics YOLO 模型加载和推理
- 提供 `detect_image()` 和 `detect_video()` 两个方法
- 所有方法不抛异常，失败返回空列表
- 检测结果统一为 `[{class, class_id, confidence, bbox}, ...]`

#### review_engine.py 职责

- `evaluate()`: 根据检测结果 + 审核规则 → 输出 verdict
- `format_report()`: 合并检测结果 + 审核结论 → 最终报告 JSON
- 规则可配置（通过 settings 字典传入）

### 3.3 数据层

```text
outputs/
└── <job_id>/                        ← 每个任务独立目录
    ├── input/                       ← 用户上传的原始文件
    │   └── <original_filename>
    ├── keyframes/                   ← 证据帧（审核截图）
    │   ├── frame_0000.jpg
    │   └── frame_0015.jpg
    ├── result/                      ← 中间分析结果
    │   └── detection_result.json
    ├── job.json                     ← 任务元数据（状态、时间、配置）
    └── analysis_report.json         ← 最终审核报告（含人工审核结果）
```

---

## 4. 数据流

### 4.1 上传 → 分析 → 审核 完整数据流

```text
用户上传文件
    │
    ▼
POST /api/jobs (multipart/form-data)
    │
    ├─ 1. 生成 job_id = 20260718_101530_a1b2c3d4
    ├─ 2. mkdir outputs/<job_id>/input/
    ├─ 3. 保存文件 → input/original.jpg
    ├─ 4. 写入 job.json (status: "created")
    ├─ 5. 返回 job_id
    └─ 6. 启动后台线程 _run_analysis(job_id)

后台线程 _run_analysis():
    │
    ├─ 7. 更新 job.json (status: "running", started_at)
    ├─ 8. 调用 services/detector.py::detect(file_path, job_dir)
    │      │
    │      ├─ 加载 YOLO 模型
    │      ├─ 图片: 直接检测
    │      └─ 视频: cv2 逐秒采样 → YOLO 逐帧检测
    │           │
    │           └─ 保存证据帧 → keyframes/frame_XXXX.jpg
    │
    ├─ 9. 调用 services/review_engine.py::evaluate(detection_result, settings)
    │      │
    │      └─ 遍历检测结果 → 按规则判定 → 输出 {verdict, reason, risk_detections}
    │
    ├─ 10. 调用 format_report() → 生成 analysis_report.json
    └─ 11. 更新 job.json (status: "completed", completed_at)

用户查看结果:
    │
    ▼
GET /api/jobs/<job_id>/report
    │
    └─ 返回 analysis_report.json

用户人工审核:
    │
    ▼
PATCH /api/jobs/<job_id>/review
    │
    ├─ 读取 analysis_report.json
    ├─ 更新 manual_review 字段
    └─ 写回文件
```

### 4.2 异常路径

```text
任何步骤抛异常:
    │
    ├─ 捕获异常 → 提取 traceback
    ├─ 更新 job.json:
    │     status: "failed"
    │     error: "<完整的错误信息>"
    └─ job.json 确保落盘（不能只在控制台输出）
```

---

## 5. 目录结构

```text
team_content_review/
├── app.py                          # Flask 入口，注册蓝图，配置启动参数
├── requirements.txt                # Python 依赖清单
├── .gitignore                      # Git 忽略规则
├── README.md                       # 项目启动和说明
│
├── models/                         # 模型文件（gitignore）
│   └── yolo11n.pt                  # YOLO11 nano 预训练权重
│
├── routes/                         # 路由层
│   ├── __init__.py                 # 蓝图注册
│   ├── jobs.py                     # 任务 CRUD + 上传
│   ├── review.py                   # 分析 + 审核 + 报告
│   └── validators.py               # 输入校验函数
│
├── services/                       # 服务层（业务逻辑）
│   ├── __init__.py
│   ├── detector.py                 # YOLO 检测器封装
│   └── review_engine.py            # 审核规则引擎
│
├── static/                         # 前端静态资源
│   ├── style.css                   # 全局样式
│   └── app.js                      # 前端交互逻辑
│
├── templates/                      # HTML 模板
│   └── index.html                  # 单页工作台
│
├── tests/                          # 测试
│   ├── __init__.py
│   ├── test_api.py                 # API 接口测试
│   └── test_review.py              # 审核规则测试
│
├── assets/                         # 测试素材（gitignore）
│   ├── valid_image.jpg
│   ├── valid_video.mp4
│   └── empty_file.txt
│
├── outputs/                        # 任务输出（gitignore）
│   └── <job_id>/
│       ├── input/
│       ├── keyframes/
│       ├── result/
│       ├── job.json
│       └── analysis_report.json
│
└── docs/                           # 项目文档
    ├── PRD.md                      # 产品需求文档
    ├── SYSTEM_DESIGN.md            # 系统设计文档（本文件）
    ├── API.md                      # API 接口文档
    ├── TEST_REPORT.md              # 测试报告
    └── BUG_RECORD.md               # Bug 记录
```

---

## 6. 接口设计

详见 `docs/API.md`（由后端工程师维护）。

接口清单：

```text
# 公共
GET    /api/health                   ← 健康检查 + 模型状态
POST   /api/jobs                     ← 上传素材 + 创建任务
GET    /api/jobs                     ← 获取任务列表
GET    /api/jobs/<job_id>            ← 获取单个任务详情
DELETE /api/jobs/<job_id>            ← 删除任务

# 方向 A 专属
POST   /api/jobs/<job_id>/analyze    ← 触发/重新触发审核分析
PATCH  /api/jobs/<job_id>/review     ← 人工修改审核结论
GET    /api/jobs/<job_id>/report     ← 获取审核报告
```

统一规范：
- 成功：`{"ok": true, ...}` + 2xx
- 失败：`{"ok": false, "error": "中文错误信息"}` + 4xx/5xx
- 上传接口先返回 task_id，不阻塞等待推理

---

## 7. 部署说明

### 7.1 环境准备

```powershell
conda activate yolo
cd team_content_review
python -m pip install -r requirements.txt
```

### 7.2 启动服务

```powershell
python app.py --host 127.0.0.1 --port 7880
```

### 7.3 验证启动

```text
浏览器访问: http://127.0.0.1:7880/api/health
预期返回:   {"status":"ok","model_ready":true}
```

### 7.4 基础检查命令

```powershell
python -m py_compile app.py                         # 语法检查
python -m unittest discover -s tests -v             # 单元测试
```

---

## 8. 安全考虑

| 安全点 | 措施 |
|---|---|
| **文件类型** | 扩展名白名单：`jpg, jpeg, png, mp4, avi, mov, webm` |
| **文件大小** | 限制 500MB，前端 + 后端双重校验 |
| **路径遍历** | job_id 严格校验格式 `YYYYMMDD_HHMMSS_8位hex`，禁止包含 `..` 和 `/` |
| **删除安全** | 删除前校验 task 目录在 `outputs/` 下，禁止删除非 outputs 目录 |
| **状态保护** | `queued` 和 `running` 状态的任务禁止删除 |
| **异常不崩溃** | 所有路由 try-catch，异常返回 500 + JSON，不导致进程退出 |
| **大文件** | outputs/ 和 models/ 写入 .gitignore，防止误提交 |

---

## 9. 任务状态机

```text
                    ┌─────────┐
                    │ created │
                    └────┬────┘
                         │ POST /api/jobs/<id>/analyze
                         ▼
                    ┌─────────┐
                    │ queued  │
                    └────┬────┘
                         │ 后台线程开始
                         ▼
                    ┌─────────┐
              ┌─────│ running │─────┐
              │     └─────────┘     │
              │ 异常                │ 成功
              ▼                    ▼
         ┌─────────┐        ┌───────────┐
         │ failed  │        │ completed │
         └────┬────┘        └───────────┘
              │ POST analyze (重试)
              ▼
         ┌─────────┐
         │ queued  │
         └─────────┘
```

---

## 10. 模块依赖关系

```text
app.py
  ├── routes/jobs.py ──────── 处理上传、任务 CRUD
  │     └── routes/validators.py ── 参数校验
  ├── routes/review.py ────── 分析触发、人工审核、报告
  │     ├── services/detector.py ── YOLO 检测
  │     │     └── ultralytics.YOLO
  │     └── services/review_engine.py ── 审核规则
  └── templates/index.html ── 前端页面
        ├── static/style.css
        └── static/app.js
```
