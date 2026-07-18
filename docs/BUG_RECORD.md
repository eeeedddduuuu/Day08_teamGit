# Bug 记录

# Bug 记录

**项目**: 方向 A — 智能数字媒体内容审核系统
**记录人**: 测试交付工程师
**分支**: test/cases
**日期**: 2026-07-18

---

## 概览

| 编号 | 问题现象 | 严重程度 | 状态 |
|---|---|---|---|
| BUG-001 | 审核引擎 evaluate() 为 Stub，始终返回 pass | 🔴 严重 | ✅ 已修复 |
| BUG-002 | 后台分析线程异常处理中恢复逻辑缺少自保护 | 🟡 中等 | ✅ 已修复 |

---

## BUG-001

| 字段 | 内容 |
|---|---|
| **编号** | BUG-001 |
| **问题现象** | 上传任意素材并触发分析后，`analysis_report.json` 中的 `auto_verdict` 始终为 `pass`，`auto_verdict_reason` 显示 `"未发现风险目标 — 等待CV算法工程师完成模型集成"`。即使检测结果中包含高置信度（0.85）的 `person` 类别，审核结论也不会变为 `reject` 或 `review`，核心审核功能完全失效。 |
| **严重程度** | 🔴 严重 — 所有内容审核均通过，无法拦截任何风险内容 |
| **影响范围** | `services/review_engine.py` → `evaluate()` 函数 |
| **复现步骤** | 1. 启动 Flask 服务（`python app.py`）<br>2. POST `/api/jobs` 上传一张图片<br>3. POST `/api/jobs/<job_id>/analyze` 触发分析<br>4. GET `/api/jobs/<job_id>/report` 查看报告<br>5. 观察到 `auto_verdict` 恒为 `pass`，与检测结果无关 |
| **原因** | `evaluate()` 函数为 Stub 实现（CV 工程师未完成），函数体直接返回硬编码字典 `{'verdict': 'pass', ...}`，未读取 `detection_result` 参数中的实际检测数据，未执行任何审核规则判断（风险类别筛选、置信度比较、帧间稳定性检查）。 |
| **修复方案** | 实现完整的三级审核规则引擎：<br>1. 遍历所有帧的所有检测结果<br>2. 筛选 `risk_classes` 中的目标类别<br>3. Rule 1：任一检测置信度 ≥ `reject_confidence` → `reject`<br>4. Rule 2：任一检测置信度 ≥ `review_confidence` → `review`；同一类别跨帧置信度波动 > 0.4 → `review`（不稳定）<br>5. Rule 3：无风险检测 → `pass`<br>6. 收集 `risk_detections` 并按置信度降序排列<br>7. 统计 high / medium / low 置信度计数 |
| **修复文件** | `services/review_engine.py` |
| **验证结果** | ✅ 运行 `pytest tests/test_review.py -v`，40 个审核规则测试全部通过。覆盖 reject（6 个）、review（6 个）、pass（5 个）、自定义配置（3 个）、统计（3 个）、边界（4 个）、format_report（8 个）、DEFAULT_SETTINGS（5 个）。提交 b999b03 已验证。 |
| **引入阶段** | 初始开发（CV Stub 代码合入 main 分支） |
| **发现方式** | 测试工程师在编写 `tests/test_review.py` 时发现 `evaluate()` 未实现 |

---

## BUG-002

| 字段 | 内容 |
|---|---|
| **编号** | BUG-002 |
| **问题现象** | 当后台分析线程 `_run_analysis_async()` 发生异常进入 except 块后，若 `load_job(job_path)` 也失败（如 `job.json` 被外部删除或损坏），则整个后台线程静默死亡。任务永远停留在 `running` 状态，既不会转为 `failed`，错误信息也不会落盘。前端轮询永远无法停止。 |
| **严重程度** | 🟡 中等 — 需特定条件触发，但一旦触发会导致任务永久悬挂 |
| **影响范围** | `routes/jobs.py` → `_run_analysis_async()` 函数 except 块 |
| **复现步骤** | 1. 创建任务并 POST `/api/jobs/<job_id>/analyze`（状态变为 `running`）<br>2. 在分析进行中，手动删除 `outputs/<job_id>/job.json`<br>3. 如果此时 `detect()` 或 `evaluate()` 抛异常，进入 except 块<br>4. except 中 `load_job(job_path)` 因文件不存在抛出 `FileNotFoundError`<br>5. 该异常未被捕获，后台线程静默死亡<br>6. 任务永久停留在 `running` 状态，无任何错误记录 |
| **原因** | `_run_analysis_async()` 的 except 块存在防御性编程不足：<br>1. 直接修改 `job['status']` 而不调用 `_transition_status()`，绕过了状态机校验<br>2. 对 `load_job()` / `save_job()` 调用无独立 try-except 保护，一旦恢复逻辑自身失败，整个 except 块崩溃，后台线程静默死亡 |
| **修复方案** | 对 except 块中的恢复逻辑添加内层 try-except：<br>```python<br>except Exception as e:<br>    import traceback<br>    try:<br>        job_path = _job_json_path(job_id)<br>        job = load_job(job_path)<br>        job['status'] = 'failed'<br>        job['completed_at'] = datetime.now().isoformat()<br>        job['error'] = traceback.format_exc()<br>        save_job(job_path, job)<br>    except Exception as recovery_error:<br>        import sys<br>        print(f'CRITICAL: 任务 {job_id} 恢复失败: {recovery_error}', file=sys.stderr)<br>        print(f'原始错误: {e}', file=sys.stderr)<br>``` |
| **修复文件** | `routes/jobs.py`（`_run_analysis_async` except 块） |
| **验证结果** | ✅ `tests/test_api.py::TestAnalyze::test_analyze_handles_detection_error` 通过。该测试模拟 `detect()` 抛出 `RuntimeError("YOLO model crash")`，验证任务正确转为 `failed` 且 `job.error` 包含完整 traceback。直接删除 job.json 再触发异常的极端场景可通过单元测试覆盖。 |
| **引入阶段** | 初始开发（`_run_analysis_async` 初版） |
| **发现方式** | 测试工程师审查 `routes/jobs.py` 异常处理流程时发现 |

---

## 测试环境

| 项目 | 值 |
|---|---|
| Python | 3.9.13 |
| pytest | 8.4.2 |
| Flask | 3.x |
| 操作系统 | Windows 11 家庭中文版 |
| 分支 | test/cases |
| 提交 | 248c42d (tests), b999b03 (assets) |

---

**备注**: 以上 2 个 Bug 均在编写及运行 94 个测试用例的过程中发现并修复。BUG-001 是 Stub 未实现导致的核心功能缺失，BUG-002 是异常处理逻辑的防御性编程不足。修复后全部 94 个测试通过（54 API + 40 Review）。