import { chromium } from 'playwright'
import { copyFile, mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(scriptDir, '..', '..')
const docsOutput = path.join(repoRoot, 'docs', 'screenshots')
const websiteOutput = path.join(repoRoot, 'website', 'screenshots')
const baseURL = process.env.ONCOPATH_SCREENSHOT_BASE_URL || 'http://127.0.0.1:3000'

await mkdir(docsOutput, { recursive: true })
await mkdir(websiteOutput, { recursive: true })

const patient = {
  patient_id: 1,
  patient_name: '演示患者 A***',
  gender: 'female',
  age: 52,
  is_primary: true,
  diagnosis: '术后随访',
}

const indicators = {
  blood_routine: [
    { detail_id: 1, index_id: 11, index_name: '白细胞计数', index_value: '5.82', index_unit: '×10⁹/L', index_status: 'normal', medical_date: '2026-08-12' },
    { detail_id: 2, index_id: 12, index_name: '血红蛋白', index_value: '108', index_unit: 'g/L', index_status: 'low', medical_date: '2026-08-12' },
    { detail_id: 3, index_id: 13, index_name: '血小板计数', index_value: '236', index_unit: '×10⁹/L', index_status: 'normal', medical_date: '2026-08-12' },
  ],
  tumor_markers: [
    { detail_id: 4, index_id: 21, index_name: '癌胚抗原 CEA', index_value: '3.24', index_unit: 'ng/mL', index_status: 'normal', medical_date: '2026-08-12' },
    { detail_id: 5, index_id: 22, index_name: '糖类抗原 CA19-9', index_value: '24.6', index_unit: 'U/mL', index_status: 'normal', medical_date: '2026-08-12' },
    { detail_id: 6, index_id: 23, index_name: '糖类抗原 CA125', index_value: '41.2', index_unit: 'U/mL', index_status: 'high', medical_date: '2026-08-12' },
  ],
}

const histories = {
  11: { name: '白细胞计数', unit: '×10⁹/L', min: 3.5, max: 9.5, values: [6.4, 5.9, 5.5, 5.82] },
  12: { name: '血红蛋白', unit: 'g/L', min: 115, max: 150, values: [126, 119, 112, 108] },
  13: { name: '血小板计数', unit: '×10⁹/L', min: 125, max: 350, values: [228, 241, 219, 236] },
  21: { name: '癌胚抗原 CEA', unit: 'ng/mL', min: 0, max: 5, values: [4.3, 3.9, 3.5, 3.24] },
  22: { name: '糖类抗原 CA19-9', unit: 'U/mL', min: 0, max: 37, values: [31.4, 28.7, 26.1, 24.6] },
  23: { name: '糖类抗原 CA125', unit: 'U/mL', min: 0, max: 35, values: [52.8, 48.2, 44.7, 41.2] },
}

const historyDates = ['2026-05-15', '2026-06-18', '2026-07-16', '2026-08-12']

function historyPayload(id) {
  const item = histories[id] || histories[11]
  return {
    index_info: {
      index_id: Number(id),
      index_name: item.name,
      index_unit: item.unit,
      reference_min: item.min,
      reference_max: item.max,
      is_edit: true,
      is_chart: true,
    },
    history: historyDates.map((medical_date, index) => ({
      medical_id: 1000 + Number(id) * 10 + index,
      medical_detail_id: 2000 + Number(id) * 10 + index,
      medical_date,
      index_name: item.name,
      index_value: String(item.values[index]),
      index_unit: item.unit,
      reference_value: `${item.min}-${item.max}`,
      index_status: item.values[index] < item.min ? 'low' : item.values[index] > item.max ? 'high' : 'normal',
      comment: index === 3 ? '演示随访数据' : '',
    })),
  }
}

const labReport = {
  medical_id: 101,
  patient_id: 1,
  hospital: '示例医学中心（演示）',
  medical_date: '2026-08-12',
  category: 'blood_routine',
  category_name: '血常规',
  comment: '公开演示数据，身份信息已遮蔽',
  interpretation_at: '2026-08-12T10:30:00',
  interpretation: '### 整体情况\n多数指标处于参考范围。血红蛋白轻度偏低，建议结合近期治疗和饮食情况继续观察。\n\n### 复查提醒\n建议按医生安排复查血常规，并结合连续趋势判断变化。',
  details: [
    { medical_detail_id: 1, index_id: 11, index_name: '白细胞计数', index_value: '5.82', index_unit: '×10⁹/L', reference_value: '3.5-9.5', index_status: 'normal' },
    { medical_detail_id: 2, index_id: 12, index_name: '血红蛋白', index_value: '108', index_unit: 'g/L', reference_value: '115-150', index_status: 'low' },
    { medical_detail_id: 3, index_id: 13, index_name: '血小板计数', index_value: '236', index_unit: '×10⁹/L', reference_value: '125-350', index_status: 'normal' },
    { medical_detail_id: 4, index_id: 14, index_name: '中性粒细胞百分比', index_value: '62.4', index_unit: '%', reference_value: '40-75', index_status: 'normal' },
    { medical_detail_id: 5, index_id: 15, index_name: '淋巴细胞百分比', index_value: '28.1', index_unit: '%', reference_value: '20-50', index_status: 'normal' },
  ],
}

const examReport = {
  exam_id: 201,
  patient_id: 1,
  title: '胸部 CT 复查',
  exam_type: 'CT',
  hospital: '示例医学中心（演示）',
  medical_date: '2026-08-08',
  exam_info: '双肺纹理清晰。术区改变稳定，未见明确新发占位。纵隔未见明显肿大淋巴结。',
  exam_diag: '术后复查影像表现稳定，建议结合临床按期随访。',
  comment: '公开演示报告，未使用真实患者资料。',
  interpretation_at: '2026-08-08T16:10:00',
  interpretation: '### 重点发现\n本次复查与既往相比整体稳定，报告未提示明确新发异常。\n\n### 下一步\n请携带既往影像由主治医生进行连续对比，并按既定计划复查。',
}

const pathologyReport = {
  pathology_id: 301,
  patient_id: 1,
  report_title: '术后病理报告（演示）',
  report_date: '2026-07-22',
  hospital: '示例医学中心（演示）',
  diagnosis: '示例性病理描述：标本切缘未见异常累及；以下内容仅用于界面演示。',
  cancer_type: '示例肿瘤类型',
  stage: '示例分期',
  histology_type: '示例组织学类型',
  ihc_markers: [
    { marker_name: 'ER', result: '阳性', intensity: '中等', percentage: '70%' },
    { marker_name: 'PR', result: '阳性', intensity: '弱至中等', percentage: '40%' },
    { marker_name: 'Ki-67', result: '约 15%' },
  ],
  gene_testing: '演示结果：未纳入任何真实基因检测数据。',
  comment: '公开演示数据，不能用于诊疗判断。',
  interpretation_at: '2026-07-22T14:20:00',
  interpretation: '### 报告说明\n该页面展示病理诊断、分期、组织学、免疫组化与基因检测信息的统一整理能力。\n\n### 重要提示\n演示内容不代表真实医学结论，实际报告必须由专业医生结合完整病史解释。',
}

const compareIndexes = [
  { index_id: 21, index_name: '癌胚抗原 CEA', index_unit: 'ng/mL', reference_min: 0, reference_max: 5 },
  { index_id: 22, index_name: '糖类抗原 CA19-9', index_unit: 'U/mL', reference_min: 0, reference_max: 37 },
  { index_id: 23, index_name: '糖类抗原 CA125', index_unit: 'U/mL', reference_min: 0, reference_max: 35 },
]

const comparePayload = {
  indexes: compareIndexes,
  aligned_data: historyDates.map((date, index) => ({
    date,
    values: {
      21: histories[21].values[index],
      22: histories[22].values[index],
      23: histories[23].values[index],
    },
  })),
}

const conversations = [
  { id: 401, patient_id: 1, title: '术后复查综合分析-#401', preview: '多学科团队已完成资料梳理、证据检索与风险汇总。', status: 'completed', external_status: 'completed', created_at: '2026-08-10T02:10:00', updated_at: '2026-08-10T03:25:00' },
  { id: 402, patient_id: 1, title: '指标趋势联合评估-#402', preview: '正在对检验趋势和影像随访结果进行并行分析。', status: 'monitoring', external_status: 'monitoring', created_at: '2026-08-15T01:30:00', updated_at: '2026-08-15T02:05:00' },
  { id: 403, patient_id: 1, title: '用药随访问题整理-#403', preview: '已形成结构化问题清单，等待补充最近一次用药反馈。', status: 'questioning', external_status: 'questioning', created_at: '2026-08-16T06:20:00', updated_at: '2026-08-16T06:40:00' },
]

const knowledgeCategories = [
  { category_id: 10, category_name: '诊疗指南', document_count: 3, children: [
    { category_id: 11, category_name: '随访与复查', document_count: 2, children: [] },
  ] },
  { category_id: 20, category_name: '患者教育', document_count: 2, children: [] },
  { category_id: 30, category_name: '用药资料', document_count: 1, children: [] },
]

const knowledgeDocuments = [
  { doc_id: 501, doc_name: '随访计划与复查项目（演示）.pdf', file_type: 'pdf', file_size: 884736, category_name: '随访与复查', created_at: '2026-08-11T08:00:00', summary_status: 'completed', summary: '整理不同阶段的复查项目、时间窗口和需要携带的历史资料。' },
  { doc_id: 502, doc_name: '检查前准备事项（演示）.docx', file_type: 'docx', file_size: 126976, category_name: '患者教育', created_at: '2026-08-09T08:00:00', summary_status: 'completed', summary: '汇总常见检查前的饮食、用药和资料准备提醒。' },
  { doc_id: 503, doc_name: '检验指标术语表（演示）.xlsx', file_type: 'xlsx', file_size: 56320, category_name: '诊疗指南', created_at: '2026-08-05T08:00:00', summary_status: 'completed', summary: '帮助理解常见指标名称、单位和连续趋势记录方式。' },
  { doc_id: 504, doc_name: '家庭用药记录模板（演示）.xlsx', file_type: 'xlsx', file_size: 41984, category_name: '用药资料', created_at: '2026-07-29T08:00:00', summary_status: 'completed', summary: '用于记录服药时间、剂量、漏服情况和不适反馈。' },
]

function agentTeamsDemoHtml() {
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}body{margin:0;font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif;color:#183b4b;background:linear-gradient(145deg,#f5fdff,#ecf8fb)}
    .shell{min-height:100vh;padding:28px}.hero{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;margin-bottom:22px}.eyebrow{color:#0787a7;font-weight:700;letter-spacing:.08em}.hero h1{margin:6px 0;font-size:28px}.hero p{margin:0;color:#64748b}.status{padding:8px 14px;border-radius:999px;background:#dff8ed;color:#087a55;font-weight:700}
    .progress{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}.step{padding:14px;border:1px solid #cceaf1;border-radius:14px;background:rgba(255,255,255,.78)}.step strong{display:block;color:#0787a7}.step.done:before{content:'✓';float:right;color:#0b9b6f}
    .grid{display:grid;grid-template-columns:1.15fr .85fr;gap:18px}.card{background:#fff;border:1px solid #dceff3;border-radius:18px;padding:20px;box-shadow:0 12px 34px rgba(15,85,105,.08)}.card h2{font-size:17px;margin:0 0 14px}.expert{display:grid;grid-template-columns:42px 1fr auto;gap:12px;align-items:center;padding:12px 0;border-bottom:1px solid #edf5f7}.expert:last-child{border:0}.avatar{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;background:#e2f7fb;color:#0787a7;font-weight:800}.expert span,.muted{color:#718496}.tag{padding:4px 9px;border-radius:999px;background:#eef9fb;color:#0787a7;font-size:12px}
    .summary{white-space:pre-line;color:#3d5662}.sources{margin-top:14px;padding-top:14px;border-top:1px solid #edf5f7}.source{display:flex;gap:8px;margin:8px 0;color:#536b76}.source:before{content:'↗';color:#0787a7}
  </style></head><body><main class="shell"><div class="hero"><div><div class="eyebrow">AGENTTEAMS · 多智能体协作</div><h1>术后复查综合分析</h1><p>演示会诊 #401 · 数据已脱敏 · 仅供界面展示</p></div><div class="status">会诊已完成</div></div><div class="progress"><div class="step done"><strong>资料评估</strong>完整性检查</div><div class="step done"><strong>专家组队</strong>4 个角色</div><div class="step done"><strong>并行分析</strong>证据与趋势</div><div class="step done"><strong>综合汇总</strong>形成报告</div></div><div class="grid"><section class="card"><h2>专家团队与结论</h2><div class="expert"><div class="avatar">综</div><div><b>综合协调 Agent</b><br><span>整合报告、影像与随访目标</span></div><em class="tag">已完成</em></div><div class="expert"><div class="avatar">检</div><div><b>检验趋势 Agent</b><br><span>分析血常规与肿瘤标志物变化</span></div><em class="tag">已完成</em></div><div class="expert"><div class="avatar">影</div><div><b>影像随访 Agent</b><br><span>对比复查报告的稳定性描述</span></div><em class="tag">已完成</em></div><div class="expert"><div class="avatar">药</div><div><b>用药支持 Agent</b><br><span>整理用药记录与复查注意事项</span></div><em class="tag">已完成</em></div></section><section class="card"><h2>综合摘要</h2><div class="summary">现有演示资料显示整体随访节奏清晰，近期影像描述稳定。部分检验指标需要结合连续趋势继续观察。

建议将下一次复查时间、需携带的历史影像和重点问题写入随访清单，并由专业医生结合完整病史判断。</div><div class="sources"><b>证据入口</b><div class="source">检验报告与组合指标趋势</div><div class="source">影像复查记录</div><div class="source">知识库随访计划</div></div></section></div></main></body></html>`
}

async function fulfillJson(route, body, status = 200) {
  await route.fulfill({ status, contentType: 'application/json; charset=utf-8', body: JSON.stringify(body) })
}

async function mockApi(route) {
  const request = route.request()
  const url = new URL(request.url())
  const pathname = url.pathname

  if (pathname === '/agentteams-demo') {
    await route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: agentTeamsDemoHtml() })
    return
  }

  if (!pathname.startsWith('/api/v1/')) {
    await route.continue()
    return
  }

  const apiPath = pathname.slice('/api/v1'.length)
  if (apiPath === '/accounts/me') return fulfillJson(route, { account_id: 1, username: '公开演示账号', account_name: '公开演示账号', account_type: 'user' })
  if (apiPath === '/accounts/notifications') return fulfillJson(route, { items: [], total: 0, unread_count: 0 })
  if (apiPath === '/patients') return fulfillJson(route, [patient])
  if (apiPath === '/patients/primary' || apiPath === '/patients/1') return fulfillJson(route, patient)
  if (apiPath === '/dashboard/1') return fulfillJson(route, {
    ...patient,
    id_card: '**************1234',
    patient_phone: '138****0000',
    emergency_contact: '家属 B***',
    emergency_phone: '139****0000',
    medical_history: '演示病史摘要（身份信息已遮蔽）',
    allergies: '未记录',
    active_medication_count: 2,
    check_count: 8,
    exam_count: 5,
    pathology_count: 2,
    timeline_event_count: 18,
    medication_total: 4,
    pending_review_count: 1,
    pending_reminder_count: 2,
    ongoing_consultation_count: 1,
    abnormal_indicator_count: 2,
    abnormal_indicators: [indicators.blood_routine[1], indicators.tumor_markers[2]],
  })
  if (apiPath === '/medical/indicators/latest') {
    const category = url.searchParams.get('category') || 'blood_routine'
    return fulfillJson(route, { indicators: indicators[category] || [] })
  }
  if (apiPath === '/medical/indices/history') return fulfillJson(route, historyPayload(url.searchParams.get('index_id')))
  if (apiPath === '/medical/indices/categories') return fulfillJson(route, [
    { category_key: 'blood_routine', category_name: '血常规', icon: 'records-o' },
    { category_key: 'tumor_markers', category_name: '肿瘤标志物', icon: 'aim' },
  ])
  if (apiPath === '/medical/indices/compare') return fulfillJson(route, comparePayload)
  if (apiPath === '/medical/checks/query') return fulfillJson(route, [labReport])
  if (apiPath === '/medical/checks/101') return fulfillJson(route, labReport)
  if (apiPath === '/medical/checks/101/interpretation') return fulfillJson(route, { data: { interpretation: labReport.interpretation } })
  if (apiPath === '/medical/exams/201') return fulfillJson(route, examReport)
  if (apiPath === '/medical/exams/201/interpretation') return fulfillJson(route, { data: { interpretation: examReport.interpretation } })
  if (apiPath === '/medical/pathology/301') return fulfillJson(route, pathologyReport)
  if (apiPath === '/medical/pathology/301/interpretation') return fulfillJson(route, { data: { interpretation: pathologyReport.interpretation } })
  if (apiPath === '/consultation/conversations') return fulfillJson(route, { total: conversations.length, conversations })
  if (apiPath === '/consultation/agentteams/sessions/401') return fulfillJson(route, {
    conversation_id: 401,
    patient_id: 1,
    status: 'completed',
    embed_url: `${baseURL}/agentteams-demo`,
  })
  if (apiPath === '/knowledge/categories') return fulfillJson(route, knowledgeCategories)
  if (apiPath === '/knowledge/documents') return fulfillJson(route, { documents: knowledgeDocuments, pagination: { page: 1, total: knowledgeDocuments.length, has_next: false } })

  return fulfillJson(route, request.method() === 'GET' ? {} : { success: true })
}

function addDemoBadge(page) {
  return page.evaluate(() => {
    const old = document.getElementById('public-demo-badge')
    if (old) old.remove()
    const badge = document.createElement('div')
    badge.id = 'public-demo-badge'
    badge.textContent = '演示数据 · 已脱敏'
    Object.assign(badge.style, {
      position: 'fixed',
      right: '18px',
      bottom: '18px',
      zIndex: '99999',
      padding: '8px 13px',
      borderRadius: '999px',
      background: 'rgba(15, 78, 99, .88)',
      color: '#fff',
      font: '600 12px/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      letterSpacing: '.04em',
      boxShadow: '0 6px 18px rgba(15, 78, 99, .22)',
      pointerEvents: 'none',
    })
    document.body.appendChild(badge)
  })
}

async function preparePage(context, viewport) {
  const page = await context.newPage()
  await page.setViewportSize(viewport)
  const browserErrors = []
  page.on('pageerror', error => browserErrors.push(error.message))
  await page.route('**/*', mockApi)
  await page.addInitScript(() => {
    localStorage.setItem('token', 'public-demo-token')
    localStorage.setItem('refreshToken', 'public-demo-refresh')
    localStorage.setItem('currentPatientId', '1')
    localStorage.setItem('onboarding_completed', '1')
    localStorage.setItem('sidebar-collapsed', 'false')
  })
  return { page, browserErrors }
}

async function waitForStable(page) {
  await page.waitForLoadState('domcontentloaded')
  await page.waitForTimeout(1100)
  await page.evaluate(() => document.fonts?.ready)
  await addDemoBadge(page)
}

async function save(page, filename) {
  const docsPath = path.join(docsOutput, filename)
  const websitePath = path.join(websiteOutput, filename)
  await page.screenshot({ path: docsPath, type: 'png', animations: 'disabled' })
  await copyFile(docsPath, websitePath)
  process.stdout.write(`captured ${filename}\n`)
}

async function assertPublicPage(page, browserErrors, filename) {
  const text = await page.locator('body').innerText()
  const forbidden = ['身份证号：', '13800000000', '13900000000', '界面回归患者', '报告患者']
  for (const token of forbidden) {
    if (text.includes(token)) throw new Error(`${filename} contains forbidden public token: ${token}`)
  }
  const importantErrors = browserErrors.filter(message => !message.includes('ResizeObserver'))
  if (importantErrors.length) throw new Error(`${filename} browser errors: ${importantErrors.join(' | ')}`)
}

async function captureScenario(context, scenario, viewport) {
  const { page, browserErrors } = await preparePage(context, viewport)
  try {
    await page.goto(`${baseURL}${scenario.url}`, { waitUntil: 'domcontentloaded' })
    await waitForStable(page)
    if (scenario.action) await scenario.action(page)
    await addDemoBadge(page)
    await assertPublicPage(page, browserErrors, scenario.filename)
    await save(page, scenario.filename)
  } finally {
    await page.close()
  }
}

const encodedIndexes = encodeURIComponent(JSON.stringify(compareIndexes))
const desktopScenarios = [
  { filename: 'desktop-home-indicators-list.png', url: '/home/main' },
  { filename: 'desktop-home-indicators-chart.png', url: '/home/main', action: async page => {
    await page.getByText('图表', { exact: true }).last().click()
    await page.waitForTimeout(900)
    await page.locator('.indicator-section').scrollIntoViewIfNeeded()
    await page.waitForTimeout(300)
  } },
  { filename: 'desktop-lab-report.png', url: '/home/report/101' },
  { filename: 'desktop-exam-report.png', url: '/home/exam-report/201' },
  { filename: 'desktop-pathology-report.png', url: '/home/pathology-report/301' },
  { filename: 'desktop-indicator-comparison-table.png', url: `/home/indicator/history?compare_mode=1&indexes=${encodedIndexes}` },
  { filename: 'desktop-indicator-comparison-chart.png', url: `/home/indicator/history?compare_mode=1&indexes=${encodedIndexes}`, action: async page => {
    await page.getByText('趋势图表', { exact: true }).last().click()
    await page.waitForTimeout(900)
  } },
  { filename: 'desktop-consultation-list.png', url: '/home/consultation' },
  { filename: 'desktop-consultation-room.png', url: '/home/consultation/401?patient_id=1', action: async page => {
    await page.locator('iframe').waitFor({ state: 'visible' })
    await page.waitForTimeout(500)
  } },
  { filename: 'desktop-knowledge-base.png', url: '/home/knowledge' },
]

const mobileScenarios = [
  { filename: 'mobile-home.png', url: '/home/main' },
  { filename: 'mobile-lab-report.png', url: '/home/report/101' },
  { filename: 'mobile-indicator-comparison.png', url: `/home/indicator/history?compare_mode=1&indexes=${encodedIndexes}`, action: async page => {
    await page.getByText('趋势图表', { exact: true }).last().click()
    await page.waitForTimeout(900)
  } },
  { filename: 'mobile-consultation.png', url: '/home/consultation' },
  { filename: 'mobile-knowledge-base.png', url: '/home/knowledge' },
]

const browser = await chromium.launch({ headless: true })
try {
  const context = await browser.newContext({ colorScheme: 'light', locale: 'zh-CN', deviceScaleFactor: 1 })
  for (const scenario of desktopScenarios) {
    await captureScenario(context, scenario, { width: 1600, height: 1000 })
  }
  for (const scenario of mobileScenarios) {
    await captureScenario(context, scenario, { width: 390, height: 844 })
  }
  await context.close()
} finally {
  await browser.close()
}
