// Large graph views of the real EAKWP knowledge base for Chapter 4, exported with
// Neo4j Browser's own "Download as PNG" (the graph canvas is enlarged to 1350 px tall).
//   NEO4J_PASSWORD=... node docs/thesis/submission/tools/neo4j_capture/capture_kb_graphs.cjs <out_dir> [name...]
// Every query reads only labels/relationships written by ai-service/app/knowledge_graph/cypher/*.cypher.
const path = require('path')
const { chromium } = require(path.resolve(__dirname, '../../../../../frontend/node_modules/playwright-core'))

const OUT = process.argv[2]
const ONLY = process.argv.slice(3)
const PASSWORD = process.env.NEO4J_PASSWORD

// caption property per label (Neo4j Browser "Customize Style")
const CAPTIONS = { KnowledgeBase: 'kb_id', Document: 'title', Chunk: 'chunk_index', Entity: 'name', Claim: 'value' }

const SHOTS = [
  { name: 'neo4j_g1_kb_toan_canh',
    q: "MATCH p=(:KnowledgeBase)-[:HAS_DOCUMENT]->(:Document) RETURN p " +
       "UNION MATCH p=(:KnowledgeBase)-[:MERGED_INTO]->(:KnowledgeBase) RETURN p" },
  { name: 'neo4j_g2_mang_thuc_the',
    q: "MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity) WHERE r.weight >= 6 " +
       "AND NOT a.type IN ['moc_thoi_gian','dieu_khoan'] AND NOT b.type IN ['moc_thoi_gian','dieu_khoan'] RETURN a, r, b" },
  { name: 'neo4j_g3_hub_hdqt',
    q: "MATCH p1=(e:Entity {name:'Hội đồng Quản trị'})-[r:RELATES_TO]-(n:Entity) WITH p1, n, r ORDER BY r.weight DESC LIMIT 25 " +
       "MATCH p2=(:Document)-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(n) WITH p1, n, collect(p2)[0..2] AS ps UNWIND ps AS p2 RETURN p1, p2" },
  { name: 'neo4j_g4_dan_chieu_dieu',
    q: "MATCH p=(d:Document)-[:HAS_CHUNK]->(:Chunk)-[:REFERENCES]->(:Chunk) " +
       "WHERE d.doc_id IN ['84202bc4-4a22-46fa-8e7c-2ba11e857b68'] OR d.title = 'Dieu le cong ty 2025' RETURN p " +
       "UNION MATCH (d:Document)-[:HAS_CHUNK]->(a:Chunk)-[:REFERENCES]->(:Chunk) " +
       "WHERE d.doc_id IN ['84202bc4-4a22-46fa-8e7c-2ba11e857b68'] OR d.title = 'Dieu le cong ty 2025' " +
       "MATCH p=(a)-[:MENTIONS]->(:Entity {type:'dieu_khoan'}) RETURN p" },
  { name: 'neo4j_g5_phien_ban',
    q: "MATCH p=(:Document)-[:NEW_VERSION_OF|DUPLICATE_OF|SIMILAR_TO]->(:Document) RETURN p " +
       "UNION MATCH p=(:KnowledgeBase {kb_id:'KB'})-[:HAS_DOCUMENT]->(:Document) RETURN p" },
  { name: 'neo4j_g6_khang_dinh_von',
    q: "MATCH p=(:Document)-[:HAS_CHUNK]->(:Chunk)-[:ASSERTS]->(:Claim {attribute:'Vốn điều lệ'}) RETURN p " +
       "UNION MATCH p=(:Claim {attribute:'Vốn điều lệ'})-[:CONFLICTS_WITH]->(:Claim) RETURN p" },
  { name: 'neo4j_g7_hop_nhat_thuc_the',
    q: "MATCH p=(:Entity)-[:SAME_AS|POSSIBLY_SAME_AS]->(:Entity) RETURN p " +
       "UNION MATCH (e:Entity) WHERE EXISTS { (e)-[:SAME_AS|POSSIBLY_SAME_AS]-() } " +
       "MATCH p=(:Document)-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(e) WITH e, collect(p)[0..3] AS ps UNWIND ps AS p RETURN p" },
  { name: 'neo4j_g8_kb2_web',
    q: "MATCH p=(:KnowledgeBase {kb_id:'KB2'})-[:HAS_DOCUMENT]->(:Document)-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(:Entity) RETURN p" },
  { name: 'neo4j_g9_tai_lieu_hdqt',
    q: "MATCH p=(d:Document {doc_id:'1cb5c2d8-7a56-46b0-b65f-4c3650a27fb7'})-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity) " +
       "WHERE c.chunk_index < 24 AND NOT e.type IN ['moc_thoi_gian'] RETURN p" },
]

async function run(page, query, wait = 7000) {
  const editor = page.locator('.cm-content').first()
  await editor.click()
  await page.keyboard.press('Control+A')
  await page.keyboard.press('Delete')
  await page.keyboard.insertText(query)
  await page.keyboard.press('Control+Enter')
  await page.waitForTimeout(wait)
}

async function styleLabels(page) {
  for (const [label, caption] of Object.entries(CAPTIONS)) {
    const chip = page.getByText(new RegExp(`^${label} \\(\\d+\\)$`)).first()
    if (!(await chip.count())) continue
    await chip.click()
    await page.waitForTimeout(600)
    const btn = page.getByText(caption, { exact: true }).last()
    if (await btn.count()) await btn.click()
    await page.waitForTimeout(400)
    // Bigger nodes -> bigger captions in the exported PNG. The size choices are a row
    // of circles under the "Size:" label; the 5th one (about 106 px to the right).
    const sizeLabel = page.getByText('Size:', { exact: true }).last()
    const box = await sizeLabel.boundingBox()
    if (box) { await page.mouse.click(box.x + 106, box.y + box.height + 18); await page.waitForTimeout(400) }
    await page.keyboard.press('Escape')
    await page.waitForTimeout(300)
  }
}

;(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true })
  const ctx = await browser.newContext({ viewport: { width: 2400, height: 1700 }, deviceScaleFactor: 2, acceptDownloads: true })
  for (const shot of SHOTS) {
    if (ONLY.length && !ONLY.includes(shot.name)) continue
    // A fresh page per view: Browser tooltips and frames from the previous view
    // otherwise cover the buttons. Label styles persist in the context's storage.
    const page = await ctx.newPage()
    await page.goto('http://localhost:7474/browser/', { waitUntil: 'domcontentloaded', timeout: 60000 })
    if (await page.locator('input[type=password]').count() || await page.waitForSelector('input[type=password]', { timeout: 8000 }).catch(() => null)) {
      await page.fill('input[type=password]', PASSWORD)
      await page.press('input[type=password]', 'Enter')
    }
    await page.waitForTimeout(5000)
    if (await page.getByText('Dismiss', { exact: true }).count()) await page.getByText('Dismiss', { exact: true }).first().click()
    const col = page.getByTitle('Collapse Sidebar'); if (await col.count()) await col.first().click()
    for (let i = 0; i < 4; i++) { const rm = page.getByLabel('Remove frame'); if (!(await rm.count())) break; await rm.first().click({ force: true }); await page.waitForTimeout(250) }
    await run(page, shot.q)
    await styleLabels(page)
    // Run again so the force layout is computed with the new node sizes.
    for (let i = 0; i < 3; i++) { const rm = page.getByLabel('Remove frame'); if (!(await rm.count())) break; await rm.first().click({ force: true }); await page.waitForTimeout(250) }
    await run(page, shot.q)
    await page.evaluate(() => {
      for (const el of document.querySelectorAll('div')) {
        const r = el.getBoundingClientRect()
        if (Math.abs(r.height - 500) < 2 && r.width > 900) { el.style.height = '1350px'; el.style.maxHeight = 'none' }
      }
      window.dispatchEvent(new Event('resize'))
    })
    await page.waitForTimeout(2500)
    const fit = page.getByLabel('Zoom to fit').first(); if (await fit.count()) { await fit.click(); await page.waitForTimeout(3000) }
    const dl = page.getByLabel('Download as PNG').first()
    await page.mouse.move(5, 5); await page.keyboard.press('Escape'); await page.waitForTimeout(400)
    const [download] = await Promise.all([page.waitForEvent('download', { timeout: 20000 }).catch(() => null), dl.click({ force: true })])
    if (download) { await download.saveAs(path.join(OUT, `${shot.name}.png`)); console.log('captured', shot.name) }
    else console.log('FAILED', shot.name)
    const counts = await page.evaluate(() => document.body.innerText.match(/Nodes \(\d+\)|Relationships \(\d+\)/g))
    console.log('   ', JSON.stringify(counts))
    await page.close()
  }
  await browser.close()
})()
