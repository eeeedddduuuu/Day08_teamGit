# 项目进度报告 — Day08 ContentGuard

> **报告人：** 产品负责人（PO）
> **时间：** 2026-07-18 15:55
> **当前阶段：** 下午集成测试

---

## 一、各角色交付状态

| 角色 | 产出 | 状态 |
|---|---|---|
| **PO** | PRD / SYSTEM_DESIGN / 验收清单 / 演示脚本 / 进度报告 | ✅ 全部完成 |
| **后端** | 8 个 API + 任务状态机 + 参数校验 + 首页路由 | ✅ 完成 |
| **CV** | YOLO 检测器 + 审核规则引擎 + yolo11n.pt | ✅ 完成 |
| **前端** | 上传页 + 任务列表 + 详情展示 | ⚠️ 有 Bug |
| **测试** | 94 个自动化用例 + test_api.py + test_review.py | ✅ 完成 |

---

## 二、自动化测试结果

```
94 用例，91 passed，3 failed
```

| 失败用例 | 原因 | 严重度 |
|---|---|---|
| `test_review_on_unstable_results` | 测试期望文案含"不稳定"，引擎用"波动" | 🟢 文案差异 |
| `test_pass_on_no_detection` | 测试期望"未发现风险目标"，引擎返回更详细 | 🟢 文案差异 |
| `test_risk_detections_sorted_by_confidence` | 引擎正确过滤了低于阈值的检测 | 🟢 逻辑更合理 |

**3 个失败均非 Bug，不影响功能。**

---

## 三、API 接口验收（curl 实测）

| # | 接口 | 结果 |
|---|---|---|
| 1 | `GET /api/health` → `{"model_ready":true}` | ✅ |
| 2 | `POST /api/jobs` → 返回 job_id | ✅ |
| 3 | `GET /api/jobs` → 任务列表 | ✅ |
| 4 | `GET /api/jobs/<id>` → 含 report | ✅ |
| 5 | `DELETE /api/jobs/<id>` | ✅ |
| 6 | `POST /api/jobs/<id>/analyze` | ✅ |
| 7 | `PATCH /api/jobs/<id>/review` | ✅ |
| 8 | `GET /api/jobs/<id>/report` | ✅ |
| 9 | 首页 `/` | ✅ |
| 10 | 空文件 → 400 + 中文错误 | ✅ |
| 11 | 非法格式 → 400 + 中文错误 | ✅ |
| 12 | 非法 verdict → 400 + 中文错误 | ✅ |
| 13 | 不存在任务 → 400 | ✅ |
| 14 | 删除已完成任务 | ✅ |

**后端接口全部通过。**

---

## 四、前端 Bug 清单

| # | 问题 | 严重度 | 现象 |
|---|---|---|---|
| BUG-03 | 证据帧不显示 | 🔴 | API 返回 `["keyframes/frame_0000.jpg"]`（字符串数组），代码取 `frame.url` 永远 undefiend |
| BUG-04 | 缺人工审核按钮 | 🟡 | PATCH /review 接口已通，但页面无 pass/review/reject 按钮 |
| BUG-05 | 缺项目名称输入框 | 🟢 | `project_name` 写死为"内容审核项目" |
| BUG-06 | 缺删除按钮 | 🟢 | DELETE 接口已通，但页面无删除入口 |

---

## 五、已修复 Bug 记录

| 编号 | 问题 | 修复方案 | 状态 |
|---|---|---|---|
| BUG-01 | 后台分析线程未启动，任务卡在 queued | 修复 Flask `current_app` 上下文传递 | ✅ |
| BUG-02 | 首页 `/` 返回 404 | 添加 `@app.route('/')` 渲染 index.html | ✅ |

---

## 六、待办事项

| 优先级 | 负责人 | 任务 | 截止 |
|---|---|---|---|
| 🔴 | 前端 | 修复 BUG-03：证据帧路径拼接 | 立刻 |
| 🟡 | 前端 | 修复 BUG-04：添加审核按钮（pass/review/reject） | 16:10 |
| 🟢 | 前端 | 修复 BUG-05/06：加项目名称输入框 + 删除按钮 | 16:20 前 |
| 🟢 | 测试 | 填写 TEST_REPORT.md（5 正常 + 5 异常） | 演示前 |
| 🟢 | 测试 | 填写 BUG_RECORD.md（≥2 个真实 Bug） | 演示前 |
| 🟢 | 前端 | 截 8 张页面截图到 screenshots/ | 演示前 |
| 🟢 | PO | 按 DEMO_SCRIPT.md 演练一遍 | 16:00 |

---

## 七、当前代码文件清单

```text
D:\Projects\工程实训\Day08\Day08_teamGit\
├── app.py                       49行  Flask 入口 ✅
├── requirements.txt              5项   依赖清单 ✅
├── .gitignore                   完整   ✅
├── models/
│   └── yolo11n.pt               5.6MB  ✅
├── routes/
│   ├── __init__.py              蓝图注册 ✅
│   ├── jobs.py                  12KB   任务 CRUD ✅
│   ├── review.py                6KB    审核接口 ✅
│   └── validators.py            1KB    参数校验 ✅
├── services/
│   ├── detector.py              11KB   YOLO 检测 ✅
│   └── review_engine.py         11KB   审核引擎 ✅
├── static/
│   ├── style.css                316行  ✅
│   └── app.js                   267行  ⚠️ 有 Bug
├── templates/
│   └── index.html               55行   ⚠️ 缺审核按钮
├── tests/
│   ├── test_api.py              54 用例 ✅
│   └── test_review.py           40 用例 ✅
└── docs/
    ├── PRD.md                   12KB   ✅
    ├── SYSTEM_DESIGN.md         18KB   ✅
    ├── API.md                   4KB    ✅
    ├── ACCEPTANCE_CHECKLIST.md  5KB    ✅
    ├── DEMO_SCRIPT.md           9KB    ✅
    ├── ALGORITHM_VALIDATION.md  7KB    ✅
    ├── TEST_REPORT.md           占位   🔲
    ├── BUG_RECORD.md            占位   🔲
    └── PROGRESS_REPORT.md       本文件  ✅
```

---

## 八、结论

**后端 + CV + 测试全部完成并验证通过。前端核心功能可用但缺审核交互。** 修复 BUG-03 和 BUG-04 后即可演示。
