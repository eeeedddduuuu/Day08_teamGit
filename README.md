# ContentGuard — 智能数字媒体内容审核工作台

> Day08 CV 综合项目实战 — 方向 A
> 项目口号：机器初筛，人做决策，全程留档

## 技术栈

- **后端**: Python 3.10+ / Flask
- **检测**: Ultralytics YOLO (yolo11n.pt)
- **视频处理**: OpenCV、FFmpeg
- **前端**: HTML / CSS / JavaScript (Vanilla)

## 快速启动

### 1. 环境准备

```powershell
conda activate yolo
cd team_content_review
```

### 2. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

### 3. 放置模型文件

将 `yolo11n.pt` 放到 `models/` 目录下：

```text
models/
└── yolo11n.pt
```

### 4. 启动服务

```powershell
python app.py --host 127.0.0.1 --port 7880
```

### 5. 验证

浏览器访问健康检查接口：

```text
http://127.0.0.1:7880/api/health
```

返回 `{"status": "ok", "model_ready": true}` 表示启动成功。

## 项目结构

```text
team_content_review/
├── app.py                  # Flask 入口
├── requirements.txt        # Python 依赖
├── models/                 # YOLO 模型文件 (gitignore)
├── assets/                 # 测试素材 (gitignore)
├── outputs/                # 任务输出目录
│   └── <job_id>/
│       ├── input/          # 原始上传文件
│       ├── keyframes/      # 证据帧图片
│       ├── result/         # 分析结果
│       ├── job.json        # 任务状态
│       └── analysis_report.json
├── routes/                 # API 路由
│   ├── jobs.py             # 任务 CRUD
│   ├── review.py           # 审核接口
│   └── validators.py       # 参数校验
├── services/               # 业务逻辑
│   ├── detector.py         # YOLO 检测封装
│   └── review_engine.py    # 审核规则引擎
├── static/                 # 前端静态文件
├── templates/              # HTML 模板
├── tests/                  # 测试用例
└── docs/                   # 项目文档
```

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| POST | `/api/jobs` | 创建任务（上传文件） |
| GET | `/api/jobs` | 任务列表 |
| GET | `/api/jobs/<job_id>` | 任务详情 |
| DELETE | `/api/jobs/<job_id>` | 删除任务 |
| POST | `/api/jobs/<job_id>/analyze` | 触发分析 |
| PATCH | `/api/jobs/<job_id>/review` | 人工审核 |
| GET | `/api/jobs/<job_id>/report` | 获取报告 |

## 常见问题

1. **模型未就绪** — 确保 `models/yolo11n.pt` 存在
2. **端口被占用** — 使用 `--port` 参数更换端口
3. **Python 版本** — 需要 Python 3.10+

## 开发进度

| 模块 | 负责人 | 状态 | 说明 |
|---|---|---|---|
| PRD / 系统设计 / 验收清单 | PO | ✅ 已完成 | `docs/PRD.md` 等4份文档 |
| Flask API 全部8个接口 | 后端 | ✅ 已完成 | `routes/jobs.py` + `routes/review.py` |
| 任务状态机 + 参数校验 | 后端 | ✅ 已完成 | `routes/validators.py` |
| YOLO 检测封装 | CV | ⚠️ 待推送 | `services/detector.py` |
| 审核规则引擎 | CV | ⚠️ 待推送 | `services/review_engine.py` |
| 前端页面（上传/列表/详情） | 前端 | ✅ 已完成 | `static/` + `templates/` |
| 测试用例 + 素材 | 测试 | ⏳ 待开始 | `tests/` |

### Git 分支

| 分支 | 内容 |
|---|---|
| `main` | 保护分支，仅合并 |
| `backend/api` | 后端 API 完整实现 |
| `po/docs` | PO 文档（已合并） |
| `cv/detection` | CV 模块（待推送） |
| `frontend/pages` | 前端页面（待创建分支） |
| `test/cases` | 测试用例（待创建分支） |
