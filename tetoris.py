import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Tetris (Mobile Gestures)", page_icon="🧱", layout="centered")
st.title("🧱 Tetris — 9×20 with Mobile Gestures")
st.caption("Tap=Rotate • Swipe L/R=Move • Swipe ↓=Soft drop • Quick flick ↓=Hard drop • Buttons also work • WASD/Arrows on desktop")

html = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  :root { --cols: 9; --rows: 20; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; background:#0e0f12; color:#eee; }
  .wrap { display:flex; flex-wrap:wrap; gap:14px; justify-content:center; align-items:flex-start; padding:12px; }
  .canvas-wrap { display:block; overflow:visible; }
  canvas {
    display:block;
    background:#0b0c0f;
    border-radius:10px;
    box-shadow:inset 0 0 0 1px #222, 0 10px 30px rgba(0,0,0,.25);
    image-rendering: pixelated; image-rendering: crisp-edges;
    touch-action: none;               /* critical: let us capture gestures */
  }
  .panel {
    display:flex; flex-direction:column; gap:10px; min-width:220px;
    background:#16181d; padding:12px; border-radius:12px; box-shadow:0 10px 30px rgba(0,0,0,.2);
  }
  .btn { appearance:none; border:0; padding:10px 12px; border-radius:10px; cursor:pointer; font-weight:700; }
  .primary { background:#3b82f6; color:white; }
  .muted { background:#23262d; color:#cbd5e1; }
  .lcd { font-variant-numeric: tabular-nums; background:#0b0c0f; padding:8px 10px; border-radius:8px; color:#a7f3d0; }

  /* Mobile control pad */
  .pad {
    display:grid; grid-template-columns: repeat(5, 56px); gap:10px; justify-content:center; align-items:center;
    background:#0f1116; padding:10px; border-radius:12px; box-shadow:inset 0 0 0 1px #1f2330;
    width: max-content; margin: 6px auto 0;
  }
  .pad button {
    height:56px; border-radius:12px; font-size:16px; font-weight:800;
    background:#1e293b; color:#e2e8f0; border:none;
    box-shadow: 0 2px 0 #0b0f19 inset, 0 6px 16px rgba(0,0,0,.25);
  }
  .pad button:active { transform: translateY(1px); }
  .pad .wide { grid-column: span 2; }
  .pad .ghost { background:#0b1322; color:#93c5fd; }

  .legend { font-size:12px; color:#94a3b8; text-align:center; }

  /* Compact on very small phones */
  @media (max-width: 420px) {
    .pad { grid-template-columns: repeat(5, 52px); gap:8px; }
    .pad button { height:52px; font-size:14px; }
  }
</style>
</head>
<body>
  <div class="wrap">
    <div class="canvas-wrap">
      <canvas id="board" aria-label="Tetris board"></canvas>
      <div class="pad" aria-label="mobile control pad">
        <button id="leftBtn">◀</button>
        <button id="rightBtn">▶</button>
        <button id="rotBtn" class="ghost">⟳</button>
        <button id="softBtn">▼</button>
        <button id="hardBtn" class="wide">HARD</button>
        <button id="pauseBtn" class="wide muted">PAUSE</button>
      </div>
      <div class="legend">Tap=Rotate • Swipe L/R=Move • Swipe ↓=Soft • Quick flick ↓=Hard</div>
    </div>
    <div class="panel">
      <div style="display:flex; gap:8px;">
        <button class="btn primary" id="start">Start</button>
        <button class="btn muted" id="pbtn">P (pause)</button>
      </div>
      <div><strong>Score</strong><div class="lcd"><span id="score">0</span></div></div>
      <div><strong>Lines</strong><div class="lcd"><span id="lines">0</span></div></div>
      <div><strong>Level</strong><div class="lcd"><span id="level">1</span></div></div>
    </div>
  </div>

<script>
(() => {
  // ====== Config ======
  const COLS = 9, ROWS = 20, CELL = 24; // small main game bit (phone friendly)
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

  // Tetromino shapes (in 4×4 frame)
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

  const startBtn = document.getElementById('start');
  const pbtn = document.getElementById('pbtn');

  // Mobile pad buttons
  const leftBtn = document.getElementById('leftBtn');
  const rightBtn = document.getElementById('rightBtn');
  const softBtn = document.getElementById('softBtn');
  const hardBtn = document.getElementById('hardBtn');
  const rotBtn = document.getElementById('rotBtn');
  const pauseBtn = document.getElementById('pauseBtn');

  function createGrid(w,h){ return Array.from({length:h}, () => Array(w).fill(null)); }

  // Drawing
  function drawCell(x,y,color,ghost=false){
    if (x < 0 || x >= COLS || y < 0 || y >= ROWS) return;
    const px = x * CELL, py = y * CELL;
    ctx.save();
    if(ghost) ctx.globalAlpha = 0.25;
    ctx.fillStyle = color || "#0b0c0f";
    ctx.fillRect(px+1, py+1, CELL-2, CELL-2);
    if(color){
      ctx.globalAlpha = ghost ? 0.25 : 1;
      ctx.strokeStyle = "rgba(255,255,255,.08)";
      ctx.lineWidth = 1;
      ctx.strokeRect(px+1.5, py+1.5, CELL-3, CELL-3);
    }
    ctx.restore();
  }

  function drawGridLines(){
    ctx.save();
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 2;
    ctx.strokeRect(0.5,0.5,COLS*CELL-1,ROWS*CELL-1);
    // inner grid
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(148,163,184,.25)";
    for (let x=1;x<COLS;x++){ const gx = x*CELL+0.5; ctx.beginPath(); ctx.moveTo(gx,1); ctx.lineTo(gx,ROWS*CELL-1); ctx.stroke(); }
    for (let y=1;y<ROWS;y++){ const gy = y*CELL+0.5; ctx.beginPath(); ctx.moveTo(1,gy); ctx.lineTo(COLS*CELL-1,gy); ctx.stroke(); }
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

  // Game logic
  function newPiece(){
    if (nextQueue.length < 7){
      const bag = Object.keys(SHAPES);
      for (let i=bag.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [bag[i],bag[j]]=[bag[j],bag[i]]; }
      nextQueue.push(...bag);
    }
    const type = nextQueue.shift();
    falling = new Tetromino(type);
    if (collides(falling,0,0,falling.shape)){ gameOver(); return; }
  }

  function Tetromino(type){
    this.type = type;
    this.x = Math.floor((COLS-4)/2);  // center spawn for 9-wide
    this.y = -2;                       // spawn above, not drawn until y>=0
    this.shape = SHAPES[type].map(v=>v.slice());
    this.blocks = () => this.shape;
  }

  function rotate(shape){ return shape.map(([x,y])=>[y,3-x]).map(([x,y])=>[x-1,y-1]); }

  function wallKick(t,newShape,dx=0,dy=0){
    const kicks=[[0,0],[1,0],[-1,0],[2,0],[-2,0],[0,-1]];
    for(const[kx,ky]of kicks){
      if(!collides(t,dx+kx,dy+ky,newShape)){ t.x+=dx+kx;t.y+=dy+ky;t.shape=newShape;return true; }
    } return false;
  }

  function collides(t,dx,dy,shape){
    for(const[px,py]of shape){
      const x=t.x+dx+px,y=t.y+dy+py;
      if(x<0||x>=COLS||y>=ROWS)return true;
      if(y>=0&&grid[y][x])return true;
    } return false;
  }

  function clearLines(){
    let count=0;
    outer:for(let y=ROWS-1;y>=0;y--){
      for(let x=0;x<COLS;x++){ if(!grid[y][x])continue outer; }
      grid.splice(y,1); grid.unshift(Array(COLS).fill(null)); count++; y++;
    } return count;
  }

  function updateHUD(){ scoreEl.textContent=score; linesEl.textContent=lines; levelEl.textContent=level; }

  function lockPiece(){
    // Ceiling death: any block above row 0 when locking => game over
    let hitCeiling=false;
    for(const[px,py]of falling.blocks()){
      const x=falling.x+px, y=falling.y+py;
      if(y<0){hitCeiling=true;} else if(y<ROWS){ grid[y][x]=COLORS[falling.type]; }
    }
    if(hitCeiling){ gameOver(); return; }
    const cleared=clearLines();
    score+=[0,100,300,500,800][cleared]*Math.max(1,level);
    lines+=cleared; level=1+Math.floor(lines/10); updateHUD();
    newPiece();
  }

  function hardDrop(){
    while(!collides(falling,0,1,falling.shape)){ falling.y++; score+=2; }
    lockPiece();
  }

  function ghostDropY(){ let dy=0; while(!collides(falling,0,dy+1,falling.shape))dy++; return falling.y+dy; }

  function step(dt){
    if(!running || paused) return;
    dropCounter += dt;
    const speed = Math.max(80, 800 - (level-1)*60);
    if(dropCounter > speed){
      if(collides(falling,0,1,falling.shape)){ lockPiece(); }
      else { falling.y++; }
      dropCounter = 0;
    }
  }

  // ====== Desktop keyboard ======
  document.addEventListener('keydown',(e)=>{
    const left=e.code==='KeyA'||e.code==='ArrowLeft';
    const right=e.code==='KeyD'||e.code==='ArrowRight';
    const down=e.code==='KeyS'||e.code==='ArrowDown';
    const rot=e.code==='KeyW'||e.code==='ArrowUp';
    const hard=e.code==='Space';
    if(!running||paused){ if(e.key==='p'||e.key==='P') togglePause(); return; }
    if(!falling) return;
    if(left) moveLeft();
    else if(right) moveRight();
    else if(down) softDropAction();
    else if(rot) rotateAction();
    else if(hard){ e.preventDefault(); hardDropAction(); }
  });

  // ====== Shared control actions ======
  function moveLeft(){ if(!collides(falling,-1,0,falling.shape)) falling.x--; }
  function moveRight(){ if(!collides(falling, 1,0,falling.shape)) falling.x++; }
  function rotateAction(){ const rotated = rotate(falling.shape.map(p=>p.slice())); wallKick(falling, rotated); }
  function softDropAction(){ if(!collides(falling,0,1,falling.shape)){ falling.y++; score+=1; updateHUD(); } }
  function hardDropAction(){ hardDrop(); }

  // ====== Mobile on-screen buttons (hold-to-repeat) ======
  function repeatWhileHold(el, fn, interval=110){
    let t=null;
    const start=(e)=>{ e.preventDefault(); if(!running||paused||!falling) return; fn(); t=setInterval(fn, interval); };
    const stop =()=>{ if(t){ clearInterval(t); t=null; } };
    el.addEventListener('pointerdown', start, {passive:false});
    ['pointerup','pointerleave','pointercancel'].forEach(ev=> el.addEventListener(ev, stop));
  }
  repeatWhileHold(leftBtn, moveLeft);
  repeatWhileHold(rightBtn, moveRight);
  repeatWhileHold(softBtn, softDropAction, 80);
  hardBtn.addEventListener('pointerdown', (e)=>{ e.preventDefault(); if(!running||paused||!falling) return; hardDropAction(); }, {passive:false});
  rotBtn.addEventListener('pointerdown', (e)=>{ e.preventDefault(); if(!running||paused||!falling) return; rotateAction(); }, {passive:false});
  pauseBtn.addEventListener('pointerdown', (e)=>{ e.preventDefault(); togglePause(); }, {passive:false});

  // ====== Gesture controls on canvas ======
  let touch = {active:false, x0:0, y0:0, lastX:0, lastY:0, moved:false, t0:0, accumX:0, accumY:0};
  const SWIPE_COL = CELL * 0.6;     // horizontal distance for one column move
  const SWIPE_SOFT = CELL * 0.5;    // vertical distance per soft drop step
  const FLICK_DOWN_DIST = CELL * 2; // quick flick threshold
  const FLICK_TIME = 200;           // ms

  function canvasPoint(e){
    const rect = canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  canvas.addEventListener('pointerdown', (e)=>{
    e.preventDefault();
    touch.active = true; touch.moved=false;
    const p = canvasPoint(e);
    touch.x0 = touch.lastX = p.x;
    touch.y0 = touch.lastY = p.y;
    touch.t0 = performance.now();
    touch.accumX = 0; touch.accumY = 0;
  }, {passive:false});

  canvas.addEventListener('pointermove', (e)=>{
    if(!touch.active || !running || paused || !falling) return;
    e.preventDefault();
    const p = canvasPoint(e);
    const dx = p.x - touch.lastX;
    const dy = p.y - touch.lastY;
    touch.lastX = p.x; touch.lastY = p.y;

    const totalDx = p.x - touch.x0;
    const totalDy = p.y - touch.y0;
    if(Math.hypot(totalDx, totalDy) > 6) touch.moved = true;

    // Horizontal: move by columns as finger slides
    touch.accumX += dx;
    while (touch.accumX <= -SWIPE_COL) { moveLeft();  touch.accumX += SWIPE_COL; }
    while (touch.accumX >=  SWIPE_COL) { moveRight(); touch.accumX -= SWIPE_COL; }

    // Vertical: soft drop continuously while dragging down
    touch.accumY += dy;
    while (touch.accumY >= SWIPE_SOFT) { softDropAction(); touch.accumY -= SWIPE_SOFT; }
  }, {passive:false});

  function endGesture(e){
    if(!touch.active) return;
    e.preventDefault();
    const dt = performance.now() - touch.t0;
    const dy = touch.lastY - touch.y0;
    if(!touch.moved && dt < 200){
      // Tap = rotate
      if(running && !paused && falling) rotateAction();
    } else if (dy > FLICK_DOWN_DIST && dt < FLICK_TIME){
      // Quick flick down = hard drop
      if(running && !paused && falling) hardDropAction();
    }
    touch.active = false;
  }
  canvas.addEventListener('pointerup', endGesture, {passive:false});
  canvas.addEventListener('pointercancel', endGesture, {passive:false});
  canvas.addEventListener('pointerleave', (e)=>{ if(touch.active) endGesture(e); }, {passive:false});

  // ====== Controls (Start/Pause) ======
  startBtn.addEventListener('click', start);
  pbtn.addEventListener('click', togglePause);

  function togglePause(){ if(!running) return; paused = !paused; }

  // ====== Loop ======
  let rafId = null;
  function loop(ts){
    if(!lastTime) lastTime = ts;
    const dt = Math.min((ts - lastTime)/1000, 0.033);
    lastTime = ts;
    step(dt);
    drawBoard();
    rafId = requestAnimationFrame(loop);
  }

  function start(){
    grid = createGrid(COLS, ROWS);
    score=0; lines=0; level=1; nextQueue=[];
    running=true; paused=false; dropCounter=0; lastTime=0;
    newPiece(); updateHUD();
    if(rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(loop);
  }

  function gameOver(){
    running=false; paused=false;
    // overlay
    ctx.save();
    ctx.fillStyle="rgba(0,0,0,.6)"; ctx.fillRect(0,0,canvas.width,canvas.height);
    ctx.fillStyle="#e2e8f0"; ctx.font="bold 20px system-ui"; ctx.textAlign="center";
    ctx.fillText("Game Over", canvas.width/2, canvas.height/2 - 6);
    ctx.font="14px system-ui"; ctx.fillStyle="#94a3b8";
    ctx.fillText("Hit the ceiling or stacked out", canvas.width/2, canvas.height/2 + 14);
    ctx.restore();
  }

  // initial frame
  drawBoard();
})();
</script>
</body>
</html>
"""

components.html(html, height=720, scrolling=False)