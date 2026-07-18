 # 测试报告

  > **项目**: 方向 A — 智能数字媒体内容审核系统
  > **测试工程师**: Test Agent
  > **测试日期**: 2026-07-18
  > **测试环境**: Python 3.9.13 · pytest 8.4.2 · Flask 测试客户端
  > **提交**: 248c42d · 分支 test/cases

  ---

  ## 测试概览

  | 指标 | 数值 |
  |---|---|
  | 测试用例总数 | 94 |
  | 通过 | 94 |
  | 失败 | 0 |
  | 阻塞 | 0 |
  | 通过率 | 100% |

  | 测试文件 | 用例数 | 通过 | 失败 |
  |---|---|---|---|
  | `tests/test_api.py` | 54 | 54 | 0 |
  | `tests/test_review.py` | 40 | 40 | 0 |

  ---

  ## 正常测试记录（≥ 5 条）

  | 编号 | 测试项 | 测试类 | 输入 | 预期结果 | 实际结果 | 状态 |
  |---|---|---|---|---|---|---|
  | TC-01 | 上传合法 JPEG 图片 | TestCreateJob | `test.jpg` + `project_name` | 201 + `job_id` | 返回 201，`ok: true`，含
  `job_id` | ✅ |
  | TC-02 | 上传合法 MP4 视频 | TestCreateJob | `test_video.mp4` + `project_name` | 201 + `job_id` | 返回 201，`ok:
  true`，含 `job_id` | ✅ |
  | TC-03 | 任务列表按创建时间倒序 | TestGetJobs | 3 个已创建的 job 目录 | 列表长度 3，按 `created_at` 降序 | 返回 3
  条，排序正确 | ✅ |
  | TC-04 | 获取单个任务详情 | TestGetJobs | 存在的 `job_id` | 200 + 完整 `job` 对象 | 返回
  `job_id`、`project_name`、`status` 等全部字段 | ✅ |
  | TC-05 | 人工审核 — 通过 | TestReview | `verdict: "pass"` + 已完成任务 | 200 + `manual_review.verdict = "pass"` |
  审核结果写入 `analysis_report.json` | ✅ |
  | TC-06 | 人工审核 — 拒绝 | TestReview | `verdict: "reject"` + 审核人/备注 | 200 + 完整人工审核信息 |
  `reviewer`、`notes`、`reviewed_at` 均持久化 | ✅ |
  | TC-07 | 获取分析报告 | TestReport | 存在报告的任务 `job_id` | 200 + 报告 JSON | 返回 `auto_verdict`、`statistics`
  等完整报告 | ✅ |
  | TC-08 | 高置信度风险类 → 拒绝 | TestReviewRules | `person` 置信度 0.85 | `verdict = "reject"` | 返回 `reject`，1
  条高风险检测 | ✅ |
  | TC-09 | 中等置信度 → 待复核 | TestReviewRules | `person` 置信度 0.45 | `verdict = "review"` | 返回 `review`，1
  条中等置信度 | ✅ |
  | TC-10 | 无检测 → 通过 | TestReviewRules | 空检测帧 | `verdict = "pass"` | 返回 `pass`，无风险检测 | ✅ |
  | TC-11 | 完整生命周期 | TestJobLifecycle | 创建 → 列表 → 详情 → 审核 → 删除 | 每一步返回 200/201 |
  全链路通过，最终目录已清理 | ✅ |
  | TC-12 | 分析后任务自动完成 | TestCreateJob | 上传合法图片（mock 线程同步） | `status = "completed"` | job.json 中
  status 为 completed | ✅ |

  ---

  ## 异常测试记录（≥ 5 条）

  | 编号 | 测试项 | 测试类 | 输入 | 预期结果 | 实际结果 | 状态 |
  |---|---|---|---|---|---|---|
  | TC-13 | 上传空文件 | TestCreateJob | 0 字节文件 | 400 + `"文件为空"` | 400，`error` 含 "空" | ✅ |
  | TC-14 | 上传不支持格式 | TestCreateJob | `test.xyz` | 400 + `"不支持的文件格式"` | 400，`error` 含 "不支持" | ✅ |
  | TC-15 | 上传 .txt 文件 | TestCreateJob | `document.txt` | 400（不在白名单） | 400，`ok: false` | ✅ |
  | TC-16 | 不传 file 字段 | TestCreateJob | 仅 `project_name` | 400 + `"缺少上传文件"` | 400，错误信息明确 | ✅ |
  | TC-17 | 缺少 project_name | TestCreateJob | 仅 `file` | 400 + `"缺少项目名称"` | 400，错误信息明确 | ✅ |
  | TC-18 | 空白 project_name | TestCreateJob | `project_name: "   "` | 400 | 400，`ok: false` | ✅ |
  | TC-19 | 获取不存在的任务 | TestGetJobs | 不存在的 `job_id` | 404 + `"任务不存在"` | 404，错误信息明确 | ✅ |
  | TC-20 | 非法 job_id 格式 | TestGetJobs | `"not-a-valid-job-id"` | 400 | 400，格式校验生效 | ✅ |
  | TC-21 | SQL 注入尝试 | TestGetJobs | `job_id` 含 `' OR '1'='1` | 400 | 400，正则校验阻止 | ✅ |
  | TC-22 | 路径穿透尝试 | TestGetJobs | `..%2F..%2Fetc%2Fpasswd` | 400 或 404 | 400/404，安全阻断 | ✅ |
  | TC-23 | 删除不存在的任务 | TestDeleteJob | 不存在的 `job_id` | 404 | 404，错误信息明确 | ✅ |
  | TC-24 | 删除 running 状态任务 | TestDeleteJob | `status = "running"` | 409 + `"无法删除"` | 409，目录未被删除 | ✅ |
  | TC-25 | 删除 queued 状态任务 | TestDeleteJob | `status = "queued"` | 409 + `"无法删除"` | 409，目录未被删除 | ✅ |
  | TC-26 | 分析不存在的任务 | TestAnalyze | 不存在的 `job_id` | 404 | 404，错误信息明确 | ✅ |
  | TC-27 | 分析时输入文件缺失 | TestAnalyze | 无 `input/` 目录的任务 | 400 + `"不存在"` | 400，错误信息明确 | ✅ |
  | TC-28 | 检测异常 → 任务失败 | TestAnalyze | `detect()` 抛出 RuntimeError | status 变为 `failed` | `job.json` 中
  status=failed，含 traceback | ✅ |
  | TC-29 | 非法审核结论 | TestReview | `verdict: "approved"` | 400 + `"无效"` | 400，错误信息含 "无效" | ✅ |
  | TC-30 | 审核未完成的任务 | TestReview | `status = "running"` | 409 | 409，拒绝操作 | ✅ |
  | TC-31 | 审核 created 状态任务 | TestReview | `status = "created"` | 409 | 409，拒绝操作 | ✅ |
  | TC-32 | 审核无报告的任务 | TestReview | 无 `analysis_report.json` | 404 | 404，错误信息明确 | ✅ |
  | TC-33 | 获取不存在的报告 | TestReport | 任务存在但无报告 | 404 | 404，错误信息明确 | ✅ |
  | TC-34 | 检测缺少 class 字段 | TestReviewRules | 检测结果无 `class` 键 | `verdict = "pass"` | 空 class 不在
  risk_classes → pass | ✅ |
  | TC-35 | 检测缺少 confidence 字段 | TestReviewRules | 检测结果无 `confidence` 键 | `verdict = "pass"` | confidence
  默认 0.0 < 0.35 → pass | ✅ |

  ---

  ## 状态覆盖测试

  | 状态 | 是否测试 | 覆盖方式 |
  |---|---|---|
  | `created` | ✅ | `test_cannot_delete_created_job` — created 状态可被删除 |
  | `queued` | ✅ | `test_cannot_delete_queued_job` — queued 状态禁止删除（409） |
  | `running` | ✅ | `test_cannot_delete_running_job` — running 状态禁止删除（409）；`test_review_job_not_completed` —
  running 状态拒绝审核（409） |
  | `completed` | ✅ | 多数 API 测试基于 completed 状态：审核、报告获取、删除 |
  | `failed` | ✅ | `test_delete_failed_job` — failed 状态可删除；`test_analyze_handles_detection_error` —
  异常后自动转为 failed |

  ---

  ## 审核规则覆盖

  | 规则 | 置信度范围 | 预期裁决 | 测试覆盖 |
  |---|---|---|---|
  | 高风险类别 + 高置信度 | `>= 0.60` | `reject` | ✅ `test_reject_on_high_confidence_risk_class` 等 6 个测试 |
  | 帧间波动 > 0.4 | 任意 | `review`（不稳定） | ✅ `test_review_on_unstable_results` |
  | 高风险类别 + 中等置信度 | `0.35 ~ 0.60` | `review` | ✅ `test_review_on_medium_confidence` 等 4 个测试 |
  | 低置信度 | `< 0.35` | `pass` | ✅ `test_pass_on_low_confidence` |
  | 无风险类别检测 | — | `pass` | ✅ `test_pass_on_no_detection`、`test_pass_on_non_risk_class` |
  | 自定义规则配置 | 任意 | 按配置 | ✅ `test_custom_risk_classes`、`test_custom_all_thresholds` |

  ---

  ## Mock 说明

  所有测试使用 `unittest.mock.patch` 隔离外部依赖，确保可在纯 Python 环境运行：

  | 外部依赖 | Mock 方式 | 原因 |
  |---|---|---|
  | `services.detector.detect()` | `patch` 返回受控检测结果 | 无需 YOLO 模型文件 |
  | `services.review_engine.evaluate()` | `patch` 返回受控裁决（仅 API 测试） | 隔离审核逻辑，API 与 Review 测试独立 |
  | `services.review_engine.format_report()` | `patch` 返回受控报告 | 隔离报告格式化 |
  | `threading.Thread` | 替换为同步执行 | 消除竞态条件，确保测试确定性 |
  | 文件系统 | `tempfile.mkdtemp` 临时目录 | 测试隔离，自动清理 |

  > **注意**: `tests/test_review.py` 中的 `evaluate()` 和 `format_report()` 使用真实实现（非
  mock），直接验证审核规则逻辑。

  ---

  ## 运行方式

  ```powershell
  # 安装测试依赖
  pip install pytest>=7.0

  # 运行全部测试
  python -m pytest tests/ -v

  # 仅运行 API 测试
  python -m pytest tests/test_api.py -v

  # 仅运行审核逻辑测试
  python -m pytest tests/test_review.py -v

  # 导出测试结果
  python -m pytest tests/ -v --tb=short > test_output.txt