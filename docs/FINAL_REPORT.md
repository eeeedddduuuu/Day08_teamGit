# ContentGuard 项目总结报告

> **项目名称：** ContentGuard — 智能数字媒体内容审核工作台
> **方向：** 方向 A（智能数字媒体内容审核系统）
> **小组：** 5 人协作
> **日期：** 2026-07-18
> **仓库：** https://github.com/eeeedddduuuu/Day08_teamGit

---

## 一、项目概述

ContentGuard 是一个面向游戏宣传素材的轻量级 CV 工作台，实现"YOLO 机器初筛 + 人工复核 + 结果留档"的完整内容审核闭环。

**技术栈：** Python / Flask / HTML / CSS / JavaScript / OpenCV / Ultralytics YOLO11n / FFmpeg

**核心流程：**

```text
上传素材 → 创建任务 → YOLO 自动检测 → 规则引擎判定
→ 展示审核结论与证据帧 → 人工修改结论 → 输出审核报告
```

---

## 二、小组成员与分工

| 角色 | 姓名 | 主要产出 |
|---|---|---|
| **产品负责人** | 罗欢 | PRD.md / SYSTEM_DESIGN.md / ACCEPTANCE_CHECKLIST.md / DEMO_SCRIPT.md / 进度报告 / 最终报告 |
| **后端工程师** | 郎妤菲 | Flask API 8 个接口 / 任务状态机 / 参数校验 / 文件存储 / 异常处理 |
| **CV 算法工程师** | 吴淑怡 | YOLO 检测封装 / 审核规则引擎 / 证据帧保存 / 算法验证文档 |
| **前端工程师** | 刘芮溪 | 工作台页面 / 上传交互 / 任务列表 / 结果展示 / 审核 UI / 灯箱 |
| **测试交付工程师** | 吴宇琦 | 94 个自动化测试用例 / 测试素材 / 测试报告 / Bug 记录 |

---

## 三、功能实现对照（任务书 4.2 节）

| # | 任务书要求 | 实现情况 |
|---|---|---|
| 1 | 支持上传图片或视频素材 | ✅ 支持 jpg/jpeg/png/mp4/avi/mov/webm |
| 2 | YOLO 对图片或采样帧进行目标检测 | ✅ 图片直接检测，视频按秒采样 |
| 3 | 记录检测类别、置信度和边界框坐标 | ✅ 完整记录在 analysis_report.json |
| 4 | 根据目标类别和审核规则进行内容筛选 | ✅ 三级判定：通过 / 待复核 / 不通过 |
| 5 | 输出三种审核结果 | ✅ 全部实现并验证 |
| 6 | 保存至少一张审核证据帧 | ✅ 保存置信度最高的帧，含 YOLO 检测框标注 |
| 7 | 页面展示原始素材、检测结果、审核结论和证据图片 | ✅ 分块卡片展示，支持灯箱放大 |
| 8 | 支持人工修改审核结论并写回 JSON | ✅ 内联表单 + PATCH 接口 |
| 9 | 输出可重新读取的审核报告 | ✅ GET /report + analysis_report.json |
| 10 | 异常输入给出明确提示 | ✅ 空文件/非法格式/模型缺失均有中文提示 |

---

## 四、API 接口清单（任务书 5.4 节）

| 方法 | 路径 | 说明 | 测试结果 |
|---|---|---|---|
| GET | `/api/health` | 健康检查 + 模型状态 | ✅ |
| POST | `/api/jobs` | 创建任务（上传文件） | ✅ |
| GET | `/api/jobs` | 任务列表 | ✅ |
| GET | `/api/jobs/<id>` | 任务详情（含报告） | ✅ |
| DELETE | `/api/jobs/<id>` | 删除任务（含状态保护） | ✅ |
| POST | `/api/jobs/<id>/analyze` | 触发分析 | ✅ |
| PATCH | `/api/jobs/<id>/review` | 人工审核 | ✅ |
| GET | `/api/jobs/<id>/report` | 获取审核报告 | ✅ |

**接口规范：** 成功返回 `{"ok": true}` + 2xx，失败返回 `{"ok": false, "error": "中文信息"}` + 4xx/5xx

---

## 五、任务状态机（任务书 5.1 节）

```text
created → queued → running → completed
                            └→ failed → queued (重试)
```

| 状态 | 前端显示 | 验证结果 |
|---|---|---|
| created | 灰色"已创建" | ✅ |
| queued | 黄色"排队中" | ✅ |
| running | 蓝色"处理中" + 进度条 | ✅ |
| completed | 绿色"已完成" | ✅ |
| failed | 红色"失败" + 错误信息 | ✅ |

---

## 六、审核规则（任务书 4.3 节）

```json
{
  "risk_classes": ["person"],
  "reject_confidence": 0.60,
  "review_confidence": 0.35,
  "min_evidence_frames": 1
}
```

**判定逻辑：**
- 高风险类别 + 置信度 ≥ 0.60 → **不通过**
- 置信度 0.35~0.60 或帧间波动 > 0.4 → **待复核**
- 无风险目标 + 处理正常 → **通过**

---

## 七、测试结果

| 指标 | 数值 |
|---|---|
| 自动化用例总数 | 94（54 API + 40 审核规则） |
| 通过 | 91 |
| 失败 | 3（均为文案差异，非功能 Bug） |
| 通过率 | **96.8%** |
| 正常测试记录 | 10 条 |
| 异常测试记录 | 5 条 |
| 真实 Bug 及修复 | 6 个 |

### 已修复 Bug

| 编号 | 问题 | 修复方案 |
|---|---|---|
| BUG-001 | 任务卡在 queued（后台线程上下文丢失） | 显式传入 outputs_dir 参数 |
| BUG-002 | 首页 / 返回 404 | 添加 @app.route('/') 路由 |
| BUG-003 | 证据帧不显示（frame.url 取不到） | 兼容字符串/对象格式 + 添加 /outputs 路由 |
| BUG-004 | 审核按钮字段名不匹配 | manual_review → verdict |
| BUG-005 | 证据帧无检测框标注 | 添加 _draw_boxes() 函数 |
| BUG-006 | 缺项目名称输入 + 删除按钮 | 前端全面完善 |

---

## 八、目录结构（任务书 5.3 节）

```text
team_content_review/
├── app.py                       ✅ Flask 入口（含 Range 支持）
├── requirements.txt             ✅ 5 项依赖
├── .gitignore                   ✅
├── README.md                    ✅ 含启动说明 + 成员表 + API 表
├── models/
│   └── yolo11n.pt               ✅ 5.4MB
├── assets/                      ✅ 7 个测试素材
├── outputs/<job_id>/            ✅ 运行时生成
│   ├── input/                   ✅ 原始文件
│   ├── keyframes/               ✅ 证据帧（含检测框）
│   ├── result/                  ✅ 中间结果
│   ├── job.json                 ✅ 任务状态
│   └── analysis_report.json     ✅ 审核报告
├── routes/
│   ├── __init__.py              ✅ 蓝图注册
│   ├── jobs.py                  ✅ 任务 CRUD
│   ├── review.py                ✅ 审核接口
│   └── validators.py            ✅ 参数校验
├── services/
│   ├── detector.py              ✅ YOLO 检测 + 框绘制
│   └── review_engine.py         ✅ 审核规则引擎
├── static/
│   ├── style.css                ✅ 完整样式系统
│   └── app.js                   ✅ 完整交互逻辑
├── templates/
│   └── index.html               ✅ 左右布局工作台
├── tests/
│   ├── test_api.py              ✅ 54 用例
│   └── test_review.py           ✅ 40 用例
├── screenshots/                 ✅ 页面截图目录
└── docs/
    ├── PRD.md                   ✅ 产品需求文档
    ├── SYSTEM_DESIGN.md         ✅ 系统架构设计
    ├── API.md                   ✅ 接口文档
    ├── ACCEPTANCE_CHECKLIST.md  ✅ 42 条验收清单
    ├── DEMO_SCRIPT.md           ✅ 8 分钟演示脚本
    ├── ALGORITHM_VALIDATION.md  ✅ 算法验证记录
    ├── TEST_REPORT.md           ✅ 测试报告
    ├── BUG_RECORD.md            ✅ Bug 记录
    ├── PROGRESS_REPORT.md       ✅ 进度报告
    └── FINAL_REPORT.md          ✅ 本总结报告
```

---

## 九、验收清单（任务书 9 & 11 节）

### 硬性验收条件

| 条件 | 结果 |
|---|---|
| 项目能按 README 启动 | ✅ |
| 页面可完成素材上传和任务创建 | ✅ |
| 有可变化的任务状态 | ✅ created→queued→running→completed/failed |
| 有至少一个真正运行的核心 CV 功能 | ✅ YOLO 检测 + 审核判定 |
| 结果文件可打开可解释 | ✅ analysis_report.json |
| 失败情况有明确提示 | ✅ 中文错误信息全覆盖 |
| 文档/截图/测试记录完整 | ✅ |
| 成员能说明自己的代码和工作内容 | ✅ |

### 提交前检查清单

- [x] conda activate yolo 可用
- [x] requirements.txt 可安装
- [x] README 含启动命令
- [x] 页面可正常打开
- [x] /api/health 返回正常
- [x] 模型文件路径正确
- [x] 测试素材路径正确
- [x] 可上传合法素材
- [x] 可返回任务编号
- [x] 任务状态能流转
- [x] 页面展示核心 CV 结果
- [x] 结果文件可重新打开
- [x] 异常输入有明确提示
- [x] 历史任务可重新打开
- [x] PRD / 系统架构 / API / 测试报告 / Bug 记录已全部完成
- [x] 成员分工和个人产出已整理
- [x] 无 API Key / 密码泄露
- [x] 无大型缓存文件

---

## 十、Git 协作记录

```text
main 分支提交历程（关键节点）：
595439f  init: project scaffold
bd84ce4  Merge PR#1 — PO 文档合入
ae59a5e  添加前端页面
4cf8c76  merge: test suite (94 cases)
e537df8  feat: integrate CV detection module
fc2b3a5  fix: homepage 404 route
c3bb073  fix: background thread crash (BUG-01)
639d536  fix: frontend review buttons + evidence frames
b2a1fc9  fix: evidence frame bounding box drawing
117f7b5  feat: frontend overhaul (toast/search/lightbox)
9e8a8f1  fix: HTTP Range support for video playback
4c3069f  feat: UI redesign (sidebar layout/cards/animations)
```

---

## 十一、总结

本项目在 1 天内完成了从需求分析、系统设计、前后端开发、CV 算法集成到测试交付的完整工程闭环。5 名成员按角色分工并行开发，通过 Git 分支协作，最终交付了一个可运行、可演示的智能内容审核工作台。

**核心亮点：**
- 8 个 API 接口全部实现并验证
- 94 个自动化测试用例，通过率 96.8%
- 完整的前端交互（上传/列表/详情/审核/删除/搜索/灯箱）
- 6 个真实 Bug 发现并修复
- 全套工程文档（PRD / 系统设计 / API / 测试 / Bug / 验收 / 演示）
- 支持图片和视频两种素材格式
- 证据帧含 YOLO 检测框标注
