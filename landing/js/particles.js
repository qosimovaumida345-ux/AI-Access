/* ============================================================
   SHADOWFORGE — PARTICLE SYSTEM ENGINE
   Canvas-based floating particles with connection lines.
   Purple + red color scheme. Performance optimized.
   ============================================================ */

(function ShadowParticles() {
  'use strict';

  /* ── CONFIG ──────────────────────────────────────────────── */
  const CONFIG = {
    count:           90,
    connectionDist:  130,
    connectionAlpha: 0.07,
    colors: [
      { r: 102, g: 0,   b: 204 },  // purple
      { r: 150, g: 0,   b: 204 },  // mid purple
      { r: 255, g: 0,   b: 21  },  // blood red
      { r: 80,  g: 0,   b: 160 },  // deep purple
      { r: 200, g: 0,   b: 50  },  // dark red
    ],
    minSize:  0.4,
    maxSize:  2.2,
    minSpeed: 0.08,
    maxSpeed: 0.35,
    mouseRadius:     150,
    mouseForce:      0.015,
    enableMouse:     true,
  };

  /* ── STATE ───────────────────────────────────────────────── */
  let canvas, ctx;
  let W = 0, H = 0;
  let particles = [];
  let animFrame;
  let mouse = { x: -9999, y: -9999 };
  let isRunning = false;

  /* ── INIT ────────────────────────────────────────────────── */
  function init() {
    canvas = document.getElementById('particles-canvas');
    if (!canvas) return;

    ctx = canvas.getContext('2d');
    resize();
    buildParticles();
    bindEvents();
    isRunning = true;
    loop();
  }

  /* ── RESIZE ──────────────────────────────────────────────── */
  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  /* ── BUILD PARTICLES ─────────────────────────────────────── */
  function buildParticles() {
    particles = [];
    for (let i = 0; i < CONFIG.count; i++) {
      particles.push(createParticle(true));
    }
  }

  /* ── CREATE PARTICLE ─────────────────────────────────────── */
  function createParticle(randomY = false) {
    const color = CONFIG.colors[Math.floor(Math.random() * CONFIG.colors.length)];
    return {
      x:       Math.random() * W,
      y:       randomY ? Math.random() * H : H + 10,
      size:    CONFIG.minSize + Math.random() * (CONFIG.maxSize - CONFIG.minSize),
      speedX:  (Math.random() - 0.5) * 0.25,
      speedY:  -(CONFIG.minSpeed + Math.random() * (CONFIG.maxSpeed - CONFIG.minSpeed)),
      color,
      alpha:   0,
      life:    0,
      maxLife: 180 + Math.random() * 280,
      pulse:   Math.random() * Math.PI * 2,
      pulseSpeed: 0.015 + Math.random() * 0.02,
      driftX:  (Math.random() - 0.5) * 0.4,
    };
  }

  /* ── UPDATE PARTICLE ─────────────────────────────────────── */
  function updateParticle(p) {
    p.life++;
    p.pulse += p.pulseSpeed;
    p.x += p.speedX + Math.sin(p.pulse * 0.7) * p.driftX;
    p.y += p.speedY;

    // Fade in / out
    const fadeFrames = 50;
    if (p.life < fadeFrames) {
      p.alpha = p.life / fadeFrames;
    } else if (p.life > p.maxLife - fadeFrames) {
      p.alpha = (p.maxLife - p.life) / fadeFrames;
    } else {
      p.alpha = 0.4 + Math.sin(p.pulse) * 0.3;
    }

    // Mouse repulsion
    if (CONFIG.enableMouse) {
      const dx = p.x - mouse.x;
      const dy = p.y - mouse.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < CONFIG.mouseRadius) {
        const force = (1 - dist / CONFIG.mouseRadius) * CONFIG.mouseForce;
        p.x += (dx / dist) * force * 30;
        p.y += (dy / dist) * force * 30;
      }
    }

    // Wrap X
    if (p.x < -20) p.x = W + 20;
    if (p.x > W + 20) p.x = -20;

    // Reset when done
    if (p.life >= p.maxLife || p.y < -30) {
      Object.assign(p, createParticle(false));
    }
  }

  /* ── DRAW PARTICLE ───────────────────────────────────────── */
  function drawParticle(p) {
    const { r, g, b } = p.color;
    const alpha = Math.max(0, Math.min(1, p.alpha));
    if (alpha < 0.01) return;

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = `rgb(${r},${g},${b})`;
    ctx.shadowColor = `rgba(${r},${g},${b},0.8)`;
    ctx.shadowBlur = p.size * 5;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  /* ── DRAW CONNECTIONS ────────────────────────────────────── */
  function drawConnections() {
    const len = particles.length;
    for (let i = 0; i < len; i++) {
      const a = particles[i];
      if (a.alpha < 0.1) continue;

      for (let j = i + 1; j < len; j++) {
        const b = particles[j];
        if (b.alpha < 0.1) continue;

        const dx   = a.x - b.x;
        const dy   = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < CONFIG.connectionDist) {
          const alpha = (1 - dist / CONFIG.connectionDist) * CONFIG.connectionAlpha;
          if (alpha < 0.005) continue;

          ctx.save();
          ctx.globalAlpha = alpha;
          ctx.strokeStyle = 'rgba(102,0,204,0.8)';
          ctx.lineWidth = 0.5;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
          ctx.restore();
        }
      }
    }
  }

  /* ── MAIN LOOP ───────────────────────────────────────────── */
  function loop() {
    if (!isRunning) return;
    ctx.clearRect(0, 0, W, H);
    drawConnections();
    particles.forEach(p => {
      updateParticle(p);
      drawParticle(p);
    });
    animFrame = requestAnimationFrame(loop);
  }

  /* ── EVENTS ──────────────────────────────────────────────── */
  function bindEvents() {
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        resize();
        buildParticles();
      }, 200);
    });

    if (CONFIG.enableMouse) {
      window.addEventListener('mousemove', e => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
      });
      window.addEventListener('mouseleave', () => {
        mouse.x = -9999;
        mouse.y = -9999;
      });
    }

    // Pause when tab not visible (performance)
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        isRunning = false;
        cancelAnimationFrame(animFrame);
      } else {
        isRunning = true;
        loop();
      }
    });
  }

  /* ── START ───────────────────────────────────────────────── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose for external control
  window.ShadowParticles = {
    stop: () => { isRunning = false; cancelAnimationFrame(animFrame); },
    start: () => { if (!isRunning) { isRunning = true; loop(); } },
    setCount: (n) => {
      CONFIG.count = n;
      buildParticles();
    },
  };

})();