// ============================================================
// ContentGuard — 智能内容审核工作台 前端逻辑
// ============================================================
let currentJobId = null;

// DOM 引用
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const uploadArea = document.getElementById('uploadArea');
const previewArea = document.getElementById('previewArea');
const uploadStatus = document.getElementById('uploadStatus');
const taskList = document.getElementById('taskList');
const detailSection = document.getElementById('detailSection');
const taskDetail = document.getElementById('taskDetail');
const evidenceArea = document.getElementById('evidenceArea');
const searchInput = document.getElementById('searchInput');
const verdictCount = document.getElementById('verdictCount');

// 缓存任务列表用于搜索
let allJobs = [];

// ============================================================
// Toast 通知
// ============================================================
function toast(msg, type) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    const t = document.createElement('div');
    t.className = 'toast toast-' + (type || 'info');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 2500);
}

// ============================================================
// 上传
// ============================================================
uploadBtn.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.style.borderColor = '#4f46e5'; });
uploadArea.addEventListener('dragleave', () => { uploadArea.style.borderColor = '#cbd5e1'; });
uploadArea.addEventListener('drop', e => {
    e.preventDefault();
    uploadArea.style.borderColor = '#cbd5e1';
    if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; uploadFile(); }
});
fileInput.addEventListener('change', uploadFile);

async function uploadFile() {
    const file = fileInput.files[0];
    if (!file) { showStatus('请先选择文件', 'warning'); return; }
    const projectNameInput = document.getElementById('projectNameInput');
    const projectName = projectNameInput ? projectNameInput.value.trim() || '审核项目' : '审核项目';
    showPreview(file);
    showStatus('上传中...', 'loading');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_name', projectName);
    try {
        const res = await fetch('/api/jobs', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.ok) {
            showStatus('上传成功！任务 ID：' + data.job_id, 'success');
            fileInput.value = '';
            if (projectNameInput) projectNameInput.value = '';
            fetchTasks();
        } else {
            showStatus('上传失败：' + (data.error || '未知错误'), 'error');
        }
    } catch (err) {
        showStatus('网络错误，请检查后端服务', 'error');
    }
}

function showPreview(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        if (file.type.startsWith('image/')) {
            previewArea.innerHTML = '<img src="' + e.target.result + '" alt="预览" class="preview-img">';
        } else if (file.type.startsWith('video/')) {
            previewArea.innerHTML = '<video src="' + e.target.result + '" controls class="preview-video"></video>';
        } else {
            previewArea.innerHTML = '<span style="color:#64748b;">' + file.name + '</span>';
        }
    };
    reader.readAsDataURL(file);
}

// ============================================================
// 任务列表
// ============================================================
async function fetchTasks() {
    try {
        const res = await fetch('/api/jobs');
        const data = await res.json();
        if (data.ok && data.jobs) {
            allJobs = data.jobs;
            renderTaskList(allJobs);
        } else {
            taskList.innerHTML = '<p class="empty-tip">暂无任务</p>';
        }
    } catch (err) {
        taskList.innerHTML = '<p class="empty-tip">无法连接后端服务</p>';
    }
}

function renderTaskList(jobs) {
    if (!jobs || jobs.length === 0) {
        taskList.innerHTML = '<p class="empty-tip">暂无任务，上传一个素材开始吧</p>';
        updateVerdictCount([]);
        return;
    }
    // 统计
    updateVerdictCount(jobs);
    let html = '';
    for (const job of jobs) {
        const statusClass = 'status-' + job.status;
        const statusText = { 'created': '已创建', 'queued': '排队中', 'running': '处理中', 'completed': '已完成', 'failed': '失败' }[job.status] || job.status;
        let progressHtml = '';
        if (job.status === 'running') {
            progressHtml = '<div class="progress-wrapper"><div class="fill"></div></div>';
        }
        html += '<div class="task-card' + (job.job_id === currentJobId ? ' active' : '') + '" onclick="showDetail(\'' + job.job_id + '\')">'
            + '<div class="task-left"><span class="task-name">' + (job.asset_name || '未命名') + '</span>' + progressHtml + '</div>'
            + '<div class="task-meta"><span class="status-badge ' + statusClass + '">' + statusText + '</span>'
            + '<span class="task-time">' + (job.created_at || '') + '</span></div></div>';
    }
    taskList.innerHTML = html;
}

function updateVerdictCount(jobs) {
    // 简单统计（如果有 report 数据的话）
    if (!verdictCount) return;
    // 这里需要遍历 report，但任务列表可能没有带 report
    // 仅在页面加载时通过 data-属性 或者额外 API 实现
}

// 搜索
if (searchInput) {
    searchInput.addEventListener('input', function() {
        const q = this.value.toLowerCase();
        const filtered = allJobs.filter(j =>
            (j.asset_name || '').toLowerCase().includes(q) ||
            (j.job_id || '').toLowerCase().includes(q) ||
            (j.project_name || '').toLowerCase().includes(q)
        );
        renderTaskList(filtered);
    });
}

// ============================================================
// 删除
// ============================================================
async function deleteJob(jobId) {
    if (!confirm('确定要删除任务 ' + jobId + ' 吗？此操作不可恢复。')) return;
    try {
        const res = await fetch('/api/jobs/' + jobId, { method: 'DELETE' });
        const data = await res.json();
        if (data.ok) {
            toast('任务已删除', 'success');
            detailSection.style.display = 'none';
            currentJobId = null;
            fetchTasks();
        } else {
            toast('删除失败：' + (data.error || '未知错误'), 'error');
        }
    } catch (err) { toast('删除失败，请检查网络', 'error'); }
}

// ============================================================
// 人工审核（内联表单）
// ============================================================
async function submitReview(jobId, verdict) {
    const reviewer = document.getElementById('reviewerName').value.trim() || '审核员';
    const notes = document.getElementById('reviewNotes').value.trim() || '';
    try {
        const res = await fetch('/api/jobs/' + jobId + '/review', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ verdict: verdict, reviewer: reviewer, notes: notes })
        });
        const data = await res.json();
        if (data.ok) {
            toast('审核结论已更新为：' + ({ pass: '通过', review: '待复核', reject: '不通过' }[verdict] || verdict), 'success');
            showDetail(jobId);
        } else {
            toast('审核提交失败：' + (data.error || '未知错误'), 'error');
        }
    } catch (err) { toast('审核提交失败，请检查网络', 'error'); }
}

// ============================================================
// 任务详情（核心 — 对应 DEMO_SCRIPT 第2/3/4段）
// ============================================================
async function showDetail(jobId) {
    try {
        const verdictMap = { 'reject': '不通过', 'review': '待复核', 'pass': '通过' };
        const verdictColor = { 'reject': '#dc2626', 'review': '#d97706', 'pass': '#16a34a' };
        const verdictBg = { 'reject': '#fef2f2', 'review': '#fffbeb', 'pass': '#f0fdf4' };
        const verdictBorder = { 'reject': '#fecaca', 'review': '#fde68a', 'pass': '#bbf7d0' };

        const res = await fetch('/api/jobs/' + jobId);
        const data = await res.json();
        if (!data.ok) { toast('获取详情失败：' + (data.error || ''), 'error'); return; }

        const job = data.job;
        const report = data.report;
        currentJobId = jobId;
        detailSection.style.display = 'block';

        const statusText = { 'created': '已创建', 'queued': '排队中', 'running': '处理中', 'completed': '已完成', 'failed': '失败' }[job.status] || job.status;

        // 审核结论
        let verdictDisplay = '待处理', verdictColorStyle = '#64748b', verdictBgStyle = '#f8fafc', verdictBorderStyle = '#e2e8f0';
        if (report) {
            const finalVerdict = report.manual_review ? report.manual_review.verdict : (report.auto_verdict || null);
            if (finalVerdict && verdictMap[finalVerdict]) {
                verdictDisplay = verdictMap[finalVerdict];
                verdictColorStyle = verdictColor[finalVerdict] || '#64748b';
                verdictBgStyle = verdictBg[finalVerdict] || '#f8fafc';
                verdictBorderStyle = verdictBorder[finalVerdict] || '#e2e8f0';
                // 如果是人工审核，加标记
                if (report.manual_review && report.manual_review.verdict) {
                    verdictDisplay = '【人工】' + verdictDisplay;
                }
            }
        }

        // 审核依据
        let verdictReason = '暂无审核依据';
        if (report && report.auto_verdict_reason) verdictReason = report.auto_verdict_reason;

        // ===== 原始素材预览 =====
        let materialHtml = '';
        const assetName = job.asset_name || '';
        const ext = assetName.split('.').pop().toLowerCase();
        if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
            materialHtml = '<div class="material-preview"><h4>原始素材</h4><img src="/outputs/' + jobId + '/input/' + assetName + '" alt="原始素材" class="material-img" onclick="openLightbox(this.src)"></div>';
        } else if (['mp4', 'avi', 'mov', 'webm'].includes(ext)) {
            materialHtml = '<div class="material-preview"><h4>原始素材</h4><video src="/outputs/' + jobId + '/input/' + assetName + '" controls class="material-video"></video></div>';
        } else if (assetName) {
            materialHtml = '<div class="material-preview"><h4>原始素材</h4><p style="color:#64748b;">' + assetName + '</p></div>';
        }

        // ===== 检测结果表格 =====
        let detTableHtml = '';
        if (report && report.detection_summary) {
            const ds = report.detection_summary;
            detTableHtml = '<div class="det-summary"><h4>检测摘要</h4>'
                + '<table class="summary-table">'
                + '<tr><td>总检测数</td><td><b>' + (ds.total_detections || 0) + '</b></td></tr>'
                + '<tr><td>检测类别</td><td>' + (Object.keys(ds.classes_detected || {}).join(', ') || '无') + '</td></tr>'
                + '<tr><td>最高置信度</td><td><b>' + (ds.max_confidence || 0).toFixed(4) + '</b></td></tr>'
                + '<tr><td>平均置信度</td><td>' + (ds.avg_confidence || 0).toFixed(4) + '</td></tr>'
                + '<tr><td>分析帧数</td><td>' + (ds.total_frames || report.total_frames_analyzed || 1) + '</td></tr>'
                + '</table></div>';
        }

        // ===== 风险检测列表 =====
        let riskHtml = '';
        if (report && report.risk_detections && report.risk_detections.length > 0) {
            riskHtml = '<div class="risk-list"><h4 style="color:#dc2626;">风险检测详情</h4><table class="det-table"><thead><tr><th>帧</th><th>时间</th><th>类别</th><th>置信度</th><th>边界框</th></tr></thead><tbody>';
            for (const d of report.risk_detections) {
                const bbox = (d.bbox || []).join(', ');
                riskHtml += '<tr style="background:#fef2f2;"><td>' + (d.frame_index || 0) + '</td><td>' + (d.timestamp || 0).toFixed(1) + 's</td><td><b>' + d.class + '</b></td><td style="color:#dc2626;font-weight:600;">' + (d.confidence || 0).toFixed(4) + '</td><td>[' + bbox + ']</td></tr>';
            }
            riskHtml += '</tbody></table></div>';
        }

        // ===== 审核结论卡片 =====
        let verdictCardHtml = '<div class="verdict-card" style="background:' + verdictBgStyle + ';border:2px solid ' + verdictBorderStyle + ';border-radius:12px;padding:20px;margin:16px 0;">'
            + '<div style="font-size:18px;font-weight:700;color:' + verdictColorStyle + ';">审核结论：' + verdictDisplay + '</div>'
            + '<div style="font-size:14px;color:#475569;margin-top:8px;">' + verdictReason + '</div>';
        if (report && report.manual_review && report.manual_review.verdict) {
            verdictCardHtml += '<div style="font-size:13px;color:#64748b;margin-top:8px;">审核人：' + (report.manual_review.reviewer || '未知') + ' | 备注：' + (report.manual_review.notes || '无') + '</div>';
        }
        verdictCardHtml += '</div>';

        // ===== 审核表单 =====
        let reviewFormHtml = '';
        if (job.status === 'completed') {
            reviewFormHtml = '<div class="review-form" style="margin-top:16px;padding:16px;background:#f8fafc;border-radius:12px;">'
                + '<h4 style="margin:0 0 12px;">人工审核</h4>'
                + '<div style="display:flex;gap:10px;margin-bottom:10px;flex-wrap:wrap;">'
                + '<input id="reviewerName" placeholder="审核人姓名" style="padding:8px 12px;border:1px solid #d1d5db;border-radius:6px;flex:1;min-width:120px;">'
                + '<input id="reviewNotes" placeholder="审核备注（可选）" style="padding:8px 12px;border:1px solid #d1d5db;border-radius:6px;flex:2;min-width:200px;">'
                + '</div>'
                + '<div style="display:flex;gap:10px;flex-wrap:wrap;">'
                + '<button onclick="submitReview(\'' + job.job_id + '\',\'pass\')" style="background:#16a34a;color:#fff;border:none;padding:10px 24px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;">通过</button>'
                + '<button onclick="submitReview(\'' + job.job_id + '\',\'review\')" style="background:#d97706;color:#fff;border:none;padding:10px 24px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;">待复核</button>'
                + '<button onclick="submitReview(\'' + job.job_id + '\',\'reject\')" style="background:#dc2626;color:#fff;border:none;padding:10px 24px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;">不通过</button>'
                + '<button onclick="deleteJob(\'' + job.job_id + '\')" style="background:#6b7280;color:#fff;border:none;padding:10px 24px;border-radius:8px;cursor:pointer;font-size:14px;margin-left:auto;">删除任务</button>'
                + '</div></div>';
        }

        // ===== 组装详情 =====
        taskDetail.innerHTML = '<div class="detail-content">'
            + '<div class="detail-grid">'
            + '<div class="detail-item"><span class="label">任务 ID</span><span class="value">' + job.job_id + '</span></div>'
            + '<div class="detail-item"><span class="label">项目名称</span><span class="value">' + (job.project_name || '未命名') + '</span></div>'
            + '<div class="detail-item"><span class="label">素材名称</span><span class="value">' + (job.asset_name || '未命名') + '</span></div>'
            + '<div class="detail-item"><span class="label">状态</span><span class="value"><span class="status-badge status-' + job.status + '">' + statusText + '</span></span></div>'
            + '<div class="detail-item"><span class="label">创建时间</span><span class="value">' + (job.created_at || '') + '</span></div>'
            + '<div class="detail-item"><span class="label">异常信息</span><span class="value" style="color:#dc2626;">' + (job.error || '无') + '</span></div>'
            + '</div></div>'
            + materialHtml
            + verdictCardHtml
            + detTableHtml
            + riskHtml
            + reviewFormHtml;

        // ===== 证据帧（可点击放大）=====
        let evHtml = '';
        if (report && report.evidence_frames && report.evidence_frames.length > 0) {
            evHtml = '<h3 style="font-size:16px;margin:16px 0 8px;">证据帧</h3><div style="display:flex;flex-wrap:wrap;gap:12px;">';
            for (const frame of report.evidence_frames) {
                let frameUrl = '', frameLabel = '证据帧';
                if (typeof frame === 'string') { frameUrl = '/outputs/' + jobId + '/' + frame; }
                else if (typeof frame === 'object' && frame !== null) {
                    frameUrl = frame.url || ''; frameLabel = frame.label || '证据帧';
                }
                if (frameUrl) {
                    evHtml += '<div class="evidence-frame" style="cursor:pointer;" onclick="openLightbox(\'' + frameUrl + '\')">'
                        + '<img src="' + frameUrl + '" alt="证据帧" style="width:100%;border-radius:4px;max-width:200px;">'
                        + '<div class="frame-label">' + frameLabel + '</div></div>';
                }
            }
            evHtml += '</div>';
        }
        evidenceArea.innerHTML = evHtml;

        // 滚动到详情
        detailSection.scrollIntoView({ behavior: 'smooth' });

    } catch (err) { toast('获取详情失败', 'error'); }
}

// ============================================================
// 图片灯箱
// ============================================================
function openLightbox(src) {
    const lb = document.createElement('div');
    lb.className = 'lightbox';
    lb.innerHTML = '<span class="lightbox-close" onclick="this.parentElement.remove()">&times;</span><img src="' + src + '" class="lightbox-img">';
    lb.addEventListener('click', function(e) { if (e.target === lb) lb.remove(); });
    document.body.appendChild(lb);
}

// ============================================================
// 辅助
// ============================================================
function showStatus(msg, type) {
    uploadStatus.textContent = msg;
    uploadStatus.style.color = type === 'success' ? '#16a34a' : type === 'error' ? '#dc2626' : type === 'warning' ? '#d97706' : '#475569';
}

// ============================================================
// 初始化
// ============================================================
fetchTasks();
setInterval(fetchTasks, 10000);

// 暴露全局函数
window.showDetail = showDetail;
window.deleteJob = deleteJob;
window.submitReview = submitReview;
window.openLightbox = openLightbox;
