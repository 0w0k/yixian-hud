// 常驻 yisim 服务:bundle 只加载一次,然后按行读 stdin(每行一个请求 JSON,与
// yisim_marginal.js 的 totalOnly 入参同形),每个请求算一次、输出一行结果 JSON。
//
// 取代"每次 spawn node 重 eval 整份 yisim.bundle"的旧法 —— bundle 解析只发生一次,
// 之后常驻进程低占用待命;HUD 关闭伤害显示时由 Python 端 kill 本进程 → 释放内存。
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const BUNDLE = path.join(__dirname, '..', '..', 'web', 'yisim.bundle.js');
(0, eval)(fs.readFileSync(BUNDLE, 'utf8'));
const Y = globalThis.yisim;

function toSlot(c) {
  if (!c || !c.name) return null;
  const isDream = typeof c.name === 'string' && c.name.startsWith('梦');
  return isDream ? { name: c.name, level: c.level, phase: c.level, isDream: true }
                 : { name: c.name, level: c.level, isDream: false };
}

function buildOpts(j, deckSlots) {
  const opts = {
    mode: 'solo',
    rollMode: j.rollMode || 'average',
    deckSlots,
    maxTurns: 64,
    talents: j.talents || [],
    playerState: j.playerState || null,
    plantStacks: j.plantStacks || null,
  };
  const o = j.opponent;
  if (o && Array.isArray(o.board) && o.board.some(x => x)) {
    const oDeck = o.deckSlots || o.board.length || deckSlots;
    opts.mode = 'matchup';
    opts.opponentSlots = o.board.slice(0, oDeck).map(toSlot);
    opts.opponentState = o.playerState || null;
    opts.opponentTalents = o.talents || [];
  }
  return opts;
}

async function handle(j) {
  const board = j.board || [];
  const deckSlots = j.deckSlots || board.length || 8;
  const slots = board.map(toSlot);
  const opts = buildOpts(j, deckSlots);
  if (Y.ready) { try { await Promise.resolve(Y.ready); } catch (e) {} }
  const r = await Promise.resolve(Y.simulate(slots, opts));
  const cum = (r && r.cumulativeDamage) ? r.cumulativeDamage.slice(0, 8).map(x => Math.round(x)) : [];
  const taken = (r && r.cumulativeTaken) ? r.cumulativeTaken.slice(0, 8).map(x => Math.round(x)) : [];
  const myHp = (r && r.myHpSeries) ? r.myHpSeries.slice(0, 8).map(x => Math.round(x)) : [];
  const oppHp = (r && r.oppHpSeries) ? r.oppHpSeries.slice(0, 8).map(x => Math.round(x)) : [];
  const full = (r && r.first8Turns != null) ? Math.round(r.first8Turns)
             : (cum.length ? cum[cum.length - 1] : 0);
  return {
    full, cumulative: cum, cumulativeTaken: taken,
    myHpSeries: myHp, oppHpSeries: oppHp, mode: opts.mode,
    outcome: r && r.outcome, endTurn: r && r.endTurn, deterministic: r && r.deterministic,
  };
}

// 串行处理:一行请求 → 一行响应,顺序对应(Python 端也是一问一答)。
let queue = Promise.resolve();
const rl = readline.createInterface({ input: process.stdin });
rl.on('line', (line) => {
  line = (line || '').trim();
  if (!line) return;
  queue = queue.then(async () => {
    let out;
    try { out = await handle(JSON.parse(line)); }
    catch (e) { out = { error: String(e && e.message) }; }
    process.stdout.write(JSON.stringify(out) + '\n');
  });
});
rl.on('close', () => process.exit(0));
