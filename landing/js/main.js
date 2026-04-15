/* ============================================================
   SHADOWFORGE — MAIN LANDING JS
   Terminal demo typewriter. Toast system. Install preview.
   Providers grid. General UI interactions.
   ============================================================ */

(function ShadowMain() {
  'use strict';

  /* ══════════════════════════════════════════════════════════
     TERMINAL DEMO
     ══════════════════════════════════════════════════════════ */
  const DEMO_SEQUENCES = [
    {
      cmd: 'shadowforge init --name "cyber-store" --type saas',
      outputs: [
        { text: '◈ Reading project intent...', cls: 't-info', delay: 500 },
        { text: '◈ Selecting AI model: groq/llama-3.3-70b', cls: 't-info', delay: 950 },
        { text: '◈ Generating project blueprint...', cls: 't-info', delay: 1400 },
        { text: '✓ Structure: 34 folders / 89 files', cls: 't-ok', delay: 2000 },
        { text: '✓ Components written (React + Tailwind)', cls: 't-ok', delay: 2400 },
        { text: '✓ API routes: /auth /products /checkout', cls: 't-ok', delay: 2800 },
        { text: '✓ Database schema generated (PostgreSQL)', cls: 't-ok', delay: 3200 },
        { text: '✓ Tests: 47 passing', cls: 't-ok', delay: 3600 },
        { text: '⚡ Ready — run: npm run dev', cls: 't-warn', delay: 4000 },
      ],
    },
    {
      cmd: 'sudo shadowforge analyze --zip ./legacy-app.zip',
      outputs: [
        { text: '◈ Extracting ZIP archive...', cls: 't-info', delay: 400 },
        { text: '◈ Scanning 156 files...', cls: 't-info', delay: 900 },
        { text: '⚠ Found 12 security vulnerabilities', cls: 't-warn', delay: 1400 },
        { text: '⚠ 3 deprecated dependencies', cls: 't-warn', delay: 1800 },
        { text: '◈ AI analyzing code quality...', cls: 't-info', delay: 2200 },
        { text: '✓ Auto-fixed: SQL injection in auth.js', cls: 't-ok', delay: 2800 },
        { text: '✓ Updated 3 dependencies', cls: 't-ok', delay: 3200 },
        { text: '✓ Code quality: 94/100', cls: 't-ok', delay: 3600 },
        { text: '⚡ Report: ./shadowforge-report.html', cls: 't-warn', delay: 4000 },
      ],
    },
    {
      cmd: 'shadowforge deploy --target github --build all',
      outputs: [
        { text: '◈ Pushing to GitHub...', cls: 't-info', delay: 500 },
        { text: '✓ Repository: cyber-store created', cls: 't-ok', delay: 1000 },
        { text: '✓ Code committed & pushed', cls: 't-ok', delay: 1400 },
        { text: '◈ Triggering GitHub Actions...', cls: 't-info', delay: 1900 },
        { text: '✓ Build: Windows EXE ✓', cls: 't-ok', delay: 2500 },
        { text: '✓ Build: macOS DMG ✓', cls: 't-ok', delay: 2900 },
        { text: '✓ Build: Linux AppImage ✓', cls: 't-ok', delay: 3300 },
        { text: '✓ Build: Android APK ✓', cls: 't-ok', delay: 3700 },
        { text: '⚡ Release v1.0.0 published on GitHub', cls: 't-warn', delay: 4100 },
      ],
    },
  ];

  let terminalStarted = false;
  let currentSeqIndex = 0;

  function typeText(el, text, speed = 42) {
    return new Promise(resolve => {
      let i = 0;
      el.textContent = '';
      function tick() {
        if (i < text.length) {
          el.textContent += text[i++];
          setTimeout(tick, speed + Math.random() * 20);
        } else {
          resolve();
        }
      }
      tick();
    });
  }

  function addTerminalLine(container, text, cls, delay_ms) {
    return new Promise(resolve => {
      setTimeout(() => {
        const el = document.createElement('span');
        el.className = 'terminal-out-line ' + (cls || '');
        el.textContent = text;
        container.appendChild(el);
        container.scrollTop = container.scrollHeight;

        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            el.classList.add('is-shown');
          });
        });

        resolve();
      }, delay_ms);
    });
  }

  async function runTerminalSequence(index) {
    const seq       = DEMO_SEQUENCES[index % DEMO_SEQUENCES.length];
    const cmdEl     = document.getElementById('terminal-typed-cmd');
    const outputEl  = document.getElementById('terminal-output');

    if (!cmdEl || !outputEl) return;

    // Clear output
    outputEl.innerHTML = '';

    // Type command
    await typeText(cmdEl, seq.cmd, 38);

    // Output lines
    const promises = seq.outputs.map(o =>
      addTerminalLine(outputEl, o.text, o.cls, o.delay)
    );
    await Promise.all(promises);

    // Loop
    setTimeout(() => {
      currentSeqIndex = (currentSeqIndex + 1) % DEMO_SEQUENCES.length;
      runTerminalSequence(currentSeqIndex);
    }, 4500);
  }

  function initTerminal() {
    const demoSection = document.getElementById('demo');
    if (!demoSection) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting && !terminalStarted) {
            terminalStarted = true;
            runTerminalSequence(0);
          }
        });
      },
      { threshold: 0.4 }
    );

    observer.observe(demoSection);
  }

  /* ══════════════════════════════════════════════════════════
     TOAST NOTIFICATION SYSTEM
     ══════════════════════════════════════════════════════════ */
  function showToast(message, type = '', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // Remove after duration
    setTimeout(() => {
      toast.style.animation = 'fade-in 0.3s ease reverse both';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // Expose globally
  window.ShadowToast = showToast;

  /* ══════════════════════════════════════════════════════════
     PROVIDER CHIPS INTERACTION
     ══════════════════════════════════════════════════════════ */
  function initProviderChips() {
    const chips = document.querySelectorAll('.provider-chip');
    chips.forEach(chip => {
      chip.addEventListener('click', () => {
        const name = chip.querySelector('span:last-child') ||
                     chip;
        showToast(
          `◈ ${chip.textContent.trim().replace('FREE','').replace('AUTO','')} — Connected`,
          'success',
          2500
        );
      });
    });
  }

  /* ══════════════════════════════════════════════════════════
     INSTALL CTA — PREVIEW HINT
     ══════════════════════════════════════════════════════════ */
  function initCtaHint() {
    const ctaBtn = document.getElementById('main-cta-btn');
    if (!ctaBtn) return;

    let hovered = false;

    ctaBtn.addEventListener('mouseenter', () => {
      if (!hovered) {
        hovered = true;
        showToast(
          '⚡ System ready. Click to initialize.',
          'warning',
          3000
        );
      }
    });
  }

  /* ══════════════════════════════════════════════════════════
     GLOBAL SMOOTH SCROLL
     ══════════════════════════════════════════════════════════ */
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', e => {
        const href = anchor.getAttribute('href');
        if (href === '#') return;

        const target = document.querySelector(href);
        if (!target) return;

        e.preventDefault();

        const navH = parseInt(
          getComputedStyle(document.documentElement)
            .getPropertyValue('--navbar-height') || '72'
        );

        window.scrollTo({
          top: target.getBoundingClientRect().top + window.scrollY - navH - 8,
          behavior: 'smooth',
        });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════
     GLITCH SCANLINE EFFECT (periodic)
     ══════════════════════════════════════════════════════════ */
  function initGlitchPeriodic() {
    function triggerGlitch() {
      const body = document.body;
      body.style.filter = 'hue-rotate(15deg) brightness(1.05)';
      setTimeout(() => {
        body.style.filter = '';
      }, 80);

      // Schedule next
      const next = 8000 + Math.random() * 15000;
      setTimeout(triggerGlitch, next);
    }

    // First glitch after 5 seconds
    setTimeout(triggerGlitch, 5000);
  }

  /* ══════════════════════════════════════════════════════════
     INIT
     ══════════════════════════════════════════════════════════ */
  function init() {
    initTerminal();
    initProviderChips();
    initCtaHint();
    initSmoothScroll();
    initGlitchPeriodic();

    // Welcome toast
    setTimeout(() => {
      showToast('◈ ShadowForge OS — System Online', 'success', 3500);
    }, 2000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();