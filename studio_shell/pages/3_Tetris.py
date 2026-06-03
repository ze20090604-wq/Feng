from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


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
  body {
    margin: 0;
    background: #020617;
    color: var(--text);
    font-family: Arial, "Microsoft JhengHei", sans-serif;
  }
  .shell {
    display: grid;
    grid-template-columns: minmax(320px, max-content) minmax(280px, 1fr);
    gap: 18px;
    align-items: start;
    padding: 4px;
  }
  .board-wrap, .side {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 14px;
  }
  canvas {
    display: block;
    background: var(--bg);
    border: 1px solid var(--line);
    border-radius: 6px;
    outline: none;
  }
  h2 {
    margin: 0 0 10px;
    font-size: 22px;
    line-height: 1.25;
  }
  .hint {
    color: var(--muted);
    line-height: 1.5;
    margin: 8px 0 14px;
  }
  .stats {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin: 12px 0;
  }
  .stat, .ai-panel, .leaderboard {
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 10px;
    background: rgba(15, 23, 42, 0.75);
  }
  .label {
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 4px;
  }
  .value {
    font-size: 24px;
    font-weight: 700;
  }
  .preview-row {
    display: flex;
    gap: 14px;
    align-items: flex-start;
    margin-top: 10px;
  }
  .ai-panel {
    margin-top: 14px;
  }
  .ai-line {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin: 8px 0;
  }
  input[type="range"] {
    width: 100%;
  }
  .controls {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 14px;
  }
  button {
    min-height: 38px;
    border: 1px solid var(--line);
    border-radius: 7px;
    background: #1f2937;
    color: var(--text);
    font-size: 14px;
    cursor: pointer;
  }
  button:hover { background: #334155; }
  .wide { grid-column: span 3; }
  .game-over {
    display: none;
    margin-top: 12px;
    padding: 10px;
    border-radius: 8px;
    background: #7f1d1d;
    color: #fee2e2;
    font-weight: 700;
  }
  .game-over.show { display: block; }
  .leaderboard {
    margin-top: 14px;
  }
  .leaderboard ol {
    margin: 8px 0 0;
    padding-left: 24px;
  }
  .leaderboard li {
    color: var(--text);
    margin: 4px 0;
  }
  @media (max-width: 760px) {
    .shell { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="shell">
  <div class="board-wrap">
    <canvas id="board" width="300" height="600" tabindex="0" aria-label="Tetris board"></canvas>
  </div>
  <aside class="side">
    <h2>&#20420;&#22217;&#26031;&#26041;&#22602;</h2>
    <p class="hint">&#40670;&#19968;&#19979;&#26827;&#30436;&#24460;&#21487;&#20197;&#29992;&#37749;&#30436;&#25805;&#20316;&#12290;A/&#8592; &#24038;&#31227;&#65292;D/&#8594; &#21491;&#31227;&#65292;S/&#8595; &#19979;&#31227;&#65292;W/&#8593; &#26059;&#36681;&#65292;&#31354;&#30333;&#37749;&#30452;&#33853;&#65292;F &#26283;&#23384;&#26041;&#22602;&#12290;</p>
    <div class="stats">
      <div class="stat"><div class="label">&#20998;&#25976;</div><div class="value" id="score">0</div></div>
      <div class="stat"><div class="label">&#28040;&#34892;</div><div class="value" id="lines">0</div></div>
      <div class="stat"><div class="label">&#31561;&#32026;</div><div class="value" id="level">1</div></div>
      <div class="stat"><div class="label">&#29376;&#24907;</div><div class="value" id="status">&#36914;&#34892;&#20013;</div></div>
    </div>
    <div class="preview-row">
      <div>
        <div class="label">&#26283;&#23384; F</div>
        <canvas id="hold" width="96" height="96"></canvas>
      </div>
      <div>
        <div class="label">&#19979;&#19968;&#20491;&#26041;&#22602;</div>
        <canvas id="next" width="96" height="96"></canvas>
      </div>
    </div>
    <div class="ai-panel">
      <div class="ai-line">
        <label for="aiMode">AI &#27169;&#24335;</label>
        <input id="aiMode" type="checkbox" />
      </div>
      <div class="label">AI &#25918;&#26041;&#22602;&#36895;&#24230;&#65306;<span id="aiSpeedValue">3</span>x</div>
      <input id="aiSpeed" type="range" min="1" max="5" step="1" value="3" />
    </div>
    <div class="leaderboard">
      <div class="label">&#20998;&#25976;&#25490;&#34892;&#27036;</div>
      <ol id="leaderboardList"></ol>
    </div>
    <div class="controls">
      <button id="left">&#24038;&#31227;</button>
      <button id="rotate">&#26059;&#36681;</button>
      <button id="right">&#21491;&#31227;</button>
      <button id="down">&#19979;&#31227;</button>
      <button id="holdButton">&#26283;&#23384; F</button>
      <button id="drop">&#30452;&#33853;</button>
      <button id="pause">&#26283;&#20572; P</button>
      <button class="wide" id="restart">&#37325;&#26032;&#38283;&#22987;</button>
    </div>
    <div class="game-over" id="gameOver">&#36938;&#25138;&#32080;&#26463;&#65292;&#25353;&#12300;&#37325;&#26032;&#38283;&#22987;&#12301;&#20877;&#29609;&#19968;&#27425;&#12290;</div>
  </aside>
</div>

<script>
const COLS = 10;
const ROWS = 20;
const CELL = 30;
const PREVIEW = 24;
const EMPTY = "";
const COLORS = {
  I: "#22d3ee",
  O: "#facc15",
  T: "#c084fc",
  L: "#fb923c",
  J: "#60a5fa",
  S: "#4ade80",
  Z: "#f87171"
};
const SHAPES = {
  I: [
    [[0,1],[1,1],[2,1],[3,1]],
    [[2,0],[2,1],[2,2],[2,3]]
  ],
  O: [
    [[1,0],[2,0],[1,1],[2,1]]
  ],
  T: [
    [[1,0],[0,1],[1,1],[2,1]],
    [[1,0],[1,1],[2,1],[1,2]],
    [[0,1],[1,1],[2,1],[1,2]],
    [[1,0],[0,1],[1,1],[1,2]]
  ],
  L: [
    [[2,0],[0,1],[1,1],[2,1]],
    [[1,0],[1,1],[1,2],[2,2]],
    [[0,1],[1,1],[2,1],[0,2]],
    [[0,0],[1,0],[1,1],[1,2]]
  ],
  J: [
    [[0,0],[0,1],[1,1],[2,1]],
    [[1,0],[2,0],[1,1],[1,2]],
    [[0,1],[1,1],[2,1],[2,2]],
    [[1,0],[1,1],[0,2],[1,2]]
  ],
  S: [
    [[1,0],[2,0],[0,1],[1,1]],
    [[1,0],[1,1],[2,1],[2,2]]
  ],
  Z: [
    [[0,0],[1,0],[1,1],[2,1]],
    [[2,0],[1,1],[2,1],[1,2]]
  ]
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

let board;
let piece;
let nextPiece;
let heldPieceKind;
let canHold;
let score;
let lines;
let level;
let gameOver;
let paused;
let dropTimer;
let aiTimer;
let aiTarget;
let gameStartedAt;
let scoreSaved;

function createEmptyBoard() {
  return Array.from({ length: ROWS }, () => Array(COLS).fill(EMPTY));
}

function createPiece(kind) {
  return { kind, x: 3, y: 0, rotation: 0 };
}

function createRandomPiece() {
  const keys = Object.keys(SHAPES);
  return createPiece(keys[Math.floor(Math.random() * keys.length)]);
}

function cloneBoard(source) {
  return source.map(row => row.slice());
}

function getPieceCells(target) {
  return SHAPES[target.kind][target.rotation].map(([dx, dy]) => [target.x + dx, target.y + dy]);
}

function isPositionLegalOn(target, targetBoard) {
  return getPieceCells(target).every(([x, y]) => {
    return x >= 0 && x < COLS && y >= 0 && y < ROWS && targetBoard[y][x] === EMPTY;
  });
}

function isPositionLegal(target) {
  return isPositionLegalOn(target, board);
}

function movePiece(dx, dy) {
  if (gameOver || paused) return false;
  const moved = { ...piece, x: piece.x + dx, y: piece.y + dy };
  if (isPositionLegal(moved)) {
    piece = moved;
    draw();
    return true;
  }
  if (dx === 0 && dy === 1) {
    fixPieceToBoard();
    clearFullLines();
    spawnNextPiece();
    aiTarget = null;
    draw();
  }
  return false;
}

function rotatePiece() {
  if (gameOver || paused) return;
  const rotated = { ...piece, rotation: (piece.rotation + 1) % SHAPES[piece.kind].length };
  for (const kick of [0, -1, 1, -2, 2]) {
    const candidate = { ...rotated, x: rotated.x + kick };
    if (isPositionLegal(candidate)) {
      piece = candidate;
      aiTarget = null;
      draw();
      return;
    }
  }
}

function holdPiece() {
  if (gameOver || paused || !canHold) return;

  const currentKind = piece.kind;
  if (heldPieceKind === null) {
    heldPieceKind = currentKind;
    piece = nextPiece;
    nextPiece = createRandomPiece();
  } else {
    piece = createPiece(heldPieceKind);
    heldPieceKind = currentKind;
  }

  piece.x = 3;
  piece.y = 0;
  piece.rotation = 0;
  canHold = false;
  aiTarget = null;

  if (!isPositionLegal(piece)) {
    endGame();
  }
  draw();
}

function hardDrop() {
  if (gameOver || paused) return;
  let dropped = 0;
  while (movePiece(0, 1)) dropped += 1;
  score += dropped * 2;
  updateStats();
}

function fixPieceToBoard() {
  for (const [x, y] of getPieceCells(piece)) {
    if (y >= 0 && y < ROWS && x >= 0 && x < COLS) board[y][x] = piece.kind;
  }
}

function clearFullLines() {
  const kept = board.filter(row => row.some(cell => cell === EMPTY));
  const cleared = ROWS - kept.length;
  if (cleared > 0) {
    board = Array.from({ length: cleared }, () => Array(COLS).fill(EMPTY)).concat(kept);
    lines += cleared;
    score += { 1: 100, 2: 300, 3: 500, 4: 800 }[cleared];
    level = 1 + Math.floor(lines / 10);
    resetDropTimer();
  }
}

function spawnNextPiece() {
  piece = nextPiece;
  piece.x = 3;
  piece.y = 0;
  piece.rotation = 0;
  nextPiece = createRandomPiece();
  canHold = true;
  if (!isPositionLegal(piece)) {
    endGame();
  }
}

function endGame() {
  gameOver = true;
  statusEl.textContent = "\u7d50\u675f";
  gameOverEl.classList.add("show");
  clearInterval(dropTimer);
  clearInterval(aiTimer);
  saveScore();
  renderLeaderboard();
}

function drawCell(ctx, x, y, size, kind) {
  ctx.fillStyle = kind ? COLORS[kind] : "#111827";
  ctx.fillRect(x * size, y * size, size, size);
  ctx.strokeStyle = "#334155";
  ctx.lineWidth = 1;
  ctx.strokeRect(x * size + 0.5, y * size + 0.5, size - 1, size - 1);
}

function drawBoard() {
  boardCtx.clearRect(0, 0, boardCanvas.width, boardCanvas.height);
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) drawCell(boardCtx, x, y, CELL, board[y][x]);
  }
  for (const [x, y] of getPieceCells(piece)) {
    if (y >= 0) drawCell(boardCtx, x, y, CELL, piece.kind);
  }
}

function drawPreview(ctx, kind) {
  ctx.clearRect(0, 0, 96, 96);
  for (let y = 0; y < 4; y++) {
    for (let x = 0; x < 4; x++) drawCell(ctx, x, y, PREVIEW, EMPTY);
  }
  if (!kind) return;
  for (const [x, y] of SHAPES[kind][0]) drawCell(ctx, x, y, PREVIEW, kind);
}

function updateStats() {
  scoreEl.textContent = String(score);
  linesEl.textContent = String(lines);
  levelEl.textContent = String(getEffectiveLevel());
  statusEl.textContent = gameOver ? "\u7d50\u675f" : paused ? "\u66ab\u505c" : "\u9032\u884c\u4e2d";
}

function loadLeaderboard() {
  try {
    const parsed = JSON.parse(localStorage.getItem(LEADERBOARD_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveScore() {
  if (scoreSaved || score <= 0) return;
  scoreSaved = true;
  const entry = {
    score,
    lines,
    level: getEffectiveLevel(),
    mode: aiModeEl.checked ? "AI" : "Manual",
    at: new Date().toLocaleString()
  };
  const leaderboard = loadLeaderboard()
    .concat(entry)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);
  localStorage.setItem(LEADERBOARD_KEY, JSON.stringify(leaderboard));
}

function renderLeaderboard() {
  const leaderboard = loadLeaderboard();
  leaderboardListEl.innerHTML = "";
  if (leaderboard.length === 0) {
    const emptyItem = document.createElement("li");
    emptyItem.textContent = "\u5c1a\u7121\u7d00\u9304";
    leaderboardListEl.appendChild(emptyItem);
    return;
  }
  for (const entry of leaderboard) {
    const item = document.createElement("li");
    item.textContent = `${entry.score} pts / ${entry.lines} lines / Lv ${entry.level} / ${entry.mode}`;
    leaderboardListEl.appendChild(item);
  }
}

function draw() {
  drawBoard();
  drawPreview(nextCtx, nextPiece.kind);
  drawPreview(holdCtx, heldPieceKind);
  updateStats();
}

function getTimeLevelBonus() {
  if (!gameStartedAt) return 0;
  return Math.floor((Date.now() - gameStartedAt) / 30000);
}

function getEffectiveLevel() {
  return level + getTimeLevelBonus();
}

function getInterval() {
  return Math.max(70, 760 - (getEffectiveLevel() - 1) * 55);
}

function resetDropTimer() {
  clearInterval(dropTimer);
  dropTimer = setInterval(() => movePiece(0, 1), getInterval());
}

function getAiInterval() {
  const speed = Number(aiSpeedEl.value);
  return Math.max(25, Math.round(260 / speed));
}

function resetAiTimer() {
  clearInterval(aiTimer);
  aiSpeedValueEl.textContent = aiSpeedEl.value;
  if (aiModeEl.checked) {
    aiTimer = setInterval(runAiStep, getAiInterval());
  }
}

function placePieceOn(targetBoard, targetPiece) {
  const nextBoard = cloneBoard(targetBoard);
  for (const [x, y] of getPieceCells(targetPiece)) {
    if (y >= 0 && y < ROWS && x >= 0 && x < COLS) nextBoard[y][x] = targetPiece.kind;
  }
  return nextBoard;
}

function clearedLineCount(targetBoard) {
  return targetBoard.filter(row => row.every(cell => cell !== EMPTY)).length;
}

function boardAfterClears(targetBoard) {
  const kept = targetBoard.filter(row => row.some(cell => cell === EMPTY));
  const cleared = ROWS - kept.length;
  return Array.from({ length: cleared }, () => Array(COLS).fill(EMPTY)).concat(kept);
}

function columnHeights(targetBoard) {
  const heights = [];
  for (let x = 0; x < COLS; x++) {
    let height = 0;
    for (let y = 0; y < ROWS; y++) {
      if (targetBoard[y][x] !== EMPTY) {
        height = ROWS - y;
        break;
      }
    }
    heights.push(height);
  }
  return heights;
}

function countHoles(targetBoard) {
  let holes = 0;
  for (let x = 0; x < COLS; x++) {
    let seenBlock = false;
    for (let y = 0; y < ROWS; y++) {
      if (targetBoard[y][x] !== EMPTY) seenBlock = true;
      else if (seenBlock) holes += 1;
    }
  }
  return holes;
}

function bumpiness(heights) {
  let total = 0;
  for (let i = 0; i < heights.length - 1; i++) total += Math.abs(heights[i] - heights[i + 1]);
  return total;
}

function countWells(heights) {
  let wells = 0;
  for (let x = 0; x < heights.length; x++) {
    const left = x === 0 ? Infinity : heights[x - 1];
    const right = x === heights.length - 1 ? Infinity : heights[x + 1];
    const depth = Math.min(left, right) - heights[x];
    if (depth > 1) wells += depth;
  }
  return wells;
}

function landingResult(candidate, targetBoard = board) {
  const landedBoard = placePieceOn(targetBoard, candidate);
  const cleared = clearedLineCount(landedBoard);
  return {
    board: boardAfterClears(landedBoard),
    cleared
  };
}

function evaluateBoardState(targetBoard, cleared) {
  const heights = columnHeights(targetBoard);
  const aggregateHeight = heights.reduce((sum, value) => sum + value, 0);
  const maxHeight = Math.max(...heights);
  return (
    cleared * 12
    - aggregateHeight * 0.5
    - maxHeight * 0.35
    - countHoles(targetBoard) * 5.2
    - bumpiness(heights) * 0.8
    + countWells(heights) * 0.15
  );
}

function evaluateLanding(candidate, targetBoard = board) {
  const result = landingResult(candidate, targetBoard);
  return evaluateBoardState(result.board, result.cleared);
}

function bestLandingValue(kind, targetBoard) {
  const best = findBestMoveFor(kind, targetBoard, null, false);
  return best ? best.value : -9999;
}

function evaluateLandingWithFuture(candidate, targetBoard, futureKind) {
  const result = landingResult(candidate, targetBoard);
  const immediate = evaluateBoardState(result.board, result.cleared);
  if (!futureKind) return immediate;
  return immediate + bestLandingValue(futureKind, result.board) * 0.38;
}

function findBestMoveFor(kind, targetBoard = board, futureKind = null, includeFuture = true) {
  let best = null;
  for (let rotation = 0; rotation < SHAPES[kind].length; rotation++) {
    for (let x = -3; x < COLS + 3; x++) {
      let candidate = { kind, x, y: 0, rotation };
      if (!isPositionLegalOn(candidate, targetBoard)) continue;
      while (isPositionLegalOn({ ...candidate, y: candidate.y + 1 }, targetBoard)) {
        candidate = { ...candidate, y: candidate.y + 1 };
      }
      const value = includeFuture
        ? evaluateLandingWithFuture(candidate, targetBoard, futureKind)
        : evaluateLanding(candidate, targetBoard);
      if (!best || value > best.value) {
        best = {
          x: candidate.x,
          rotation,
          value,
          landingY: candidate.y
        };
      }
    }
  }
  return best;
}

function findBestMove() {
  return findBestMoveFor(piece.kind, board, nextPiece.kind);
}

function planAiTarget() {
  const direct = findBestMove();
  let bestPlan = direct ? { ...direct, kind: piece.kind, useHold: false } : null;

  if (canHold) {
    const holdKind = heldPieceKind === null ? nextPiece.kind : heldPieceKind;
    const futureKind = heldPieceKind === null ? piece.kind : nextPiece.kind;
    const holdMove = findBestMoveFor(holdKind, board, futureKind);
    const holdPenalty = heldPieceKind === null ? 0.35 : 0.15;
    if (holdMove) {
      const holdPlan = {
        ...holdMove,
        kind: holdKind,
        useHold: true,
        value: holdMove.value - holdPenalty
      };
      if (!bestPlan || holdPlan.value > bestPlan.value + 0.2) bestPlan = holdPlan;
    }
  }

  return bestPlan;
}

function runAiStep() {
  if (!aiModeEl.checked || gameOver || paused) return;
  if (!aiTarget || aiTarget.kind !== piece.kind) {
    aiTarget = planAiTarget();
  }
  if (aiTarget && aiTarget.useHold && canHold) {
    const targetAfterHold = { ...aiTarget, useHold: false };
    holdPiece();
    aiTarget = { ...targetAfterHold, kind: piece.kind };
    return;
  }
  if (!aiTarget || aiTarget.x === undefined) {
    hardDrop();
    return;
  }
  if (piece.rotation !== aiTarget.rotation) {
    rotatePiece();
    return;
  }
  if (piece.x < aiTarget.x) {
    movePiece(1, 0);
    return;
  }
  if (piece.x > aiTarget.x) {
    movePiece(-1, 0);
    return;
  }
  hardDrop();
}

function refreshSpeedTimers() {
  if (gameOver) return;
  resetDropTimer();
  resetAiTimer();
  draw();
}

function startGame() {
  board = createEmptyBoard();
  piece = createRandomPiece();
  nextPiece = createRandomPiece();
  heldPieceKind = null;
  canHold = true;
  score = 0;
  lines = 0;
  level = 1;
  gameOver = false;
  paused = false;
  aiTarget = null;
  scoreSaved = false;
  gameStartedAt = Date.now();
  gameOverEl.classList.remove("show");
  resetDropTimer();
  resetAiTimer();
  draw();
  renderLeaderboard();
  setTimeout(() => boardCanvas.focus(), 50);
}

function togglePause() {
  if (gameOver) return;
  paused = !paused;
  updateStats();
}

document.getElementById("left").addEventListener("click", () => movePiece(-1, 0));
document.getElementById("right").addEventListener("click", () => movePiece(1, 0));
document.getElementById("down").addEventListener("click", () => movePiece(0, 1));
document.getElementById("rotate").addEventListener("click", rotatePiece);
document.getElementById("drop").addEventListener("click", hardDrop);
document.getElementById("holdButton").addEventListener("click", holdPiece);
document.getElementById("pause").addEventListener("click", togglePause);
document.getElementById("restart").addEventListener("click", startGame);
aiModeEl.addEventListener("change", () => {
  aiTarget = null;
  resetAiTimer();
});
aiSpeedEl.addEventListener("input", resetAiTimer);

document.addEventListener("keydown", (event) => {
  if (["ArrowLeft", "ArrowRight", "ArrowDown", "ArrowUp", " ", "f", "F"].includes(event.key)) {
    event.preventDefault();
  }
  if (event.key === "ArrowLeft" || event.key.toLowerCase() === "a") movePiece(-1, 0);
  if (event.key === "ArrowRight" || event.key.toLowerCase() === "d") movePiece(1, 0);
  if (event.key === "ArrowDown" || event.key.toLowerCase() === "s") movePiece(0, 1);
  if (event.key === "ArrowUp" || event.key.toLowerCase() === "w") rotatePiece();
  if (event.key === " ") hardDrop();
  if (event.key.toLowerCase() === "f") holdPiece();
  if (event.key.toLowerCase() === "p") togglePause();
});

boardCanvas.addEventListener("click", () => boardCanvas.focus());
startGame();
setInterval(refreshSpeedTimers, 5000);
</script>
</body>
</html>
"""


def main() -> None:
    st.title("\u4fc4\u56c9\u65af\u65b9\u584a")
    st.caption(
        "\u9ede\u4e00\u4e0b\u68cb\u76e4\u5f8c\uff0c\u7528\u9375\u76e4\u6216\u53f3\u5074\u6309\u9215\u64cd\u63a7\u65b9\u584a\u3002"
        "\u53ef\u958b\u555f AI \u6a21\u5f0f\uff0c\u4e26\u8abf\u6574 AI \u653e\u65b9\u584a\u901f\u5ea6 1-5 \u500d\u3002"
    )
    components.html(GAME_HTML, height=760, scrolling=False)


main()
