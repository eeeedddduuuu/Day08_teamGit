# Bug 记录 — ContentGuard

> **记录日期：** 2026-07-18

---

| 编号 | 问题现象 | 复现步骤 | 原因 | 修复方案 | 验证结果 |
|---|---|---|---|---|---|
| BUG-001 | 任务创建后始终卡在 queued 状态，从不进入 running | 1. 上传任意图片 2. 查询任务状态 3. 观察到 started_at 始终为 null | 后台线程中使用了 `current_app`，但 Flask 在子线程中无法获取应用上下文 | 将 `outputs_dir` 作为参数显式传入 `_run_analysis_async()`，避免在线程中使用 `current_app` | ✅ 任务正常流转 created→queued→running→completed |
| BUG-002 | 浏览器访问 `http://127.0.0.1:7880/` 返回 404 | 1. 启动 Flask 2. 浏览器访问首页 | `app.py` 只注册了 API 蓝图，缺少根路由 `/` | 在 `app.py` 中添加 `@app.route('/')` 路由，返回 `render_template('index.html')` | ✅ 首页正常渲染 |
| BUG-003 | 证据帧图片不显示 | 1. 上传图片 2. 任务完成后查看详情 3. 证据帧区域无图片 | 前端代码 `frame.url` 取值方式错误：API 返回字符串数组 `["keyframes/frame_0000.jpg"]`，代码期望对象数组 `[{url, label}]` | 1. 前端兼容字符串和对象两种格式 2. 后端添加 `/outputs/<job_id>/<path>` 静态文件路由 3. 前端路径拼接 `/outputs/<job_id>/` 前缀 | ✅ 证据帧正常显示 |
| BUG-004 | 点击审核按钮提示"无效的审核结论: None" | 1. 上传图片完成审核 2. 点击通过/待复核/不通过按钮 | 前端 `submitReview()` 使用的字段名为 `manual_review`，但后端接口期望的字段名为 `verdict` | 将前端请求体中的 `manual_review` 改为 `verdict`，并添加 `reviewer` 和 `notes` 字段 | ✅ 审核按钮正常工作 |
| BUG-005 | 证据帧保存的是原图，没有检测框标注 | 1. 上传包含检测目标的图片 2. 查看证据帧 | `detector.py` 中 `cv2.imwrite()` 直接保存原始帧，未绘制检测边界框 | 在 `services/detector.py` 中添加 `_draw_boxes()` 函数，在保存证据帧前绘制 YOLO 检测框和标签 | ✅ 证据帧显示带标注框的图片 |
| BUG-006 | 前端缺少项目名称输入框和删除按钮 | 1. 打开首页 2. 观察上传区域和任务详情 | 前端 v1 版本功能不完整 | 添加项目名称输入框、审核按钮组（pass/review/reject）、删除按钮（含确认弹窗） | ✅ 功能齐全 |
