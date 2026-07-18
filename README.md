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
| PRD / 系统设计 / 验收清单 / 演示脚本 | PO | ✅ | `docs/PRD.md` 等4份文档 |
| Flask API 全部8个接口 | 后端 | ✅ | `routes/jobs.py` + `routes/review.py` |
| 任务状态机 + 参数校验 | 后端 | ✅ | `routes/validators.py` |
| YOLO 检测封装（含检测框绘制） | CV | ✅ | `services/detector.py` |
| 审核规则引擎 | CV | ✅ | `services/review_engine.py` |
| 算法验证文档 | CV | ✅ | `docs/ALGORITHM_VALIDATION.md` |
| 前端页面（上传/列表/详情/审核按钮/删除） | 前端 | ✅ | `static/` + `templates/` |
| 测试用例 (94个, 91 passed) | 测试 | ✅ | `tests/test_api.py` + `tests/test_review.py` |
| 测试报告 + Bug记录(6个) | PO | ✅ | `docs/TEST_REPORT.md` + `docs/BUG_RECORD.md` |

### 测试结果

```
94 tests: 91 passed, 3 failed (文案差异，非功能Bug)
```

### 小组成员

| 角色 | 姓名 | 产出 |
|---|---|---|
| 产品负责人 | | PRD / 系统设计 / 验收清单 / 演示脚本 / 进度报告 |
| 后端工程师 | | Flask API / 任务状态机 / 参数校验 |
| CV 算法工程师 | | YOLO 检测 / 审核规则引擎 / 算法验证 |
| 前端工程师 | | 工作台页面 / 上传 / 审核交互 |
| 测试交付工程师 | | 94 测试用例 / 测试素材 / 打包 |
