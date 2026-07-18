// ============================================================
// 状态
// ============================================================
let currentJobId = null;

// ============================================================
// DOM 引用
// ============================================================
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const uploadArea = document.getElementById('uploadArea');
const previewArea = document.getElementById('previewArea');
const uploadStatus = document.getElementById('uploadStatus');
const taskList = document.getElementById('taskList');
const detailSection = document.getElementById('detailSection');
const taskDetail = document.getElementById('taskDetail');
const evidenceArea = document.getElementById('evidenceArea');

// ============================================================
// 事件绑定
// ============================================================
uploadBtn.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('click', () => fileInput.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#4f46e5';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = '#cbd5e1';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#cbd5e1';
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        uploadFile();
    }
});

fileInput.addEventListener('change', uploadFile);

// ============================================================
// 上传功能（含预览）
// ============================================================
async function uploadFile() {
    const file = fileInput.files[0];
    if (!file) {
        showStatus('请先选择文件', 'warning');
        return;
    }

    // 获取项目名称
    const projectNameInput = document.getElementById('projectNameInput');
    const projectName = projectNameInput ? projectNameInput.value.trim() || '内容审核项目' : '内容审核项目';

    showPreview(file);
    showStatus('⏳ 上传中...', 'loading');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_name', projectName);

    try {
        const res = await fetch('/api/jobs', {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        if (data.ok) {
            showStatus('✅ 上传成功！任务 ID：' + data.job_id, 'success');
            fileInput.value = '';
            if (projectNameInput) projectNameInput.value = '';
            fetchTasks();
        } else {
            showStatus('❌ 上传失败：' + (data.error || '未知错误'), 'error');
        }
    } catch (err) {
        showStatus('❌ 网络错误，请检查后端服务是否启动', 'error');
        console.error(err);
    }
}

// -------- 预览 --------
function showPreview(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        if (file.type.startsWith('image/')) {
            previewArea.innerHTML = `<img src="${e.target.result}" alt="预览">`;
        } else if (file.type.startsWith('video/')) {
            previewArea.innerHTML = `<video src="${e.target.result}" controls></video>`;
        } else {
            previewArea.innerHTML = `<span style="color:#64748b;">📄 ${file.name}</span>`;
        }
    };
    reader.readAsDataURL(file);
}

// ============================================================
// 获取任务列表
// ============================================================
async function fetchTasks() {
    try {
        const res = await fetch('/api/jobs');
        const data = await res.json();

        if (data.ok && data.jobs) {
            renderTaskList(data.jobs);
        } else {
            taskList.innerHTML = '<p class="empty-tip">暂无任务</p>';
        }
    } catch (err) {
        taskList.innerHTML = '<p class="empty-tip">⚠️ 无法连接后端服务</p>';
        console.error(err);
    }
}

// ============================================================
// 渲染任务列表
// ============================================================
function renderTaskList(jobs) {
    if (!jobs || jobs.length === 0) {
        taskList.innerHTML = '<p class="empty-tip">暂无任务，上传一个素材开始吧</p>';
        return;
    }

    let html = '';
    for (const job of jobs) {
        const statusClass = 'status-' + job.status;
        const statusText = {
            'created': '已创建',
            'queued': '排队中',
            'running': '处理中',
            'completed': '已完成',
            'failed': '失败'
        }[job.status] || job.status;

        let progressHtml = '';
        if (job.status === 'running') {
            progressHtml = `
                <div class="progress-wrapper">
                    <div class="fill"></div>
                </div>
            `;
        }

        html += `
            <div class="task-card" onclick="showDetail('${job.job_id}')">
                <div class="task-left">
                    <span class="task-name">${job.asset_name || '未命名'}</span>
                    ${progressHtml}
                </div>
                <div class="task-meta">
                    <span class="status-badge ${statusClass}">${statusText}</span>
                    <span class="task-time">${job.created_at || ''}</span>
                </div>
            </div>
        `;
    }
    taskList.innerHTML = html;
}

// ============================================================
// 删除任务
// ============================================================
async function deleteJob(jobId) {
    if (!confirm('确定要删除任务 ' + jobId + ' 吗？')) return;

    try {
        const res = await fetch('/api/jobs/' + jobId, {
            method: 'DELETE'
        });
        const data = await res.json();

        if (data.ok) {
            alert('✅ 任务已删除');
            detailSection.style.display = 'none';
            fetchTasks();
        } else {
            alert('❌ 删除失败：' + (data.error || '未知错误'));
        }
    } catch (err) {
        alert('❌ 删除失败，请检查网络');
        console.error(err);
    }
}

// ============================================================
// 人工审核
// ============================================================
async function submitReview(jobId, verdict) {
    const reason = prompt('请输入审核备注（可选）：');
    if (reason === null) return;

    try {
        const res = await fetch('/api/jobs/' + jobId + '/review', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                verdict: verdict,
                reviewer: 'PO',
                notes: reason || ''
            })
        });
        const data = await res.json();

        if (data.ok) {
            alert('✅ 审核结论已更新为：' + verdict);
            showDetail(jobId);
        } else {
            alert('❌ 审核提交失败：' + (data.error || '未知错误'));
        }
    } catch (err) {
        alert('❌ 审核提交失败，请检查网络');
        console.error(err);
    }
}

// ============================================================
// 显示任务详情
// ============================================================
async function showDetail(jobId) {
    try {
        const verdictMap = {
            'reject': '不通过',
            'review': '待复核',
            'pass': '通过'
        };

        const verdictColor = {
            'reject': '#dc2626',
            'review': '#d97706',
            'pass': '#16a34a'
        };

        const res = await fetch('/api/jobs/' + jobId);
        const data = await res.json();

        if (!data.ok) {
            alert('获取详情失败：' + (data.error || ''));
            return;
        }

        const job = data.job;
        const report = data.report;
        currentJobId = jobId;
        detailSection.style.display = 'block';

        const statusText = {
            'created': '已创建',
            'queued': '排队中',
            'running': '处理中',
            'completed': '已完成',
            'failed': '失败'
        }[job.status] || job.status;

        // 审核结论
        let verdictDisplay = '待处理';
        let verdictColorStyle = '#64748b';
        if (report) {
            const finalVerdict = report.manual_review || report.auto_verdict;
            if (finalVerdict && verdictMap[finalVerdict]) {
                verdictDisplay = verdictMap[finalVerdict];
                verdictColorStyle = verdictColor[finalVerdict] || '#64748b';
            }
        }

        // 审核按钮（只有 completed 状态才显示）
        let reviewButtons = '';
        if (job.status === 'completed') {
            reviewButtons = `
                <div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap;">
                    <button onclick="submitReview('${job.job_id}','pass')" style="background:#16a34a;color:#fff;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">✅ 通过</button>
                    <button onclick="submitReview('${job.job_id}','review')" style="background:#d97706;color:#fff;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">⏳ 待复核</button>
                    <button onclick="submitReview('${job.job_id}','reject')" style="background:#dc2626;color:#fff;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">❌ 不通过</button>
                    <button onclick="deleteJob('${job.job_id}')" style="background:#6b7280;color:#fff;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">🗑️ 删除任务</button>
                </div>
            `;
        }

        taskDetail.innerHTML = `
            <div class="detail-content">
                <div><div class="label">任务 ID</div><div class="value">${job.job_id}</div></div>
                <div><div class="label">项目名称</div><div class="value">${job.project_name || '未命名'}</div></div>
                <div><div class="label">素材名称</div><div class="value">${job.asset_name || '未命名'}</div></div>
                <div><div class="label">状态</div><div class="value"><span class="status-badge status-${job.status}">${statusText}</span></div></div>
                <div><div class="label">创建时间</div><div class="value">${job.created_at || ''}</div></div>
                <div><div class="label">审核结论</div><div class="value"><span style="color:${verdictColorStyle};font-weight:600;">${verdictDisplay}</span></div></div>
                <div><div class="label">审核依据</div><div class="value" style="font-size:13px;color:#475569;">${report && report.auto_verdict_reason ? report.auto_verdict_reason : '暂无审核依据'}</div></div>
                <div><div class="label">错误信息</div><div class="value" style="color:#dc2626;">${job.error || '无'}</div></div>
            </div>
            ${reviewButtons}
        `;

        // 证据帧（修复：兼容字符串数组和对象数组）
        let evHtml = '';
        if (report && report.evidence_frames && report.evidence_frames.length > 0) {
            evHtml = '<h3 style="font-size:16px;margin:16px 0 8px;">📸 证据帧</h3><div style="display:flex;flex-wrap:wrap;gap:12px;">';
            for (const frame of report.evidence_frames) {
                let frameUrl = '';
                let frameLabel = '';
                if (typeof frame === 'string') {
                    frameUrl = '/outputs/' + jobId + '/' + frame;
                    frameLabel = '证据帧';
                } else if (typeof frame === 'object' && frame !== null) {
                    frameUrl = frame.url || '';
                    frameLabel = frame.label || '证据帧';
                }
                if (frameUrl) {
                    evHtml += `
                        <div class="evidence-frame">
                            <img src="${frameUrl}" alt="证据帧" style="width:100%;border-radius:4px;max-width:160px;">
                            <div class="frame-label">${frameLabel}</div>
                        </div>
                    `;
                }
            }
            evHtml += '</div>';
        }
        evidenceArea.innerHTML = evHtml;

    } catch (err) {
        alert('获取详情失败');
        console.error(err);
    }
}

// ============================================================
// 辅助：状态信息
// ============================================================
function showStatus(msg, type) {
    uploadStatus.textContent = msg;
    uploadStatus.style.color = type === 'success' ? '#16a34a'
        : type === 'error' ? '#dc2626'
        : type === 'warning' ? '#d97706'
        : '#475569';
}

// ============================================================
// 页面加载 & 定时刷新
// ============================================================
fetchTasks();
setInterval(fetchTasks, 10000);

// 暴露函数到全局
window.showDetail = showDetail;
window.deleteJob = deleteJob;
window.submitReview = submitReview;