

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Tetris", page_icon="🧱", layout="centered")
st.title("🧱 Tetris (9-wide, smaller board)")
st.caption("Controls: A◀ / D▶ move • S soft drop • W rotate • Space hard drop • P pause")

html = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  :root { --cols: 9; --rows: 20; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; background:#0e0f12; color:#eee; }
  .wrap { display:flex; gap:20px; justify-content:center; align-items:flex-start; padding:14px; }
  .canvas-wrap { display:block; overflow:visible; }
  .panel {
    display:flex; flex-direction:column; gap:10px; min-width:220px;
    background:#16181d; padding:14px; border-radius:12px; box-shadow:0 10px 30px rgba(0,0,0,.2);
  }
  .btn { appearance:none; border:0; padding:10px 14px; border-radius:10px; cursor:pointer; font-weight:600; }
  .primary { background:#3b82f6; color:white; }
  .muted { background:#23262d; color:#cbd5e1; }
  .lcd { font-variant-numeric: tabular-nums; background:#0b0c0f; padding:8px 10px; border-radius:8px; color:#a7f3d0; }
  canvas {
    display:block;
    background:#0b0c0f;
    border-radius:8px;
    box-shadow:inset 0 0 0 1px #222, 0 10px 30px rgba(0,0,0,.25);
    image-rendering: crisp-edges;
    image-rendering: pixelated;
  }
  .legend { font-size:12px; color:#94a3b8; }
  .next { display:grid; grid-template-columns: repeat(6, 16px); grid-auto-rows: 16px; gap:2px; background:#0b0c0f; padding:8px; border-radius:8px; width:max-content; }
  .cell { width:16px; height:16px; border-radius:3px; }
  .footer { font-size:12px; color:#64748b; text-align:center; padding-top:8px; }
</style>
</head>
<body>
  <div class="wrap">
    <div class="canvas-wrap">
      <canvas id="board"></canvas>
    </div>
    <div class="panel">
      <div style="display:flex; gap:10px;">
        <button class="btn primary" id="start">Start</button>
        <button class="btn muted" id="pause">Pause (P)</button>
      </div>
      <div><strong>Score</strong><div class="lcd"><span id="score">0</span></div></div>
      <div><strong>Lines</strong><div class="lcd"><span id="lines">0</span></div></div>
      <div><strong>Level</strong><div class="lcd"><span id="level">1</span></div></div>
      <div>
        <strong>Next</strong>
        <div id="next" class="next" aria-label="next piece preview"></div>
      </div>
      <div class="legend">
        A / ◀ left • D / ▶ right • S / ▼ soft drop • W / ↑ rotate • Space hard drop • P pause
      </div>
      <div class="footer">Built for Streamlit via HTML component</div>
    </div>
  </div>

<script>
(() => {
  // ====== Config ======
  const COLS = 9, ROWS = 20;
  const CELL = 24;                 // ⬅️ smaller cells = smaller main game area
  const W = COLS * CELL, H = ROWS * CELL;

  const canvas = document.getElementById('board');
  const ctx = canvas.getContext('2d');
  canvas.width = W; canvas.height = H;
  canvas.style.width = W + "px"; canvas.style.height = H + "px";

  // Colors
  const COLORS = {
    I: "#60a5fa", J:"#a78bfa", L:"#f59e0b", O:"#fbbf24",
    S: "#34d399", T:"#f472b6", Z:"#ef4444"
  };

  // Shapes
  const SHAPES = {
    I: [[0,1],[1,1],[2,1],[3,1]],
    J: [[0,0],[0,1],[1,1],[2,1]],
    L: [[2,0],[0,1],[1,1],[2,1]],
    O: [[1,0],[2,0],[1,1],[2,1]],
    S: [[1,0],[2,0],[0,1],[1,1]],
    T: [[1,0],[0,1],[1,1],[2,1]],
    Z: [[0,0],[1,0],[1,1],[2,1]],
  };

  // ====== State ======
  let grid = createGrid(COLS, ROWS);
  let falling = null;
  let nextQueue = [];
  let dropCounter = 0;
  let lastTime = 0;
  let score = 0, lines = 0, level = 1;
  let running = false, paused = false;

  const scoreEl = document.getElementById('score');
  const linesEl = document.getElementById('lines');
  const levelEl = document.getElementById('level');
  const nextEl  = document.getElementById('next');
  const startBtn= document.getElementById('start');
  const pauseBtn= document.getElementById('pause');

  function createGrid(w,h){ return Array.from({length:h}, () => Array(w).fill(null)); }

  function drawCell(x,y,color,ghost=false){
    if (x < 0 || x >= COLS || y < 0 || y >= ROWS) return;
    const px = x * CELL, py = y * CELL;
    ctx.save();
    if (ghost) ctx.globalAlpha = 0.25;
    ctx.fillStyle = color || "#0b0c0f";
    ctx.fillRect(px+1, py+1, CELL-2, CELL-2);
    if (color){
      ctx.globalAlpha = ghost ? 0.25 : 1;
      ctx.strokeStyle = "rgba(255,255,255,.08)";
      ctx.lineWidth = 1;
      ctx.strokeRect(px+1.5, py+1.5, CELL-3, CELL-3);
    }
    ctx.restore();
  }

  function drawBoard(){
    ctx.clearRect(0,0,canvas.width, canvas.height);
    for (let y=0;y<ROWS;y++){ for(let x=0;x<COLS;x++){ drawCell(x,y,grid[y][x]); } }
    if (falling){
      const gy = ghostDropY();
      for (const [px,py] of falling.blocks()){
        const gx = falling.x+px, gyVis = gy+py;
        if (gyVis>=0 && gyVis<ROWS) drawCell(gx, gyVis, COLORS[falling.type], true);
      }
      for (const [px,py] of falling.blocks()){
        const dx = falling.x+px, dy = falling.y+py;
        if (dy>=0 && dy<ROWS) drawCell(dx, dy, COLORS[falling.type]);
      }
    }
    drawGridLines();
  }

  function drawGridLines(){
    ctx.save();
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 2;
    ctx.strokeRect(0.5,0.5,COLS*CELL-1,ROWS*CELL-1);
    // inner grid
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(148,163,184,.25)";
    for (let x=1;x<COLS;x++){
      const gx = x*CELL+0.5; ctx.beginPath(); ctx.moveTo(gx,1); ctx.lineTo(gx,ROWS*CELL-1); ctx.stroke();
    }
    for (let y=1;y<ROWS;y++){
      const gy = y*CELL+0.5; ctx.beginPath(); ctx.moveTo(1,gy); ctx.lineTo(COLS*CELL-1,gy); ctx.stroke();
    }
    ctx.restore();
  }

  function newPiece(){
    if (nextQueue.length < 7){
      const bag = Object.keys(SHAPES);
      for (let i=bag.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [bag[i],bag[j]]=[bag[j],bag[i]]; }
      nextQueue.push(...bag);
    }
    const type = nextQueue.shift();
    falling = new Tetromino(type);
    if (collides(falling,0,0,falling.shape)){ gameOver(); return; }
    renderNext();
  }

  function Tetromino(type){
    this.type = type;
    this.x = Math.floor((COLS-4)/2); // centered spawn for 9-wide
    this.y = -2;                      // spawn above
    this.shape = SHAPES[type].map(v=>v.slice());
    this.blocks = () => this.shape;
  }

  function rotate(shape){ return shape.map(([x,y])=>[y,3-x]).map(([x,y])=>[x-1,y-1]); }

  function wallKick(t,newShape,dx=0,dy=0){
    const kicks=[[0,0],[1,0],[-1,0],[2,0],[-2,0],[0,-1]];
    for (const [kx,ky] of kicks){
      if (!collides(t,dx+kx,dy+ky,newShape)){ t.x+=dx+kx; t.y+=dy+ky; t.shape=newShape; return true; }
    }
    return false;
  }

  function collides(t,dx,dy,shape){
    for (const [px,py] of shape){
      const x=t.x+dx+px, y=t.y+dy+py;
      if (x<0 || x>=COLS || y>=ROWS) return true;
      if (y>=0 && grid[y][x]) return true;
    }
    return false;
  }

  function lockPiece(){
    // Ceiling death: any block above row 0 when locking => game over
    let hitCeiling = false;
    for (const [px,py] of falling.blocks()){
      const x = falling.x+px, y = falling.y+py;
      if (y < 0) hitCeiling = true;
      else if (y < ROWS) grid[y][x] = COLORS[falling.type];
    }
    if (hitCeiling){ gameOver(); return; }

    const cleared = clearLines();
    score += [0,100,300,500,800][cleared] * Math.max(1, level);
    lines += cleared; level = 1 + Math.floor(lines/10);
    updateHUD();
    newPiece();
  }

  function clearLines(){
    let count = 0;
    outer: for (let y=ROWS-1;y>=0;y--){
      for (let x=0;x<COLS;x++){ if (!grid[y][x]) continue outer; }
      grid.splice(y,1); grid.unshift(Array(COLS).fill(null)); count++; y++;
    }
    return count;
  }

  function hardDrop(){ while(!collides(falling,0,1,falling.shape)){ falling.y++; score += 2; } lockPiece(); }

  function ghostDropY(){ let dy=0; while(!collides(falling,0,dy+1,falling.shape)) dy++; return falling.y + dy; }

  function step(dt){
    if (!running || paused) return;
    dropCounter += dt;
    const speed = Math.max(80, 800 - (level-1)*60);
    if (dropCounter > speed){
      if (collides(falling,0,1,falling.shape)) lockPiece();
      else falling.y++;
      dropCounter = 0;
    }
  }

  let rafId = null;
  function loop(ts){
    if(!lastTime) lastTime = ts;
    const dt = ts - lastTime; lastTime = ts;
    step(dt); drawBoard();
    rafId = requestAnimationFrame(loop);
  }

  function start(){
    grid = createGrid(COLS, ROWS);
    score=0; lines=0; level=1; nextQueue=[];
    running=true; paused=false; dropCounter=0; lastTime=0;
    newPiece(); updateHUD();
    if (rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(loop);
  }

  function togglePause(){ if(!running) return; paused = !paused; }
  function updateHUD(){ scoreEl.textContent = score; linesEl.textContent = lines; levelEl.textContent = level; }

  function renderNext(){
    nextEl.innerHTML = "";
    const previewGrid = Array.from({length:36}, () => {
      const d = document.createElement("div");
      d.className = "cell"; d.style.background = "#0f172a";
      return d;
    });
    previewGrid.forEach(n => nextEl.appendChild(n));
    if (nextQueue.length === 0) return;
    const type = nextQueue[0], shape = SHAPES[type], color = COLORS[type];
    const minx = Math.min(...shape.map(p=>p[0])), maxx = Math.max(...shape.map(p=>p[0])), miny = Math.min(...shape.map(p=>p[1]));
    const width = maxx - minx + 1, ox = Math.floor((6 - width)/2) - minx, oy = 2 - miny;
    shape.forEach(([x,y]) => {
      const cx = x + ox, cy = y + oy;
      if (cx>=0 && cx<6 && cy>=0 && cy<6){ const idx = cy*6 + cx; previewGrid[idx].style.background = color; }
    });
  }

  function gameOver(){ running=false; paused=false; drawBoard(); gameOverSplash(); }

  function gameOverSplash(){
    ctx.save();
    ctx.fillStyle="rgba(0,0,0,.6)"; ctx.fillRect(0,0,canvas.width,canvas.height);
    ctx.fillStyle="#e2e8f0"; ctx.font="bold 24px system-ui"; ctx.textAlign="center";
    ctx.fillText("Game Over", canvas.width/2, canvas.height/2 - 8);
    ctx.font="14px system-ui"; ctx.fillStyle="#94a3b8";
    ctx.fillText("Hits the ceiling = lose", canvas.width/2, canvas.height/2 + 12);
    ctx.fillText("Press Start to play again", canvas.width/2, canvas.height/2 + 32);
    ctx.restore();
  }

  // ====== Input (WASD + Arrows) ======
  document.addEventListener('keydown',(e)=>{
    const left=e.code==='KeyA'||e.code==='ArrowLeft';
    const right=e.code==='KeyD'||e.code==='ArrowRight';
    const down=e.code==='KeyS'||e.code==='ArrowDown';
    const rot=e.code==='KeyW'||e.code==='ArrowUp';
    const hard=e.code==='Space';
    if(!running||paused){ if(e.key==='p'||e.key==='P')togglePause(); return; }
    if(!falling) return;

    if(left){ if(!collides(falling,-1,0,falling.shape)) falling.x--; }
    else if(right){ if(!collides(falling,1,0,falling.shape)) falling.x++; }
    else if(down){ if(!collides(falling,0,1,falling.shape)){ falling.y++; score += 1; updateHUD(); } }
    else if(rot){ const rotated = rotate(falling.shape.map(p=>p.slice())); wallKick(falling, rotated); }
    else if(hard){ e.preventDefault(); hardDrop(); }
    else if(e.key==='p'||e.key==='P'){ togglePause(); }
  });

  startBtn.addEventListener('click', start);
  pauseBtn.addEventListener('click', togglePause);

  // initial draw
  drawBoard();
})();
</script>
</body>
</html>
"""

components.html(html, height=560, scrolling=False)
