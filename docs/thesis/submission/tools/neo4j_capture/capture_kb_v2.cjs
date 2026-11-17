// Capture Neo4j Browser views for Chapter 4 (KB after integration processing).
//   node docs/thesis/submission/tools/neo4j_capture/capture_kb_v2.cjs <out_dir>
// Needs Neo4j on localhost:7474 and NEO4J_PASSWORD in the environment.
const path = require('path')
const { chromium } = require(path.resolve(__dirname, '../../../../../frontend/node_modules/playwright-core'))

const OUT = process.argv[2]
const PASSWORD = process.env.NEO4J_PASSWORD

const SHOTS = [
  { name: 'neo4j_kb_tong_quan', view: 'table',
    q: "MATCH (kb:KnowledgeBase)-[:HAS_DOCUMENT]->(d:Document) OPTIONAL MATCH (kb)-[:MERGED_INTO]->(t) " +
       "RETURN kb.kb_id AS kho, t.kb_id AS gop_vao, count(DISTINCT d) AS tai_lieu, " +
       "sum(CASE WHEN coalesce(d.is_current, true) AND d.duplicate_of IS NULL THEN 1 ELSE 0 END) AS dang_dung, " +
       "COUNT { (kb)-[:HAS_DOCUMENT]->(:Document)-[:HAS_CHUNK]->() } AS chunk ORDER BY kho" },
  { name: 'neo4j_schema_v2', view: 'graph', q: 'CALL db.schema.visualization()' },
  { name: 'neo4j_phien_ban_trung_lap', view: 'table',
    q: "MATCH (a:Document)-[r:NEW_VERSION_OF|DUPLICATE_OF|SIMILAR_TO]->(b:Document) " +
       "RETURN type(r) AS quan_he, a.title AS tai_lieu, b.title AS tro_toi, round(r.overlap, 3) AS do_chong_lan, " +
       "a.is_current AS a_hien_hanh ORDER BY quan_he, do_chong_lan DESC" },
  { name: 'neo4j_von_dieu_le', view: 'table',
    q: "MATCH (x:Claim {attribute: 'Vốn điều lệ'})<-[:ASSERTS]-(:Chunk)<-[:HAS_CHUNK]-(d:Document) " +
       "OPTIONAL MATCH (x)-[cf:CONFLICTS_WITH]->(:Claim) " +
       "RETURN d.title AS nguon, d.effective_date AS hieu_luc, x.value AS gia_tri, x.status AS trang_thai, " +
       "x.flags AS canh_bao, cf.reason AS ly_do ORDER BY hieu_luc" },
  { name: 'neo4j_hop_nhat_mo', view: 'table',
    q: "MATCH (a:Entity)-[r:SAME_AS|POSSIBLY_SAME_AS]->(b:Entity) " +
       "RETURN type(r) AS quan_he, round(r.score, 3) AS do_giong, round(r.membership, 2) AS muc_thuoc, " +
       "a.name AS thuc_the_a, b.name AS thuc_the_b ORDER BY do_giong DESC" },
  { name: 'neo4j_do_tin_cay', view: 'table',
    q: "MATCH (:Chunk)-[m:MENTIONS]->(e:Entity) RETURN m.method AS phuong_phap, " +
       "round(avg(m.confidence), 2) AS do_tin_cay, count(*) AS so_canh, count(DISTINCT e) AS so_thuc_the " +
       "ORDER BY so_canh DESC" },
]

// :style is not applied by this Browser version; graph shots keep default colours.
const GRASS = `:style
node { diameter: 46px; color: #7ACFF5; border-color: #3C8DBC; border-width: 2px; text-color-internal: #000000; font-size: 10px; caption: "{name}"; }
relationship { color: #6B7280; shaft-width: 2px; font-size: 9px; padding: 3px; text-color-external: #000000; text-color-internal: #FFFFFF; caption: "<type>"; }
node.KnowledgeBase { diameter: 80px; color: #F79767; caption: "{kb_id}"; font-size: 14px; }
node.Document { diameter: 70px; color: #7ACFF5; caption: "{title}"; font-size: 10px; }
node.Entity { diameter: 60px; color: #C7E9B4; caption: "{name}"; }
node.Chunk { diameter: 40px; color: #FFE08A; caption: "{chunk_index}"; }`

async function run(page, query, wait = 6000) {
  const editor = page.locator('.cm-content').first()
  await editor.click()
  await page.keyboard.press('Control+A')
  await page.keyboard.press('Delete')
  await page.keyboard.insertText(query)
  await page.keyboard.press('Control+Enter')
  await page.waitForTimeout(wait)
  await page.keyboard.press('Escape')
}

;(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true })
  const page = await browser.newPage({ viewport: { width: 1600, height: 1250 }, deviceScaleFactor: Number(process.env.SCALE || 1.25) })
  await page.goto('http://localhost:7474/browser/', { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForSelector('input[type=password]', { timeout: 60000 })
  await page.fill('input[type=password]', PASSWORD)
  await page.press('input[type=password]', 'Enter')
  await page.waitForTimeout(5000)
  if (await page.locator('text=Dismiss').count()) await page.locator('text=Dismiss').first().click()

  await run(page, GRASS, 1500)
  for (const shot of SHOTS) {
    await run(page, ':clear', 1500)
    await run(page, shot.q)
    if (shot.view === 'table') {
      await page.getByText('Table', { exact: true }).first().click()
      await page.waitForTimeout(1500)
    } else {
      const fit = page.getByRole('button', { name: 'Zoom to fit' }).first()
      if (await fit.count()) { await fit.click(); await page.waitForTimeout(1800) }
    }
    await page.mouse.move(250, 900)
    // Results pane only: drop the sidebar and the editor bar.
    await page.screenshot({ path: path.join(OUT, `${shot.name}.png`), clip: { x: 412, y: 125, width: 1180, height: 660 } })
    console.log('captured', shot.name)
  }
  await browser.close()
})()
