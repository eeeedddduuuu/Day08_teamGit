# 项目进度报告 — Day08 ContentGuard

> **报告人：** 产品负责人（PO）
> **时间：** 2026-07-18 15:00
> **当前阶段：** 下午联调

---

## 一、各角色交付状态

| 角色 | 产出 | 代码位置 | 状态 |
|---|---|---|---|
| **PO** | PRD.md / SYSTEM_DESIGN.md / ACCEPTANCE_CHECKLIST.md / DEMO_SCRIPT.md | main ➜ docs/ | ✅ 已完成并合并 |
| **后端** | 8 个 API 接口 + 任务状态机 + 参数校验 | main ➜ routes/ | ⚠️ 代码到位，有 Bug |
| **CV** | YOLO 检测器 + 审核规则引擎 + yolo11n.pt | main ➜ services/ | ✅ 已完成并合并 |
| **前端** | 上传页 / 任务列表 / 详情展示 / 状态覆盖 | main ➜ templates/ + static/ | ✅ 已完成并合并 |
| **测试** | 94 个自动化测试用例 | test/cases 分支 | ✅ 已完成，待最终合并 |

---

## 二、联调验收结果

### ✅ 通过项

| # | 检查项 | 结果 |
|---|---|---|
| 1 | `conda activate yolo` 环境正常 | ✅ 所有依赖已安装 |
| 2 | `requirements.txt` 可安装 | ✅ 全部满足 |
| 3 | Flask 可启动 | ✅ `python app.py --port 7880` |
| 4 | `/api/health` 返回正常 | ✅ `{"status":"ok","model_ready":true,"direction":"A"}` |
| 5 | 模型文件存在 | ✅ `models/yolo11n.pt` (5.6MB) |
| 6 | `POST /api/jobs` 上传成功 | ✅ 返回 job_id + ok:true |
| 7 | `GET /api/jobs` 任务列表正常 | ✅ |
| 8 | `GET /api/jobs/<id>` 任务详情正常 | ✅ |

### ❌ 不通过项（Bug）

| # | 问题 | 严重程度 | 现象 |
|---|---|---|---|
| BUG-01 | 后台分析线程未启动 | 🔴 阻塞 | 创建任务后 status 始终为 `queued`，`started_at` 始终为 null |
| BUG-02 | 首页 `/` 返回 404 | 🟡 中 | Flask 缺少 `@app.route('/')` 来渲染 `index.html` |

### 🔲 待验证项

| # | 检查项 | 依赖 |
|---|---|---|
| 3 | 任务状态流转 created→queued→running→completed | BUG-01 修复 |
| 4 | 审核结论展示（pass/review/reject） | BUG-01 修复 |
| 5 | 证据帧图片展示 | BUG-01 修复 |
| 6 | 人工审核 PATCH 写回 | BUG-01 修复 |
| 7 | 异常处理（空文件、非法格式、模型缺失） | BUG-01 修复 |
| 8 | 历史任务重新打开 | BUG-01 修复 |
| 9 | 删除保护（running/queued→409） | 后续验证 |
| 10 | 页面截图（8 种状态） | BUG-02 修复 |

---

## 三、代码文件清单

```text
D:\Projects\工程实训\Day08\Day08_teamGit\
├── app.py                       ✅ Flask 入口
├── requirements.txt             ✅ 依赖清单
├── .gitignore                   ✅
├── models/
│   └── yolo11n.pt               ✅ 5.6MB
├── routes/
│   ├── __init__.py              ✅ 蓝图注册
│   ├── jobs.py                  ✅ 任务 CRUD（12KB）
│   ├── review.py                ✅ 审核接口（6KB）
│   └── validators.py            ✅ 参数校验（1KB）
├── services/
│   ├── __init__.py              ✅
│   ├── detector.py              ✅ YOLO 检测（11KB）
│   └── review_engine.py         ✅ 审核引擎（11KB）
├── static/
│   ├── style.css                ✅
│   └── app.js                   ✅
├── templates/
│   └── index.html               ✅
├── tests/
│   ├── test_api.py              ✅ 54 用例
│   └── test_review.py           ✅ 40 用例
└── docs/
    ├── PRD.md                   ✅ 12KB
    ├── SYSTEM_DESIGN.md         ✅ 18KB
    ├── API.md                   ✅ 4KB
    ├── ACCEPTANCE_CHECKLIST.md  ✅ 5KB
    ├── DEMO_SCRIPT.md           ✅ 9KB
    ├── ALGORITHM_VALIDATION.md  ✅ 7KB
    ├── TEST_REPORT.md           🔲 待补充
    └── BUG_RECORD.md            🔲 待补充
```

---

## 四、下一步行动

| 优先级 | 负责人 | 行动 | 截止 |
|---|---|---|---|
| 🔴 P0 | 后端 | 修复 BUG-01：后台分析线程启动逻辑 | 立刻 |
| 🔴 P0 | 后端 | 修复 BUG-02：添加 `@app.route('/')` 渲染首页 | 立刻 |
| 🟡 P1 | 全员 | 第二轮联调：上传 → 分析 → 展示 → 审核 全链路 | BUG-01 修复后 |
| 🟡 P1 | 测试 | 解除 mock，做真实接口回归测试 | 全链路通过后 |
| 🟡 P1 | 前端 | 页面截图（≥8 张，覆盖所有状态） | BUG-02 修复后 |
| 🟢 P2 | 测试 | 填写 TEST_REPORT.md 和 BUG_RECORD.md | 15:30 前 |
| 🟢 P2 | PO | 按 DEMO_SCRIPT.md 演练一遍 | 16:00 前 |
| 🟢 P2 | 全员 | 最终交付打包 | 16:20 |

---

## 五、风险提示

1. **后台线程 Bug** 是当前唯一阻塞项，如果 15:30 前未修复，考虑降级方案：手动在 route 里同步调用 detect()，至少保证演示链路完整
2. 首页 404 不阻塞 API 验证，但影响页面演示——需在演示前修好
3. 测试分支 `test/cases` 尚未合并到 main，等 Bug 修完后一并合并做最终回归
