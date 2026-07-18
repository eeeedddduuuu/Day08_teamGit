// ============================================================
// ContentGuard 前端逻辑
// ============================================================
let currentJobId = null;
let allJobs = [];

// DOM
const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const uploadBtn = document.getElementById('uploadBtn');
const previewArea = document.getElementById('previewArea');
const uploadStatus = document.getElementById('uploadStatus');
const taskList = document.getElementById('taskList');
const taskCount = document.getElementById('taskCount');
const searchInput = document.getElementById('searchInput');
const welcomeView = document.getElementById('welcomeView');
const detailView = document.getElementById('detailView');
const taskDetail = document.getElementById('taskDetail');
const evidenceArea = document.getElementById('evidenceArea');

// ===== Toast =====
function toast(msg, type) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    const t = document.createElement('div');
    t.className = 'toast toast-' + (type || 'info');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity 0.3s'; setTimeout(() => t.remove(), 300); }, 2500);
}

// ===== 上传 =====
uploadBtn.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('click', (e) => { if (e.target !== uploadBtn) fileInput.click(); });
uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.classList.add('drag-over'); });
uploadArea.addEventListener('dragleave', () => { uploadArea.classList.remove('drag-over'); });
uploadArea.addEventListener('drop', e => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; uploadFile(); }
});
fileInput.addEventListener('change', uploadFile);

async function uploadFile() {
    const file = fileInput.files[0];
    if (!file) { toast('请先选择文件', 'warning'); return; }
    const projectNameInput = document.getElementById('projectNameInput');
    const projectName = projectNameInput ? projectNameInput.value.trim() || '审核项目' : '审核项目';
    showPreview(file);
    uploadStatus.textContent = '上传中...';
    uploadStatus.style.color = '#6366f1';
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_name', projectName);
    try {
        const res = await fetch('/api/jobs', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.ok) {
            uploadStatus.textContent = '上传成功 ' + data.job_id;
            uploadStatus.style.color = '#10b981';
            fileInput.value = '';
            if (projectNameInput) projectNameInput.value = '';
            fetchTasks();
        } else {
            uploadStatus.textContent = '上传失败：' + (data.error || '未知错误');
            uploadStatus.style.color = '#ef4444';
        }
    } catch (err) {
        uploadStatus.textContent = '网络错误，请检查后端服务';
        uploadStatus.style.color = '#ef4444';
    }
}

function showPreview(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        if (file.type.startsWith('image/')) {
            previewArea.innerHTML = '<img src="' + e.target.result + '" alt="预览">';
        } else if (file.type.startsWith('video/')) {
            previewArea.innerHTML = '<video src="' + e.target.result + '" controls></video>';
        } else {
            previewArea.innerHTML = '<span style="color:#64748b;font-size:13px;">' + file.name + '</span>';
        }
    };
    reader.readAsDataURL(file);
}

// ===== 任务列表 =====
async function fetchTasks() {
    try {
        const res = await fetch('/api/jobs');
        const data = await res.json();
        if (data.ok && data.jobs) {
            allJobs = data.jobs;
            renderTaskList(allJobs);
        } else {
            taskList.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>暂无任务</p><span>上传素材开始审核</span></div>';
            taskCount.textContent = '0';
        }
    } catch (err) {
        taskList.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><p>无法连接后端</p></div>';
    }
}

function renderTaskList(jobs) {
    taskCount.textContent = jobs.length;
    if (!jobs.length) {
        taskList.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>暂无任务</p><span>上传素材开始审核</span></div>';
        return;
    }
    let html = '';
    for (const job of jobs) {
        const tagClass = 'tag-' + job.status;
        const statusText = { 'created': '已创建', 'queued': '排队中', 'running': '处理中', 'completed': '已完成', 'failed': '失败' }[job.status] || job.status;
        let progressHtml = '';
        if (job.status === 'running') {
            progressHtml = '<div class="progress-bar"><div class="fill"></div></div>';
        }
        html += '<div class="task-item' + (job.job_id === currentJobId ? ' active' : '') + '" onclick="showDetail(\'' + job.job_id + '\')">'
            + '<span class="task-item-name" title="' + (job.asset_name || '') + '">' + (job.asset_name || '未命名') + '</span>'
            + '<div class="task-item-meta">' + progressHtml + '<span class="status-tag ' + tagClass + '">' + statusText + '</span></div>'
            + '</div>';
    }
    taskList.innerHTML = html;
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

// ===== 删除 =====
async function deleteJob(jobId) {
    if (!confirm('确定要永久删除任务 ' + jobId + ' 吗？此操作不可恢复。')) return;
    try {
        const res = await fetch('/api/jobs/' + jobId, { method: 'DELETE' });
        const data = await res.json();
        if (data.ok) {
            toast('任务已删除', 'success');
            hideDetail();
            currentJobId = null;
            fetchTasks();
        } else {
            toast('删除失败：' + (data.error || '未知错误'), 'error');
        }
    } catch (err) { toast('网络错误', 'error'); }
}

// ===== 审核 =====
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
            const label = { pass: '通过', review: '待复核', reject: '不通过' }[verdict] || verdict;
            toast('审核结论已更新：' + label, 'success');
            showDetail(jobId);
        } else {
            toast('提交失败：' + (data.error || '未知错误'), 'error');
        }
    } catch (err) { toast('网络错误', 'error'); }
}

// ===== 任务详情 =====
async function showDetail(jobId) {
    try {
        const verdictLabel = { 'reject': '不通过', 'review': '待复核', 'pass': '通过' };
        const verdictColor = { 'reject': { bg: '#fef2f2', border: '#fecaca', text: '#dc2626', icon: '🚫' },
                               'review': { bg: '#fffbeb', border: '#fde68a', text: '#d97706', icon: '⚠️' },
                               'pass': { bg: '#f0fdf4', border: '#bbf7d0', text: '#16a34a', icon: '✅' }};

        const res = await fetch('/api/jobs/' + jobId);
        const data = await res.json();
        if (!data.ok) { toast('获取详情失败', 'error'); return; }

        const job = data.job;
        const report = data.report;
        currentJobId = jobId;

        welcomeView.style.display = 'none';
        detailView.style.display = 'block';

        const statusText = { 'created': '已创建', 'queued': '排队中', 'running': '处理中', 'completed': '已完成', 'failed': '失败' }[job.status] || '';

        // 判定最终结论
        let finalVerdict = null;
        let isManual = false;
        if (report && report.manual_review && report.manual_review.verdict) {
            finalVerdict = report.manual_review.verdict;
            isManual = true;
        } else if (report && report.auto_verdict) {
            finalVerdict = report.auto_verdict;
        }
        const vStyle = verdictColor[finalVerdict] || { bg: '#f8fafc', border: '#e2e8f0', text: '#64748b', icon: '⏳' };

        // ===== 素材预览 =====
        let materialHtml = '';
        const assetName = job.asset_name || '';
        const ext = assetName.split('.').pop().toLowerCase();
        if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
            materialHtml = '<div class="detail-block"><div class="detail-block-body">'
                + '<h4 style="margin-bottom:12px;color:#64748b;">📷 原始素材</h4>'
                + '<img src="/outputs/' + jobId + '/input/' + assetName + '" class="material-img" onclick="openLightbox(this.src)"></div></div>';
        } else if (['mp4', 'avi', 'mov', 'webm'].includes(ext)) {
            materialHtml = '<div class="detail-block"><div class="detail-block-body">'
                + '<h4 style="margin-bottom:12px;color:#64748b;">🎬 原始素材</h4>'
                + '<video src="/outputs/' + jobId + '/input/' + assetName + '" controls class="material-video"></video></div></div>';
        }

        // ===== 任务信息 =====
        let infoHtml = '<div class="detail-block"><div class="detail-block-header">📋 任务信息</div><div class="detail-block-body"><div class="info-grid">';
        infoHtml += infoRow('任务编号', job.job_id);
        infoHtml += infoRow('项目名称', job.project_name || '未命名');
        infoHtml += infoRow('素材名称', job.asset_name || '未命名');
        infoHtml += infoRow('当前状态', '<span class="status-tag tag-' + job.status + '">' + statusText + '</span>');
        infoHtml += infoRow('创建时间', job.created_at || '-');
        if (job.error) {
            infoHtml += infoRow('异常信息', '<span style="color:#ef4444;">' + job.error + '</span>');
        }
        infoHtml += '</div></div></div>';

        // ===== 审核结论 =====
        let verdictHtml = '<div class="detail-block"><div class="detail-block-body">';
        verdictHtml += '<div class="verdict-banner" style="background:' + vStyle.bg + ';border:2px solid ' + vStyle.border + ';">';
        verdictHtml += '<span class="verdict-banner-icon">' + vStyle.icon + '</span>';
        verdictHtml += '<div class="verdict-banner-text">';
        verdictHtml += '<div class="verdict-banner-title" style="color:' + vStyle.text + ';">' + (isManual ? '【人工】' : '【自动】') + '审核结论：' + (verdictLabel[finalVerdict] || '待处理') + '</div>';
        verdictHtml += '<div class="verdict-banner-reason">' + (report && report.auto_verdict_reason ? report.auto_verdict_reason : '等待分析完成') + '</div>';
        if (isManual && report.manual_review) {
            verdictHtml += '<div class="verdict-banner-meta">审核人：' + (report.manual_review.reviewer || '-') + ' ｜ 备注：' + (report.manual_review.notes || '-') + '</div>';
        }
        verdictHtml += '</div></div>';
        // 审核表单
        if (job.status === 'completed') {
            verdictHtml += '<div class="review-form"><h4 style="margin-bottom:12px;">✏️ 人工复核</h4>';
            verdictHtml += '<div class="review-form-row"><input id="reviewerName" class="input-text" placeholder="审核人姓名"><input id="reviewNotes" class="input-text" placeholder="审核备注（可选）"></div>';
            verdictHtml += '<div style="display:flex;gap:10px;flex-wrap:wrap;">';
            verdictHtml += '<button class="btn btn-pass" onclick="submitReview(\'' + jobId + '\',\'pass\')">✅ 通过</button>';
            verdictHtml += '<button class="btn btn-review" onclick="submitReview(\'' + jobId + '\',\'review\')">⚠️ 待复核</button>';
            verdictHtml += '<button class="btn btn-reject" onclick="submitReview(\'' + jobId + '\',\'reject\')">🚫 不通过</button>';
            verdictHtml += '<button class="btn btn-delete" onclick="deleteJob(\'' + jobId + '\')" style="margin-left:auto;">🗑️ 删除任务</button>';
            verdictHtml += '</div></div>';
        }
        verdictHtml += '</div></div>';

        // ===== 检测结果 =====
        let detHtml = '';
        if (report && report.detection_summary) {
            const ds = report.detection_summary;
            detHtml = '<div class="detail-block"><div class="detail-block-header">🔍 检测结果</div><div class="detail-block-body">';
            detHtml += '<table class="data-table"><thead><tr><th>指标</th><th>数值</th></tr></thead><tbody>';
            detHtml += '<tr><td>总检测数</td><td><b>' + (ds.total_detections || 0) + '</b></td></tr>';
            detHtml += '<tr><td>检测类别</td><td>' + (Object.keys(ds.classes_detected || {}).join(', ') || '无') + '</td></tr>';
            detHtml += '<tr><td>最高置信度</td><td>' + (ds.max_confidence || 0).toFixed(4) + '</td></tr>';
            detHtml += '<tr><td>平均置信度</td><td>' + (ds.avg_confidence || 0).toFixed(4) + '</td></tr>';
            detHtml += '<tr><td>分析帧数</td><td>' + (ds.total_frames || report.total_frames_analyzed || 1) + '</td></tr>';
            detHtml += '</tbody></table>';
            if (report.risk_detections && report.risk_detections.length > 0) {
                detHtml += '<h4 style="margin:16px 0 8px;color:#ef4444;">⚠️ 风险检测详情</h4>';
                detHtml += '<table class="data-table"><thead><tr><th>帧</th><th>时间</th><th>类别</th><th>置信度</th><th>边界框</th></tr></thead><tbody>';
                for (const d of report.risk_detections) {
                    detHtml += '<tr class="row-danger"><td>' + (d.frame_index || 0) + '</td><td>' + (d.timestamp || 0).toFixed(1) + 's</td><td><b>' + d.class + '</b></td><td>' + (d.confidence || 0).toFixed(4) + '</td><td>[' + (d.bbox || []).join(', ') + ']</td></tr>';
                }
                detHtml += '</tbody></table>';
            }
            detHtml += '</div></div>';
        }

        // ===== 证据帧 =====
        let evHtml = '';
        if (report && report.evidence_frames && report.evidence_frames.length > 0) {
            evHtml = '<div class="detail-block"><div class="detail-block-header">📸 证据帧</div><div class="detail-block-body"><div class="evidence-grid">';
            for (const frame of report.evidence_frames) {
                let frameUrl = '', label = '证据帧';
                if (typeof frame === 'string') { frameUrl = '/outputs/' + jobId + '/' + frame; }
                else if (typeof frame === 'object' && frame !== null) { frameUrl = frame.url || ''; label = frame.label || '证据帧'; }
                if (frameUrl) {
                    evHtml += '<div class="evidence-card" onclick="openLightbox(\'' + frameUrl + '\')">'
                        + '<img src="' + frameUrl + '" alt="证据帧"><div class="evidence-card-label">' + label + '</div></div>';
                }
            }
            evHtml += '</div></div></div>';
        }

        taskDetail.innerHTML = materialHtml + infoHtml + verdictHtml + detHtml;
        evidenceArea.innerHTML = evHtml;
        detailView.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // 更新任务列表高亮
        renderTaskList(allJobs);

    } catch (err) { toast('获取详情失败', 'error'); }
}

function infoRow(label, value) {
    return '<div class="info-item"><div class="info-label">' + label + '</div><div class="info-value">' + value + '</div></div>';
}

function hideDetail() {
    welcomeView.style.display = '';
    detailView.style.display = 'none';
    taskDetail.innerHTML = '';
    evidenceArea.innerHTML = '';
}

// ===== 灯箱 =====
function openLightbox(src) {
    const lb = document.createElement('div');
    lb.className = 'lightbox';
    lb.innerHTML = '<span class="lightbox-close">&times;</span><img src="' + src + '" class="lightbox-img">';
    lb.querySelector('.lightbox-close').addEventListener('click', () => lb.remove());
    lb.addEventListener('click', function(e) { if (e.target === lb) lb.remove(); });
    document.body.appendChild(lb);
}

// ===== 初始化 =====
fetchTasks();
setInterval(fetchTasks, 10000);

window.showDetail = showDetail;
window.deleteJob = deleteJob;
window.submitReview = submitReview;
window.openLightbox = openLightbox;
