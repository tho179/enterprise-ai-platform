// Screenshots of the running web app for Chapter 6.
//   node docs/thesis/submission/tools/capture_ui.cjs <out_dir> [base_url]
// Needs the full stack up (docker compose up -d) and the demo accounts.
const path = require('path')
const { chromium } = require(path.resolve(__dirname, '../../../../frontend/node_modules/playwright-core'))

const OUT = process.argv[2]
const BASE = process.argv[3] || 'http://localhost:3000'
const ANSWER_TIMEOUT = 240000

async function login(page, email) {
  await page.goto(`${BASE}/login`)
  await page.waitForTimeout(1500)
  await page.screenshot({ path: path.join(OUT, '01_dang_nhap.png') })
  // Demo-account shortcut buttons exist only in mock mode; type the credentials.
  await page.getByPlaceholder('ten.ban@congty.vn').fill(email)
  await page.getByPlaceholder('Nhập mật khẩu').fill(process.env.DEMO_PASSWORD || 'Demo@123')
  await page.locator('button[type="submit"]').click()
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 30000 })
  await page.waitForTimeout(2500)
}

async function ask(page, question, shot, { openTrace = true } = {}) {
  await page.goto(`${BASE}/chat`)
  await page.waitForTimeout(2000)
  // One conversation per screenshot, so earlier answers do not crowd the view.
  await page.getByText('Cuộc trò chuyện mới').first().click()
  await page.waitForTimeout(800)
  const before = await page.locator('.chat-answer').count()
  const box = page.locator('textarea').first()
  await box.fill(question)
  await box.press('Enter')
  await page.waitForFunction(
    (n) => document.querySelectorAll('.chat-answer').length > n,
    before,
    { timeout: ANSWER_TIMEOUT },
  )
  await page.waitForTimeout(1500)
  if (openTrace) {
    const trace = page.locator('.agent-trace summary').last()
    if (await trace.count()) {
      await trace.click()
      await page.locator('.agent-trace').last().scrollIntoViewIfNeeded()
    }
  }
  await page.waitForTimeout(800)
  await page.screenshot({ path: path.join(OUT, shot) })
  console.log('captured', shot)
}

;(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.25 })
  page.setDefaultTimeout(60000)

  await login(page, 'admin@congty.vn')
  for (const [url, shot] of [
    ['/documents', '02_kho_tai_lieu.png'],
    ['/documents/upload', '03_tai_len.png'],
    ['/search', '04_tim_kiem.png'],
    ['/users', '05_nguoi_dung.png'],
    ['/dashboard', '06_tong_quan.png'],
  ]) {
    await page.goto(`${BASE}${url}`)
    await page.waitForTimeout(3000)
    await page.screenshot({ path: path.join(OUT, shot) })
    console.log('captured', shot)
  }

  await ask(page, 'Hội đồng Quản trị gồm bao nhiêu thành viên?', '07_hoi_dap_trich_dan.png')
  // Open the first citation: the real PDF page with the evidence highlighted.
  const source = page.locator('.chat-source-button').last()
  if (await source.count()) {
    await source.click()
    await page.waitForTimeout(1500)
    const card = page.locator('.citation-card').first()
    if (await card.count()) {
      await card.click()
      await page.waitForTimeout(8000)    // PDF render
      // The headless PDF viewer does not honour the scroll target; scroll by hand
      // so the highlighted evidence (lower half of the page) is in view.
      await page.mouse.move(1150, 650)
      for (let i = 0; i < 2; i += 1) {
        await page.mouse.wheel(0, 180)
        await page.waitForTimeout(400)
      }
      await page.waitForTimeout(1500)
    }
    await page.screenshot({ path: path.join(OUT, '08_xem_nguon_pdf.png') })
    console.log('captured 08_xem_nguon_pdf.png')
    await page.keyboard.press('Escape')
  }
  await ask(page, 'Vốn điều lệ hiện nay của công ty là bao nhiêu?', '09_tac_tu_von_dieu_le.png')
  await ask(page, 'Giá vàng hôm nay là bao nhiêu?', '10_tu_choi.png')
  await browser.close()
})()
