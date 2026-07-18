# 验收清单 — ContentGuard

## 使用说明

在项目演示前，逐项检查以下清单。所有项目必须通过（✅）才算满足硬性验收条件。

---

## 一、项目运行

| # | 检查项 | 验证方法 | 状态 |
|---|---|---|---|
| 1 | 已使用 `conda activate yolo` 激活环境 | 终端输入 `conda info --envs` | ⬜ |
| 2 | `requirements.txt` 可以安装所有依赖 | `pip install -r requirements.txt` | ⬜ |
| 3 | README 写明启动命令 | 阅读 README.md | ⬜ |
| 4 | `python app.py` 可以正常启动 | 访问 `http://127.0.0.1:7880` | ⬜ |
| 5 | `/api/health` 返回 `{"status":"ok","model_ready":true}` | 浏览器访问 health 接口 | ⬜ |
| 6 | 模型文件 `models/yolo11n.pt` 存在且路径正确 | 检查文件是否存在 | ⬜ |
| 7 | 测试素材路径正确、可访问 | 检查 `assets/` 目录 | ⬜ |

---

## 二、功能验收

| # | 检查项 | 验证方法 | 状态 |
|---|---|---|---|
| 8 | 可以上传合法 jpg 图片素材 | 用 `assets/valid_image.jpg` 测试 | ⬜ |
| 9 | 可以上传合法 mp4 视频素材 | 用 `assets/valid_video.mp4` 测试 | ⬜ |
| 10 | 上传后返回任务编号（job_id） | 检查 API 响应 | ⬜ |
| 11 | 任务状态能从 `created` → `queued` → `running` → `completed` | 观察任务列表状态变化 | ⬜ |
| 12 | 页面可以展示核心 CV 检测结果 | 选中已完成任务，查看详情 | ⬜ |
| 13 | 页面展示证据帧图片（至少 1 张） | 查看 keyframes 区域 | ⬜ |
| 14 | 页面展示原始素材（图片预览或视频播放） | 查看原始素材区域 | ⬜ |
| 15 | 自动审核结论为 pass / review / reject 之一 | 查看审核结论卡片 | ⬜ |
| 16 | 人工可以修改审核结论（三个选项均可选） | 点击审核按钮，修改结论 | ⬜ |
| 17 | 人工审核结果写回 JSON（刷新后不丢失） | 修改 → 刷新页面 → 重新打开任务 | ⬜ |
| 18 | 审核报告可通过接口获取 | `GET /api/jobs/<id>/report` | ⬜ |
| 19 | 结果文件 `analysis_report.json` 可以重新打开 | 关闭 → 重新点击任务 | ⬜ |
| 20 | 历史任务可以重新打开并继续审核 | 打开已完成任务，执行审核操作 | ⬜ |

---

## 三、异常处理验收

| # | 检查项 | 验证方法 | 状态 |
|---|---|---|---|
| 21 | 上传空文件 → 返回 400 + 中文错误信息 | curl 上传 0 字节文件 | ⬜ |
| 22 | 上传不支持格式（.exe/.zip）→ 返回 400 | curl 上传 .exe 文件 | ⬜ |
| 23 | 上传不填 project_name → 返回 400 | curl 不传 project_name 字段 | ⬜ |
| 24 | 查询不存在的 job_id → 返回 404 | curl `GET /api/jobs/nonexistent` | ⬜ |
| 25 | 删除不存在的任务 → 返回 404 | curl `DELETE /api/jobs/nonexistent` | ⬜ |
| 26 | 删除 `running` 状态的任务 → 返回 409 | 在上传处理中尝试删除 | ⬜ |
| 27 | 模型文件缺失 → 任务 status = `failed` + 错误信息 | 临时重命名 yolo11n.pt，上传文件 | ⬜ |
| 28 | 任务失败后 `job.json` 仍然保留（含 error 字段） | 检查 `outputs/<job_id>/job.json` | ⬜ |
| 29 | 页面在加载中显示加载动画 | 上传视频，观察页面 | ⬜ |
| 30 | 页面在无任务时显示空状态提示 | 清空 outputs/，刷新页面 | ⬜ |
| 31 | 网络断开时页面显示错误提示（不白屏） | 停止 Flask 服务，刷新页面 | ⬜ |

---

## 四、工程交付

| # | 检查项 | 验证方法 | 状态 |
|---|---|---|---|
| 32 | PRD.md 已完成（含 8 个章节） | 检查 `docs/PRD.md` | ⬜ |
| 33 | SYSTEM_DESIGN.md 已完成（含架构图） | 检查 `docs/SYSTEM_DESIGN.md` | ⬜ |
| 34 | API.md 已完成（与实际接口一致） | 用 curl 逐一验证接口 | ⬜ |
| 35 | TEST_REPORT.md 含 ≥ 5 条正常 + 5 条异常测试 | 检查 `docs/TEST_REPORT.md` | ⬜ |
| 36 | BUG_RECORD.md 含 ≥ 2 个真实 Bug 及完整记录 | 检查 `docs/BUG_RECORD.md` | ⬜ |
| 37 | 页面截图已保存（≥ 8 张，覆盖所有状态） | 检查 `screenshots/` 目录 | ⬜ |
| 38 | 成员分工表已整理（每人有明确产出） | 检查 README.md 或独立文件 | ⬜ |
| 39 | 项目目录无 API Key、密码等隐私信息 | `grep -r "password\|api_key\|secret"` | ⬜ |
| 40 | 项目目录无大型缓存文件（`__pycache__` 等） | 检查目录大小 | ⬜ |
| 41 | 交付目录按 `姓氏_方向A_day08/` 格式命名 | 检查目录名 | ⬜ |
| 42 | 8 分钟演示稿已准备 | 检查 `docs/DEMO_SCRIPT.md` | ⬜ |

---

## 五、硬性验收条件（一票否决）

以下任意一项不满足，项目不能评定为"完成"：

- [ ] ❌ 项目不能按照 README 启动
- [ ] ❌ 页面无法完成素材上传和任务创建
- [ ] ❌ 没有可变化的任务状态（created → queued → running → completed/failed）
- [ ] ❌ 没有至少一个真正运行的核心 CV 功能（YOLO 检测）
- [ ] ❌ 结果文件无法打开或无法解释
- [ ] ❌ 失败情况没有明确提示（页面白屏或只显示 500）
- [ ] ❌ 缺少文档（PRD / 系统设计 / API / 测试报告）
- [ ] ❌ 成员无法说明自己的代码和实际工作内容
