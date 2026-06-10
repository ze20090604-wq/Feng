from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHELL_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from studio_shell.page_shell import page_shell
from studio_shell.shell_ui import format_extra_context, inject_style

PAGE_NAME = "Tetris"

st.set_page_config(page_title="俄囉斯方塊（Tetris）", page_icon="🧩", layout="wide")
inject_style()

GAME_HTML = r"""
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8" />
<style>
  :root {
    color-scheme: dark;
    --bg: #0f172a;
    --panel: #111827;
    --line: #334155;
    --text: #e5e7eb;
    --muted: #94a3b8;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: #020617; color: var(--text); font-family: Arial, "Microsoft JhengHei", sans-serif; }
  .shell { display: grid; grid-template-columns: 1fr; gap: 18px; padding: 4px; }
  .game-area { display: grid; grid-template-columns: minmax(420px, 1.15fr) minmax(280px, 1fr); gap: 18px; align-items: start; }
  .board-wrap, .side { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
  .board-wrap { min-height: 680px; }
  canvas { display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; outline: none; }
  h2 { margin: 0 0 10px; font-size: 22px; line-height: 1.25; }
  .hint { color: var(--muted); line-height: 1.5; margin: 8px 0 14px; }
  .board-wrap { display: flex; justify-content: flex-start; align-items: flex-start; }
  .board-wrap canvas { touch-action: manipulation; }
  .stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin: 12px 0; }
  .stat, .ai-panel, .leaderboard { border: 1px solid var(--line); border-radius: 8px; padding: 10px; background: rgba(15, 23, 42, 0.75); }
  .label { color: var(--muted); font-size: 12px; margin-bottom: 4px; }
  .value { font-size: 24px; font-weight: 700; }
  .preview-row { display: flex; gap: 14px; align-items: flex-start; margin-top: 10px; }
  .ai-panel { margin-top: 14px; }
  .ai-line { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin: 8px 0; }
  input[type="range"] { width: 100%; }
  .controls { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 14px; }
  button { min-height: 38px; border: 1px solid var(--line); border-radius: 7px; background: #1f2937; color: var(--text); font-size: 14px; cursor: pointer; }
  button:hover { background: #334155; }
  .wide { grid-column: span 3; }
  .game-over { display: none; margin-top: 12px; padding: 10px; border-radius: 8px; background: #7f1d1d; color: #fee2e2; font-weight: 700; }
  .game-over.show { display: block; }
  .leaderboard { margin-top: 14px; }
  .leaderboard ol { margin: 8px 0 0; padding-left: 24px; max-height: 180px; overflow-y: auto; scrollbar-width: thin; }
  .leaderboard li { color: var(--text); margin: 4px 0; }
  @media (max-width: 760px) { .game-area { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="shell">
  <div class="game-area">
    <div class="board-wrap"><canvas id="board" width="300" height="600" tabindex="0" aria-label="Tetris board"></canvas></div>
    <aside class="side">
      <p class="hint">點一下棋盤後可以用鍵盤操作。A/← 左移，D/→ 右移，S/↓ 下移，W/↑ 旋轉，空白鍵直落，F 暫存方塊。</p>
      <div class="stats">
        <div class="stat"><div class="label">分數</div><div class="value" id="score">0</div></div>
        <div class="stat"><div class="label">消行</div><div class="value" id="lines">0</div></div>
        <div class="stat"><div class="label">等級</div><div class="value" id="level">1</div></div>
        <div class="stat"><div class="label">狀態</div><div class="value" id="status">進行中</div></div>
      </div>
      <div class="preview-row"><div><div class="label">暫存 F</div><canvas id="hold" width="96" height="96"></canvas></div><div><div class="label">下一個方塊</div><canvas id="next" width="96" height="96"></canvas></div></div>
      <div class="ai-panel"><div class="ai-line"><label for="aiMode">AI 模式</label><input id="aiMode" type="checkbox" /></div><div class="label">AI 放方塊速度：<span id="aiSpeedValue">3</span>x</div><input id="aiSpeed" type="range" min="1" max="5" step="1" value="3" /></div>
      <div class="controls"><button id="left">左移</button><button id="rotate">旋轉</button><button id="right">右移</button><button id="down">下移</button><button id="holdButton">暫存 F</button><button id="drop">直落</button><button id="pause">暫停 P</button><button class="wide" id="restart">重新開始</button></div>
      <div class="game-over" id="gameOver">遊戲結束，按「重新開始」再玩一次。</div>
      <div class="leaderboard"><div class="label">本機紀錄</div><ol id="leaderboardList"></ol></div>
    </aside>
  </div>
</div>
<script>
const COLS = 10;
const ROWS = 20;
const CELL = 30;
const PREVIEW = 24;
const EMPTY = "";
const COLORS = { I:"#22d3ee", O:"#facc15", T:"#c084fc", L:"#fb923c", J:"#60a5fa", S:"#4ade80", Z:"#f87171" };
const SHAPES = {
  I: [[[0,1],[1,1],[2,1],[3,1]],[[2,0],[2,1],[2,2],[2,3]]],
  O: [[[1,0],[2,0],[1,1],[2,1]]],
  T: [[[1,0],[0,1],[1,1],[2,1]],[[1,0],[1,1],[2,1],[1,2]],[[0,1],[1,1],[2,1],[1,2]],[[1,0],[0,1],[1,1],[1,2]]],
  L: [[[2,0],[0,1],[1,1],[2,1]],[[1,0],[1,1],[1,2],[2,2]],[[0,1],[1,1],[2,1],[0,2]],[[0,0],[1,0],[1,1],[1,2]]],
  J: [[[0,0],[0,1],[1,1],[2,1]],[[1,0],[2,0],[1,1],[1,2]],[[0,1],[1,1],[2,1],[2,2]],[[1,0],[1,1],[0,2],[1,2]]],
  S: [[[1,0],[2,0],[0,1],[1,1]],[[1,0],[1,1],[2,1],[2,2]]],
  Z: [[[0,0],[1,0],[1,1],[2,1]],[[2,0],[1,1],[2,1],[1,2]]]
};
const boardCanvas = document.getElementById("board");
const boardCtx = boardCanvas.getContext("2d");
const nextCanvas = document.getElementById("next");
const nextCtx = nextCanvas.getContext("2d");
const holdCanvas = document.getElementById("hold");
const holdCtx = holdCanvas.getContext("2d");
const scoreEl = document.getElementById("score");
const linesEl = document.getElementById("lines");
const levelEl = document.getElementById("level");
const statusEl = document.getElementById("status");
const gameOverEl = document.getElementById("gameOver");
const aiModeEl = document.getElementById("aiMode");
const aiSpeedEl = document.getElementById("aiSpeed");
const aiSpeedValueEl = document.getElementById("aiSpeedValue");
const leaderboardListEl = document.getElementById("leaderboardList");
const LEADERBOARD_KEY = "tetris-leaderboard-v1";
let board, piece, nextPiece, heldPieceKind, canHold, score, lines, level, gameOver, paused, dropTimer, aiTimer, aiTarget, scoreSaved;
function createEmptyBoard() { return Array.from({ length: ROWS }, () => Array(COLS).fill(EMPTY)); }
function createPiece(kind) { return { kind, x: 3, y: 0, rotation: 0 }; }
function createRandomPiece() { const keys = Object.keys(SHAPES); return createPiece(keys[Math.floor(Math.random() * keys.length)]); }
function getPieceCells(target) { return SHAPES[target.kind][target.rotation].map(([dx, dy]) => [target.x + dx, target.y + dy]); }
function isPositionLegal(target) { return getPieceCells(target).every(([x, y]) => x >= 0 && x < COLS && y >= 0 && y < ROWS && board[y][x] === EMPTY); }
function movePiece(dx, dy) { if (gameOver || paused) return false; const moved = { ...piece, x: piece.x + dx, y: piece.y + dy }; if (isPositionLegal(moved)) { piece = moved; draw(); return true; } if (dx === 0 && dy === 1) { fixPieceToBoard(); clearFullLines(); spawnNextPiece(); aiTarget = null; draw(); } return false; }
function rotatePiece() { if (gameOver || paused) return; const rotated = { ...piece, rotation: (piece.rotation + 1) % SHAPES[piece.kind].length }; for (const kick of [0, -1, 1, -2, 2]) { const candidate = { ...rotated, x: rotated.x + kick }; if (isPositionLegal(candidate)) { piece = candidate; aiTarget = null; draw(); return; } } }
function holdPiece() { if (gameOver || paused || !canHold) return; const currentKind = piece.kind; if (heldPieceKind === null) { heldPieceKind = currentKind; piece = nextPiece; nextPiece = createRandomPiece(); } else { piece = createPiece(heldPieceKind); heldPieceKind = currentKind; } piece.x = 3; piece.y = 0; piece.rotation = 0; canHold = false; aiTarget = null; if (!isPositionLegal(piece)) endGame(); draw(); }
function hardDrop() { if (gameOver || paused) return; let dropped = 0; while (movePiece(0, 1)) dropped += 1; score += dropped * 2; updateStats(); }
function fixPieceToBoard() { for (const [x, y] of getPieceCells(piece)) { if (y >= 0 && y < ROWS && x >= 0 && x < COLS) board[y][x] = piece.kind; } }
function clearFullLines() { const kept = board.filter(row => row.some(cell => cell === EMPTY)); const cleared = ROWS - kept.length; if (cleared > 0) { board = Array.from({ length: cleared }, () => Array(COLS).fill(EMPTY)).concat(kept); lines += cleared; score += { 1:100, 2:300, 3:500, 4:800 }[cleared]; level = 1 + Math.floor(lines / 10); resetDropTimer(); } }
function spawnNextPiece() { piece = nextPiece; piece.x = 3; piece.y = 0; piece.rotation = 0; nextPiece = createRandomPiece(); canHold = true; if (!isPositionLegal(piece)) endGame(); }
function endGame() { gameOver = true; statusEl.textContent = "結束"; gameOverEl.classList.add("show"); clearInterval(dropTimer); clearInterval(aiTimer); saveScore(); }
function drawCell(ctx, x, y, size, kind) { ctx.fillStyle = kind ? COLORS[kind] : "#111827"; ctx.fillRect(x * size, y * size, size, size); ctx.strokeStyle = "#334155"; ctx.lineWidth = 1; ctx.strokeRect(x * size + 0.5, y * size + 0.5, size - 1, size - 1); }
function drawBoard() { boardCtx.clearRect(0, 0, boardCanvas.width, boardCanvas.height); for (let y = 0; y < ROWS; y++) for (let x = 0; x < COLS; x++) drawCell(boardCtx, x, y, CELL, board[y][x]); for (const [x, y] of getPieceCells(piece)) if (y >= 0) drawCell(boardCtx, x, y, CELL, piece.kind); }
function drawPreview(ctx, kind) { ctx.clearRect(0, 0, 96, 96); for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) drawCell(ctx, x, y, PREVIEW, EMPTY); if (!kind) return; for (const [x, y] of SHAPES[kind][0]) drawCell(ctx, x, y, PREVIEW, kind); }
function updateStats() { scoreEl.textContent = String(score); linesEl.textContent = String(lines); levelEl.textContent = String(getEffectiveLevel()); statusEl.textContent = gameOver ? "結束" : paused ? "暫停" : "進行中"; }
function loadLeaderboard() { try { const parsed = JSON.parse(localStorage.getItem(LEADERBOARD_KEY) || "[]"); return Array.isArray(parsed) ? parsed : []; } catch { return []; } }
function saveScore() { if (scoreSaved || score <= 0) return; scoreSaved = true; const entry = { score, lines, level: getEffectiveLevel(), mode: aiModeEl.checked ? "AI" : "Manual", at: new Date().toLocaleString() }; const leaderboard = loadLeaderboard().concat(entry).sort((a, b) => b.score - a.score).slice(0, 5); localStorage.setItem(LEADERBOARD_KEY, JSON.stringify(leaderboard)); }
function renderLeaderboard() { const leaderboard = loadLeaderboard(); leaderboardListEl.innerHTML = ""; if (leaderboard.length === 0) { const emptyItem = document.createElement("li"); emptyItem.textContent = "尚無紀錄"; leaderboardListEl.appendChild(emptyItem); return; } for (const entry of leaderboard) { const item = document.createElement("li"); item.textContent = `${entry.score} pts / ${entry.lines} lines / Lv ${entry.level} / ${entry.mode}`; leaderboardListEl.appendChild(item); } }
function getEffectiveLevel() { return Math.max(1, Math.min(20, level + (aiModeEl.checked ? Number(aiSpeedEl.value) - 3 : 0))); }
function resetDropTimer() { clearInterval(dropTimer); dropTimer = setInterval(() => movePiece(0, 1), Math.max(80, 700 - getEffectiveLevel() * 50)); }
function draw() { drawBoard(); drawPreview(nextCtx, nextPiece?.kind); drawPreview(holdCtx, heldPieceKind); }
function startGame() { board = createEmptyBoard(); piece = createRandomPiece(); nextPiece = createRandomPiece(); heldPieceKind = null; canHold = true; score = 0; lines = 0; level = 1; gameOver = false; paused = false; aiTarget = null; scoreSaved = false; gameOverEl.classList.remove("show"); renderLeaderboard(); resetDropTimer(); updateStats(); draw(); }
function togglePause() { if (gameOver) return; paused = !paused; updateStats(); }
function handleKey(e) {
  if (e.key === " " || e.code === "Space" || e.key === "Spacebar") {
    e.preventDefault();
    hardDrop();
    return;
  }
  if (e.key === "ArrowLeft" || e.key === "a") movePiece(-1, 0);
  else if (e.key === "ArrowRight" || e.key === "d") movePiece(1, 0);
  else if (e.key === "ArrowDown" || e.key === "s") movePiece(0, 1);
  else if (e.key === "ArrowUp" || e.key === "w") rotatePiece();
  else if (e.key === "f") holdPiece();
  else if (e.key === "p") togglePause();
}
document.getElementById("left").onclick = () => movePiece(-1, 0);
document.getElementById("rotate").onclick = () => rotatePiece();
document.getElementById("right").onclick = () => movePiece(1, 0);
document.getElementById("down").onclick = () => movePiece(0, 1);
document.getElementById("holdButton").onclick = () => holdPiece();
document.getElementById("drop").onclick = () => hardDrop();
document.getElementById("pause").onclick = () => togglePause();
document.getElementById("restart").onclick = () => startGame();
aiModeEl.onchange = () => { updateStats(); resetDropTimer(); };
aiSpeedEl.oninput = () => { aiSpeedValueEl.textContent = aiSpeedEl.value; updateStats(); resetDropTimer(); };
window.addEventListener("keydown", handleKey);
startGame();
</script>
</body>
</html>
"""


def render_main() -> str:
    st.components.v1.html(GAME_HTML, height=1120, scrolling=True)
    return format_extra_context(PAGE_NAME)


page_shell(
    "俄囉斯方塊（Tetris）",
    "完整 Tetris 小遊戲頁面。",
    render_main,
    page_name=PAGE_NAME,
)
