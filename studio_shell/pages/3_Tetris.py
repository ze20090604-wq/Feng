from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHELL_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

from studio_shell.page_shell import page_shell
from studio_shell.shell_ui import (
  format_extra_context,
  inject_style,
  load_page_data,
  save_page_data,
  shared_data_path,
)

PAGE_NAME = "Tetris"

GAME_MODES: dict[str, dict[str, object]] = {
  "classic": {
    "label": "經典模式",
    "description": "標準 10x20 俄羅斯方塊規則。",
    "fog_base_hidden_rows": 1,
    "fog_rows_per_10_lines": 1,
    "enabled": True,
  },
  "fog_of_war": {
    "label": "戰爭迷霧",
    "description": "一開始只遮住最底下 1 行；每消除 10 行，迷霧再往上增加 1 層。",
    "fog_base_hidden_rows": 1,
    "fog_rows_per_10_lines": 1,
    "enabled": True,
  },
  "reverse_gravity": {
    "label": "反重力",
    "description": "方塊從底部往上浮，堆向頂端；清行後空白列會補到底部。",
    "fog_base_hidden_rows": 1,
    "fog_rows_per_10_lines": 1,
    "enabled": True,
  },
}
MODE_OPTIONS = [mode for mode, config in GAME_MODES.items() if bool(config.get("enabled"))]
DEFAULT_TETRIS_STATE = {
  "mode": "classic",
  "available_modes": MODE_OPTIONS,
  "fog_base_hidden_rows": int(GAME_MODES["fog_of_war"]["fog_base_hidden_rows"]),
  "fog_rows_per_10_lines": int(GAME_MODES["fog_of_war"]["fog_rows_per_10_lines"]),
}

st.set_page_config(page_title="俄囉斯方塊（Tetris）", page_icon="🧩", layout="wide")
inject_style()


def normalize_mode(value: object) -> str:
  mode = str(value or "classic").strip().lower()
  if mode in MODE_OPTIONS:
    return mode
  return "classic"


def normalize_fog_base_hidden_rows(value: object) -> int:
  try:
    row = int(value)
  except (TypeError, ValueError):
    row = int(DEFAULT_TETRIS_STATE["fog_base_hidden_rows"])
  return max(1, min(10, row))


def normalize_fog_rows_per_10_lines(value: object) -> int:
  try:
    growth = int(value)
  except (TypeError, ValueError):
    growth = int(DEFAULT_TETRIS_STATE["fog_rows_per_10_lines"])
  return max(0, min(3, growth))


def build_tetris_state(raw_state: dict[str, object]) -> dict[str, object]:
  mode = normalize_mode(raw_state.get("mode"))
  return {
    "mode": mode,
    "available_modes": MODE_OPTIONS,
    "fog_base_hidden_rows": normalize_fog_base_hidden_rows(
      raw_state.get("fog_base_hidden_rows", raw_state.get("fog_hidden_rows", 1))
    ),
    "fog_rows_per_10_lines": normalize_fog_rows_per_10_lines(
      raw_state.get("fog_rows_per_10_lines", 1)
    ),
  }


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
  .shell { display: grid; grid-template-columns: 1fr; gap: 18px; padding: 4px; max-width: 860px; margin: 0 auto; overflow-x: auto; }
  .game-area { display: grid; grid-template-columns: 92px 248px 92px; gap: 12px; align-items: start; justify-content: center; width: max-content; min-width: 456px; margin: 0 auto; }
  .board-wrap, .side, .left-rail, .right-rail { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
  .board-wrap { min-height: 472px; width: 248px; display: flex; justify-content: center; align-items: flex-start; flex: 0 0 auto; }
  canvas { display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; outline: none; }
  h2 { margin: 0 0 10px; font-size: 22px; line-height: 1.25; }
  .hint { color: var(--muted); line-height: 1.5; margin: 8px 0 14px; }
  .board-wrap canvas { touch-action: manipulation; }
  .stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin: 12px 0; }
  .stat, .ai-panel, .leaderboard { border: 1px solid var(--line); border-radius: 8px; padding: 10px; background: rgba(15, 23, 42, 0.75); }
  .label { color: var(--muted); font-size: 12px; margin-bottom: 4px; text-align: center; }
  .value { font-size: 24px; font-weight: 700; }
  .left-rail, .right-rail { display: flex; flex-direction: column; gap: 12px; width: 92px; flex: 0 0 auto; }
  .right-rail { width: 80px; }
  .rail-section { display: flex; flex-direction: column; gap: 8px; align-items: center; }
  .preview-stack { display: flex; flex-direction: column; gap: 8px; align-items: center; }
  .preview-card { border: 1px solid var(--line); border-radius: 10px; padding: 6px; background: linear-gradient(180deg, rgba(30, 41, 59, 0.92), rgba(15, 23, 42, 0.88)); display: flex; justify-content: center; align-items: center; box-shadow: inset 0 1px 0 rgba(255,255,255,0.04); }
  .right-rail .preview-card { padding: 4px; }
  .mini-canvas { margin-top: 2px; }
  .ai-panel { margin-top: 14px; }
  .ai-line { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin: 8px 0; }
  select { width: 100%; min-height: 34px; border: 1px solid var(--line); border-radius: 7px; background: #0f172a; color: var(--text); padding: 6px 8px; }
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
  .side { width: min(100%, 620px); margin: 0 auto; }
</style>
</head>
<body>
<div class="shell">
  <div class="game-area">
    <aside class="left-rail">
      <div class="rail-section">
        <div class="label">暫存方塊 F</div>
        <div class="preview-card">
          <canvas id="hold" class="mini-canvas" width="72" height="72"></canvas>
        </div>
      </div>
    </aside>
    <div class="board-wrap"><canvas id="board" width="220" height="440" tabindex="0" aria-label="Tetris board"></canvas></div>
    <aside class="right-rail">
      <div class="rail-section">
        <div class="label">下個方塊</div>
        <div class="preview-stack">
          <div class="preview-card"><canvas id="next0" class="mini-canvas" width="56" height="56"></canvas></div>
          <div class="preview-card"><canvas id="next1" class="mini-canvas" width="56" height="56"></canvas></div>
          <div class="preview-card"><canvas id="next2" class="mini-canvas" width="56" height="56"></canvas></div>
          <div class="preview-card"><canvas id="next3" class="mini-canvas" width="56" height="56"></canvas></div>
          <div class="preview-card"><canvas id="next4" class="mini-canvas" width="56" height="56"></canvas></div>
        </div>
      </div>
    </aside>
  </div>
    <aside class="side">
      <p class="hint">先點一下棋盤讓遊戲取得焦點，再用鍵盤操作：A 左移，D 右移，S 軟降，W 順時針旋轉，Q 逆時針旋轉，空白鍵硬降，F 暫存，P 暫停。每顆方塊只能暫存一次，落地後才會重置；在反重力模式中，方塊會從底部往上浮。</p>
      <div class="stats">
        <div class="stat"><div class="label">分數</div><div class="value" id="score">0</div></div>
        <div class="stat"><div class="label">消行</div><div class="value" id="lines">0</div></div>
        <div class="stat"><div class="label">等級</div><div class="value" id="level">1</div></div>
        <div class="stat"><div class="label">狀態</div><div class="value" id="status">進行中</div></div>
        <div class="stat"><div class="label">玩法模式</div><div class="value" id="modeLabel" style="font-size:18px;">經典模式</div></div>
      </div>
      <div class="ai-panel"><div class="label">AI 模式</div><select id="aiMode"><option value="off">關閉</option><option value="recommend">落點推薦</option><option value="auto">全自動代打</option></select><div class="label" style="margin-top:10px;">AI 動作速度：<span id="aiSpeedValue">3</span>x</div><input id="aiSpeed" type="range" min="1" max="5" step="1" value="3" /></div>
      <div class="controls"><button id="left">左移</button><button id="rotateCw">順時針</button><button id="rotateCcw">逆時針</button><button id="right">右移</button><button id="down">軟降</button><button id="holdButton">暫存 F</button><button id="drop">硬降</button><button id="pause">暫停 P</button><button class="wide" id="restart">重新開始</button></div>
      <div class="game-over" id="gameOver">遊戲結束，按「重新開始」再玩一次。</div>
      <div class="leaderboard"><div class="label">本機紀錄</div><ol id="leaderboardList"></ol></div>
    </aside>
</div>
<script>
const GAME_CONFIG = __GAME_CONFIG__;
const COLS = 10;
const ROWS = 20;
const CELL = 22;
const HOLD_PREVIEW = 14;
const NEXT_PREVIEW = 10;
const EMPTY = "";
const GAME_MODE = GAME_CONFIG.mode || "classic";
const MODE_LABEL = GAME_CONFIG.modeLabel || "經典模式";
const FOG_BASE_HIDDEN_ROWS = Number.isFinite(Number(GAME_CONFIG.fogBaseHiddenRows)) ? Number(GAME_CONFIG.fogBaseHiddenRows) : 1;
const FOG_ROWS_PER_10_LINES = Number.isFinite(Number(GAME_CONFIG.fogRowsPer10Lines)) ? Number(GAME_CONFIG.fogRowsPer10Lines) : 1;
const COLORS = { I:"#22d3ee", O:"#facc15", T:"#c084fc", L:"#fb923c", J:"#60a5fa", S:"#4ade80", Z:"#f87171" };
const SHAPES = {
  I: [
    [[0,1],[1,1],[2,1],[3,1]],
    [[2,0],[2,1],[2,2],[2,3]],
    [[0,2],[1,2],[2,2],[3,2]],
    [[1,0],[1,1],[1,2],[1,3]],
  ],
  O: [
    [[1,0],[2,0],[1,1],[2,1]],
    [[1,0],[2,0],[1,1],[2,1]],
    [[1,0],[2,0],[1,1],[2,1]],
    [[1,0],[2,0],[1,1],[2,1]],
  ],
  T: [
    [[1,0],[0,1],[1,1],[2,1]],
    [[1,0],[1,1],[2,1],[1,2]],
    [[0,1],[1,1],[2,1],[1,2]],
    [[1,0],[0,1],[1,1],[1,2]],
  ],
  L: [
    [[2,0],[0,1],[1,1],[2,1]],
    [[1,0],[1,1],[1,2],[2,2]],
    [[0,1],[1,1],[2,1],[0,2]],
    [[0,0],[1,0],[1,1],[1,2]],
  ],
  J: [
    [[0,0],[0,1],[1,1],[2,1]],
    [[1,0],[2,0],[1,1],[1,2]],
    [[0,1],[1,1],[2,1],[2,2]],
    [[1,0],[1,1],[0,2],[1,2]],
  ],
  S: [
    [[1,0],[2,0],[0,1],[1,1]],
    [[1,0],[1,1],[2,1],[2,2]],
    [[1,1],[2,1],[0,2],[1,2]],
    [[0,0],[0,1],[1,1],[1,2]],
  ],
  Z: [
    [[0,0],[1,0],[1,1],[2,1]],
    [[2,0],[1,1],[2,1],[1,2]],
    [[0,1],[1,1],[1,2],[2,2]],
    [[1,0],[0,1],[1,1],[0,2]],
  ]
};
const boardCanvas = document.getElementById("board");
const boardCtx = boardCanvas.getContext("2d");
const nextContexts = [0, 1, 2, 3, 4].map(index => document.getElementById(`next${index}`).getContext("2d"));
const holdCanvas = document.getElementById("hold");
const holdCtx = holdCanvas.getContext("2d");
const scoreEl = document.getElementById("score");
const linesEl = document.getElementById("lines");
const levelEl = document.getElementById("level");
const statusEl = document.getElementById("status");
const modeLabelEl = document.getElementById("modeLabel");
const gameOverEl = document.getElementById("gameOver");
const aiModeEl = document.getElementById("aiMode");
const aiSpeedEl = document.getElementById("aiSpeed");
const aiSpeedValueEl = document.getElementById("aiSpeedValue");
const leaderboardListEl = document.getElementById("leaderboardList");
const LEADERBOARD_KEY = "tetris-leaderboard-v1";
let board, piece, nextPieces, heldPieceKind, canHold, score, lines, level, gameOver, paused, dropTimer, aiTimer, aiTarget, recommendation, scoreSaved;
function isFogMode() { return GAME_MODE === "fog_of_war"; }
function isReverseGravityMode() { return GAME_MODE === "reverse_gravity"; }
function getFogHiddenRows() {
  if (!isFogMode()) return 0;
  const growthSteps = Math.floor(lines / 10);
  return Math.max(1, Math.min(ROWS - 4, FOG_BASE_HIDDEN_ROWS + growthSteps * FOG_ROWS_PER_10_LINES));
}
function getFogStartRow() {
  return Math.max(0, ROWS - getFogHiddenRows());
}
function getGravityDirection() { return isReverseGravityMode() ? -1 : 1; }
function getSpawnY(kind, rotation = 0) {
  const cells = SHAPES[kind][rotation];
  if (isReverseGravityMode()) {
    const maxY = Math.max(...cells.map(([, y]) => y));
    return ROWS - 1 - maxY;
  }
  const minY = Math.min(...cells.map(([, y]) => y));
  return Math.max(0, -minY);
}
function resetPiecePlacement(target) {
  target.x = 3;
  target.rotation = target.rotation || 0;
  target.y = getSpawnY(target.kind, target.rotation);
  return target;
}
function createEmptyBoard() { return Array.from({ length: ROWS }, () => Array(COLS).fill(EMPTY)); }
function createPiece(kind) { return { kind, x: 3, y: 0, rotation: 0 }; }
function createRandomPiece() { const keys = Object.keys(SHAPES); return createPiece(keys[Math.floor(Math.random() * keys.length)]); }
function getPieceCells(target) { return SHAPES[target.kind][target.rotation].map(([dx, dy]) => [target.x + dx, target.y + dy]); }
function isPositionLegal(target) { return getPieceCells(target).every(([x, y]) => x >= 0 && x < COLS && y >= 0 && y < ROWS && board[y][x] === EMPTY); }
function getAiMode() { return aiModeEl.value; }
function isAutoMode() { return getAiMode() === "auto"; }
function isRecommendMode() { return getAiMode() === "recommend"; }
function movePiece(dx, dy) {
  if (gameOver || paused) return false;
  const moved = { ...piece, x: piece.x + dx, y: piece.y + dy };
  if (isPositionLegal(moved)) {
    piece = moved;
    draw();
    return true;
  }
  if (dx === 0 && dy === getGravityDirection()) {
    fixPieceToBoard();
    clearFullLines();
    spawnNextPiece();
    aiTarget = null;
    recommendation = null;
    draw();
  }
  return false;
}
function rotatePiece(direction = 1) {
  if (gameOver || paused || piece.kind === "O") return false;
  const rotationCount = SHAPES[piece.kind].length;
  const nextRotation = (piece.rotation + direction + rotationCount) % rotationCount;
  const rotated = { ...piece, rotation: nextRotation };
  const kicks = [[0, 0], [-1, 0], [1, 0], [0, 1]];
  for (const [kickX, kickY] of kicks) {
    const candidate = { ...rotated, x: rotated.x + kickX, y: rotated.y + kickY };
    if (isPositionLegal(candidate)) {
      piece = candidate;
      recommendation = null;
      draw();
      return true;
    }
  }
  return false;
}
function takeNextPiece() { const upcoming = nextPieces.shift(); nextPieces.push(createRandomPiece()); return upcoming; }
function holdPiece() { if (gameOver || paused || !canHold) return; const currentKind = piece.kind; if (heldPieceKind === null) { heldPieceKind = currentKind; piece = takeNextPiece(); } else { piece = createPiece(heldPieceKind); heldPieceKind = currentKind; } piece.rotation = 0; resetPiecePlacement(piece); canHold = false; aiTarget = null; recommendation = null; if (!isPositionLegal(piece)) endGame(); draw(); }
function hardDrop() { if (gameOver || paused) return; let dropped = 0; while (movePiece(0, getGravityDirection())) dropped += 1; score += dropped * 2; updateStats(); }
function fixPieceToBoard() { for (const [x, y] of getPieceCells(piece)) { if (y >= 0 && y < ROWS && x >= 0 && x < COLS) board[y][x] = piece.kind; } }
function clearFullLines() {
  const kept = board.filter(row => row.some(cell => cell === EMPTY));
  const cleared = ROWS - kept.length;
  if (cleared > 0) {
    const emptyRows = Array.from({ length: cleared }, () => Array(COLS).fill(EMPTY));
    board = isReverseGravityMode() ? kept.concat(emptyRows) : emptyRows.concat(kept);
    lines += cleared;
    score += { 1:100, 2:300, 3:500, 4:800 }[cleared];
    level = 1 + Math.floor(lines / 10);
    resetDropTimer();
  }
}
function spawnNextPiece() { piece = takeNextPiece(); piece.rotation = 0; resetPiecePlacement(piece); canHold = true; aiTarget = null; recommendation = null; if (!isPositionLegal(piece)) endGame(); }
function endGame() { gameOver = true; statusEl.textContent = "結束"; gameOverEl.classList.add("show"); clearInterval(dropTimer); clearInterval(aiTimer); saveScore(); }
function drawCell(ctx, x, y, size, kind) { ctx.fillStyle = kind ? COLORS[kind] : "#111827"; ctx.fillRect(x * size, y * size, size, size); ctx.strokeStyle = "#334155"; ctx.lineWidth = 1; ctx.strokeRect(x * size + 0.5, y * size + 0.5, size - 1, size - 1); }
function cloneBoard(sourceBoard) { return sourceBoard.map(row => [...row]); }
function findLandingPiece(basePiece, boardState = board) {
  const gravityDirection = getGravityDirection();
  const canPlace = target => SHAPES[target.kind][target.rotation].every(([dx, dy]) => {
    const x = target.x + dx;
    const y = target.y + dy;
    return x >= 0 && x < COLS && y >= 0 && y < ROWS && boardState[y][x] === EMPTY;
  });
  if (!canPlace(basePiece)) return null;
  let landed = { ...basePiece };
  while (canPlace({ ...landed, y: landed.y + gravityDirection })) landed.y += gravityDirection;
  return landed;
}
function placePieceOnBoard(boardState, target) {
  const placed = cloneBoard(boardState);
  for (const [x, y] of getPieceCells(target)) {
    if (y >= 0 && y < ROWS && x >= 0 && x < COLS) placed[y][x] = target.kind;
  }
  return placed;
}
function clearFullLinesFromBoard(boardState) {
  const kept = boardState.filter(row => row.some(cell => cell === EMPTY));
  const cleared = ROWS - kept.length;
  const emptyRows = Array.from({ length: cleared }, () => Array(COLS).fill(EMPTY));
  return {
    board: isReverseGravityMode() ? kept.concat(emptyRows) : emptyRows.concat(kept),
    cleared,
  };
}
function evaluateBoard(boardState, cleared) {
  const normalizedBoard = isReverseGravityMode() ? [...boardState].reverse() : boardState;
  const heights = [];
  let holes = 0;
  for (let x = 0; x < COLS; x++) {
    let height = 0;
    let seenBlock = false;
    for (let y = 0; y < ROWS; y++) {
      if (normalizedBoard[y][x] !== EMPTY) {
        if (!seenBlock) {
          height = ROWS - y;
          seenBlock = true;
        }
      } else if (seenBlock) {
        holes += 1;
      }
    }
    heights.push(height);
  }
  let bumpiness = 0;
  for (let i = 0; i < heights.length - 1; i++) bumpiness += Math.abs(heights[i] - heights[i + 1]);
  const aggregateHeight = heights.reduce((sum, value) => sum + value, 0);
  const maxHeight = Math.max(...heights);
  return cleared * 12 - aggregateHeight * 0.45 - holes * 1.8 - bumpiness * 0.35 - maxHeight * 0.25;
}
function findBestPlacement(kind, boardState = board) {
  let best = null;
  for (let rotation = 0; rotation < SHAPES[kind].length; rotation++) {
    for (let x = -2; x < COLS + 2; x++) {
      const candidate = findLandingPiece({ kind, x, y: getSpawnY(kind, rotation), rotation }, boardState);
      if (!candidate) continue;
      const placed = placePieceOnBoard(boardState, candidate);
      const { board: clearedBoard, cleared } = clearFullLinesFromBoard(placed);
      const scoreValue = evaluateBoard(clearedBoard, cleared);
      if (!best || scoreValue > best.score) best = { ...candidate, score: scoreValue };
    }
  }
  return best;
}
function updateRecommendation() {
  if (gameOver || paused || !piece || getAiMode() === "off") {
    recommendation = null;
    if (!isAutoMode()) aiTarget = null;
    return;
  }
  recommendation = findBestPlacement(piece.kind);
  if (isAutoMode()) aiTarget = recommendation ? { ...recommendation } : null;
}
function drawGhostPiece(target, color, alpha) {
  if (!target) return;
  boardCtx.save();
  boardCtx.globalAlpha = alpha;
  for (const [x, y] of getPieceCells(target)) {
    if (y < 0) continue;
    boardCtx.fillStyle = color;
    boardCtx.fillRect(x * CELL, y * CELL, CELL, CELL);
    boardCtx.strokeStyle = "#cbd5e1";
    boardCtx.lineWidth = 1;
    boardCtx.strokeRect(x * CELL + 0.5, y * CELL + 0.5, CELL - 1, CELL - 1);
  }
  boardCtx.restore();
}
function drawFogOverlay() {
  if (!isFogMode()) return;
  const fogStartRow = getFogStartRow();
  boardCtx.save();
  for (let y = fogStartRow; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) {
      boardCtx.fillStyle = "rgba(2, 6, 23, 1)";
      boardCtx.fillRect(x * CELL, y * CELL, CELL, CELL);
      boardCtx.strokeStyle = "rgba(2, 6, 23, 1)";
      boardCtx.lineWidth = 1;
      boardCtx.strokeRect(x * CELL + 0.5, y * CELL + 0.5, CELL - 1, CELL - 1);
    }
  }
  boardCtx.restore();
}
function drawBoard() {
  boardCtx.clearRect(0, 0, boardCanvas.width, boardCanvas.height);
  for (let y = 0; y < ROWS; y++) for (let x = 0; x < COLS; x++) drawCell(boardCtx, x, y, CELL, board[y][x]);
  if (recommendation && (isRecommendMode() || isAutoMode())) drawGhostPiece(recommendation, isAutoMode() ? "#38bdf8" : "#f8fafc", isAutoMode() ? 0.2 : 0.28);
  for (const [x, y] of getPieceCells(piece)) if (y >= 0) drawCell(boardCtx, x, y, CELL, piece.kind);
  drawFogOverlay();
}
function drawPreview(ctx, kind, cellSize) {
  const width = ctx.canvas.width;
  const height = ctx.canvas.height;
  ctx.clearRect(0, 0, width, height);
  if (!kind) return;
  const cells = SHAPES[kind][0];
  const xs = cells.map(([x]) => x);
  const ys = cells.map(([, y]) => y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const offsetX = (width - (maxX - minX + 1) * cellSize) / 2;
  const offsetY = (height - (maxY - minY + 1) * cellSize) / 2;
  for (const [x, y] of cells) {
    const drawX = (x - minX) * cellSize + offsetX;
    const drawY = (y - minY) * cellSize + offsetY;
    ctx.fillStyle = COLORS[kind];
    ctx.fillRect(drawX, drawY, cellSize, cellSize);
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 1;
    ctx.strokeRect(drawX + 0.5, drawY + 0.5, cellSize - 1, cellSize - 1);
  }
}
function updateStats() { scoreEl.textContent = String(score); linesEl.textContent = String(lines); levelEl.textContent = String(getEffectiveLevel()); statusEl.textContent = gameOver ? "結束" : paused ? "暫停" : isAutoMode() ? "AI 代打" : isRecommendMode() ? "推薦中" : "進行中"; modeLabelEl.textContent = MODE_LABEL; }
function syncControlState() {
  aiSpeedValueEl.textContent = aiSpeedEl.value;
  updateStats();
}
function loadLeaderboard() { try { const parsed = JSON.parse(localStorage.getItem(LEADERBOARD_KEY) || "[]"); return Array.isArray(parsed) ? parsed : []; } catch { return []; } }
function saveScore() { if (scoreSaved || score <= 0) return; scoreSaved = true; const entry = { score, lines, level: getEffectiveLevel(), mode: getAiMode() === "auto" ? "AI-Auto" : getAiMode() === "recommend" ? "AI-Hint" : "Manual", at: new Date().toLocaleString() }; const leaderboard = loadLeaderboard().concat(entry).sort((a, b) => b.score - a.score).slice(0, 5); localStorage.setItem(LEADERBOARD_KEY, JSON.stringify(leaderboard)); }
function renderLeaderboard() { const leaderboard = loadLeaderboard(); leaderboardListEl.innerHTML = ""; if (leaderboard.length === 0) { const emptyItem = document.createElement("li"); emptyItem.textContent = "尚無紀錄"; leaderboardListEl.appendChild(emptyItem); return; } for (const entry of leaderboard) { const item = document.createElement("li"); item.textContent = `${entry.score} pts / ${entry.lines} lines / Lv ${entry.level} / ${entry.mode}`; leaderboardListEl.appendChild(item); } }
function getEffectiveLevel() { return Math.max(1, Math.min(20, level)); }
function resetDropTimer() { clearInterval(dropTimer); dropTimer = setInterval(() => movePiece(0, getGravityDirection()), Math.max(80, 700 - getEffectiveLevel() * 50)); }
function getAiInterval() { return Math.max(70, 460 - Number(aiSpeedEl.value) * 70); }
function autoPlayStep() {
  if (!isAutoMode() || gameOver || paused || !piece) return;
  if (!aiTarget || aiTarget.kind !== piece.kind) updateRecommendation();
  if (!aiTarget) return;
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
function resetAiTimer() {
  clearInterval(aiTimer);
  if (isAutoMode() && !gameOver && !paused) aiTimer = setInterval(autoPlayStep, getAiInterval());
}
function draw() {
  updateRecommendation();
  drawBoard();
  nextContexts.forEach((ctx, index) => drawPreview(ctx, nextPieces[index]?.kind, NEXT_PREVIEW));
  drawPreview(holdCtx, heldPieceKind, HOLD_PREVIEW);
  syncControlState();
}
function startGame() { board = createEmptyBoard(); nextPieces = Array.from({ length: 5 }, () => createRandomPiece()); piece = takeNextPiece(); piece.rotation = 0; resetPiecePlacement(piece); heldPieceKind = null; canHold = true; score = 0; lines = 0; level = 1; gameOver = false; paused = false; aiTarget = null; recommendation = null; scoreSaved = false; gameOverEl.classList.remove("show"); renderLeaderboard(); resetDropTimer(); resetAiTimer(); draw(); requestAnimationFrame(() => { draw(); requestAnimationFrame(() => boardCanvas.focus()); }); }
function togglePause() { if (gameOver) return; paused = !paused; resetAiTimer(); updateStats(); }
function handleKey(e) {
  const key = (e.key || "").toLowerCase();
  const isMoveOrRotateKey = ["a", "d", "s", "w", "q", "f", "p", " ", "spacebar"].includes(key) || e.code === "Space";
  if (isMoveOrRotateKey) e.preventDefault();
  if (isAutoMode() && !["p"].includes(key) && e.code !== "Space") return;
  if (key === " " || e.code === "Space" || key === "spacebar") {
    hardDrop();
    return;
  }
  if (key === "a") movePiece(-1, 0);
  else if (key === "d") movePiece(1, 0);
  else if (key === "s") movePiece(0, 1);
  else if (key === "w") rotatePiece(1);
  else if (key === "q") rotatePiece(-1);
  else if (key === "f") holdPiece();
  else if (key === "p") togglePause();
}
function manualAction(action) { if (isAutoMode() || gameOver) return; action(); }
document.getElementById("left").onclick = () => manualAction(() => movePiece(-1, 0));
document.getElementById("rotateCw").onclick = () => manualAction(() => rotatePiece(1));
document.getElementById("rotateCcw").onclick = () => manualAction(() => rotatePiece(-1));
document.getElementById("right").onclick = () => manualAction(() => movePiece(1, 0));
document.getElementById("down").onclick = () => manualAction(() => movePiece(0, 1));
document.getElementById("holdButton").onclick = () => manualAction(() => holdPiece());
document.getElementById("drop").onclick = () => manualAction(() => hardDrop());
document.getElementById("pause").onclick = () => togglePause();
document.getElementById("restart").onclick = () => startGame();
aiModeEl.onchange = () => { aiTarget = null; recommendation = null; resetAiTimer(); draw(); };
aiSpeedEl.oninput = () => { syncControlState(); resetAiTimer(); };
boardCanvas.addEventListener("click", () => boardCanvas.focus());
boardCanvas.addEventListener("keydown", handleKey);
window.addEventListener("pageshow", () => draw());
startGame();
boardCanvas.focus();
</script>
</body>
</html>
"""


def render_main() -> str:
  state = build_tetris_state(load_page_data(PAGE_NAME, shell_root=SHELL_ROOT))

  st.markdown("#### 模式控制")
  selected_mode = st.selectbox(
    "遊戲模式",
    MODE_OPTIONS,
    index=MODE_OPTIONS.index(state["mode"]),
    format_func=lambda mode: str(GAME_MODES[mode]["label"]),
  )
  st.caption(str(GAME_MODES[selected_mode]["description"]))
  st.info(
    "你可以直接對右側 Agent 說：『請把 Tetris 切換成戰爭迷霧模式』。"
    "Agent 會讀寫共享 JSON 來改左欄設定。"
  )
  if selected_mode == "fog_of_war":
    st.caption("迷霧規則：開局先遮住底部 1 行；每消除 10 行，再多遮 1 行。")

  tetris_state = {
    "mode": selected_mode,
    "available_modes": MODE_OPTIONS,
    "fog_base_hidden_rows": int(GAME_MODES["fog_of_war"]["fog_base_hidden_rows"]),
    "fog_rows_per_10_lines": int(GAME_MODES["fog_of_war"]["fog_rows_per_10_lines"]),
  }
  save_page_data(PAGE_NAME, tetris_state, shell_root=SHELL_ROOT)

  game_config = {
    "mode": selected_mode,
    "modeLabel": str(GAME_MODES[selected_mode]["label"]),
    "fogBaseHiddenRows": int(tetris_state["fog_base_hidden_rows"]),
    "fogRowsPer10Lines": int(tetris_state["fog_rows_per_10_lines"]),
  }
  game_html = GAME_HTML.replace("__GAME_CONFIG__", json.dumps(game_config, ensure_ascii=False))
  st.components.v1.html(game_html, height=1180, scrolling=True)

  return format_extra_context(
    PAGE_NAME,
    共享資料檔=str(shared_data_path(PAGE_NAME, shell_root=SHELL_ROOT)),
    目前模式=str(GAME_MODES[selected_mode]["label"]),
    模式代碼=selected_mode,
    可用模式=", ".join(MODE_OPTIONS),
    迷霧初始遮蔽行數=int(tetris_state["fog_base_hidden_rows"]),
    每10行增加迷霧層數=int(tetris_state["fog_rows_per_10_lines"]),
    模式說明=str(GAME_MODES[selected_mode]["description"]),
    反重力規則="方塊自底部生成、往上浮、清行後空白列補到底部" if selected_mode == "reverse_gravity" else "切換到 reverse_gravity 可啟用反重力玩法",
  )


page_shell(
    "俄囉斯方塊（Tetris）",
    "完整 Tetris 小遊戲頁面。",
    render_main,
    page_name=PAGE_NAME,
)
