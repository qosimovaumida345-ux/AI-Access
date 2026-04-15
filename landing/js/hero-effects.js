/* ============================================================
   SHADOWFORGE — HERO EFFECTS
   Mouse parallax on hero. Title glitch on hover.
   Subtle ambient breathing animation.
   ============================================================ */

(function ShadowHeroEffects() {
  'use strict';

  /* ── MOUSE PARALLAX ──────────────────────────────────────── */
  function initParallax() {
    const hero = document.querySelector('.hero');
    if (!hero) return;

    const layers = [
      { el: hero.querySelector('.hero__title'),    depthX: 0.012, depthY: 0.008 },
      { el: hero.querySelector('.hero__subtitle'), depthX: 0.008, depthY: 0.005 },
      { el: hero.querySelector('.hero__eyebrow'),  depthX: 0.006, depthY: 0.004 },
      { el: hero.querySelector('.hero__stats'),    depthX: 0.004, depthY: 0.003 },
    ].filter(l => l.el !== null);

    let targetX = 0, targetY = 0;
    let currentX = 0, currentY = 0;
    let rafId;

    function lerp(a, b, t) { return a + (b - a) * t; }

    function updateParallax() {
      currentX = lerp(currentX, targetX, 0.06);
      currentY = lerp(currentY, targetY, 0.06);

      layers.forEach(({ el, depthX, depthY }) => {
        const moveX = currentX * depthX;
        const moveY = currentY * depthY;
        el.style.transform = `translate(${moveX}px, ${moveY}px)`;
      });

      rafId = requestAnimationFrame(updateParallax);
    }

    hero.addEventListener('mousemove', e => {
      const rect = hero.getBoundingClientRect();
      targetX = (e.clientX - rect.left - rect.width  / 2);
      targetY = (e.clientY - rect.top  - rect.height / 2);
    });

    hero.addEventListener('mouseleave', () => {
      targetX = 0;
      targetY = 0;
    });

    updateParallax();
  }

  /* ── TITLE GLITCH ON HOVER ───────────────────────────────── */
  function initTitleGlitch() {
    const accent = document.querySelector('.hero__title-accent');
    if (!accent) return;

    let glitchTimeout;
    const originalText = accent.textContent;

    const glitchChars = '!@#$%^&*<>[]{}|\\∆Ω∑∞≠≈';

    function scramble(el, text, duration = 600) {
      let elapsed = 0;
      const step = 60;

      const interval = setInterval(() => {
        elapsed += step;
        const progress = elapsed / duration;

        const scrambled = text
          .split('')
          .map((char, i) => {
            if (i < Math.floor(progress * text.length)) return char;
            return glitchChars[Math.floor(Math.random() * glitchChars.length)];
          })
          .join('');

        el.textContent = scrambled;

        if (elapsed >= duration) {
          clearInterval(interval);
          el.textContent = text;
        }
      }, step);
    }

    accent.addEventListener('mouseenter', () => {
      clearTimeout(glitchTimeout);
      scramble(accent, originalText, 500);
    });

    accent.addEventListener('mouseleave', () => {
      glitchTimeout = setTimeout(() => {
        accent.textContent = originalText;
      }, 100);
    });
  }

  /* ── HERO AMBIENT BREATHING ──────────────────────────────── */
  function initAmbientBreath() {
    const fog1 = document.querySelector('.bg-env__fog-1');
    const fog2 = document.querySelector('.bg-env__fog-2');
    if (!fog1 && !fog2) return;

    // Additional subtle breathing — already handled by CSS animations
    // but we add a dynamic component based on time
    let t = 0;
    function breathe() {
      t += 0.003;
      const intensity = 0.15 + Math.sin(t) * 0.05;
      if (fog1) fog1.style.opacity = intensity.toString();
      requestAnimationFrame(breathe);
    }
    breathe();
  }

  /* ── CTA BUTTON HOVER SOUND (visual feedback) ────────────── */
  function initCtaEffects() {
    const ctaBtn = document.getElementById('hero-cta');
    if (!ctaBtn) return;

    ctaBtn.addEventListener('mouseenter', () => {
      ctaBtn.style.setProperty(
        '--btn-glow-size', '80px'
      );
    });

    ctaBtn.addEventListener('mouseleave', () => {
      ctaBtn.style.setProperty(
        '--btn-glow-size', '40px'
      );
    });

    // Ripple effect on click
    ctaBtn.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      const rect   = this.getBoundingClientRect();
      const size   = Math.max(rect.width, rect.height) * 2;
      const x      = e.clientX - rect.left - size / 2;
      const y      = e.clientY - rect.top  - size / 2;

      Object.assign(ripple.style, {
        position:     'absolute',
        width:        size + 'px',
        height:       size + 'px',
        left:         x + 'px',
        top:          y + 'px',
        background:   'rgba(255,255,255,0.15)',
        borderRadius: '50%',
        transform:    'scale(0)',
        animation:    'ripple-expand 0.6s ease-out forwards',
        pointerEvents:'none',
      });

      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 700);
    });
  }

  /* ── SCROLL HINT HIDE ────────────────────────────────────── */
  function initScrollHint() {
    const hint = document.querySelector('.hero__scroll');
    if (!hint) return;

    window.addEventListener('scroll', function handler() {
      if (window.scrollY > 100) {
        hint.style.opacity = '0';
        hint.style.pointerEvents = 'none';
        window.removeEventListener('scroll', handler);
      }
    }, { passive: true });
  }

  /* ── INIT ────────────────────────────────────────────────── */
  function init() {
    initParallax();
    initTitleGlitch();
    initAmbientBreath();
    initCtaEffects();
    initScrollHint();

    // Inject ripple keyframe if not exists
    if (!document.querySelector('#ripple-style')) {
      const style = document.createElement('style');
      style.id = 'ripple-style';
      style.textContent = `
        @keyframes ripple-expand {
          to { transform: scale(1); opacity: 0; }
        }
      `;
      document.head.appendChild(style);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();