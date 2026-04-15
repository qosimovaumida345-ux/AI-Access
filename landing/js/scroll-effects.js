/* ============================================================
   SHADOWFORGE — SCROLL EFFECTS ENGINE
   IntersectionObserver-based reveal system.
   Breach trigger. Feature cards. Protocol steps. Counters.
   ============================================================ */

(function ShadowScrollEffects() {
  'use strict';

  /* ── BREACH ZONE OBSERVER ────────────────────────────────── */
  function initBreachObserver() {
    const trigger = document.getElementById('breach-trigger');
    if (!trigger) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.intersectionRatio > 0.35) {
            document.body.classList.add('is-breached');
          } else if (entry.intersectionRatio === 0) {
            document.body.classList.remove('is-breached');
          }
        });
      },
      { threshold: [0, 0.35, 0.7, 1] }
    );

    observer.observe(trigger);
  }

  /* ── FEATURE CARDS REVEAL ────────────────────────────────── */
  function initCardReveals() {
    const cards = document.querySelectorAll('[data-reveal]');
    if (!cards.length) return;

    // Set initial state with stagger delays
    cards.forEach((card, i) => {
      card.style.transitionDelay = `${i * 0.08}s`;
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: '0px 0px -50px 0px' }
    );

    cards.forEach(card => observer.observe(card));
  }

  /* ── PROTOCOL STEPS REVEAL ───────────────────────────────── */
  function initProtocolSteps() {
    const steps = document.querySelectorAll('.protocol__step');
    if (!steps.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry, i) => {
          if (entry.isIntersecting) {
            // Stagger delay per step
            const index = Array.from(steps).indexOf(entry.target);
            setTimeout(() => {
              entry.target.classList.add('is-visible');
            }, index * 120);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.2, rootMargin: '0px 0px -40px 0px' }
    );

    steps.forEach(step => observer.observe(step));
  }

  /* ── COUNTER ANIMATION ───────────────────────────────────── */
  function animateCounter(el) {
    const target   = parseInt(el.dataset.target, 10);
    const duration = 1800;
    const startTime = performance.now();

    // Easing function
    function easeOutQuart(t) {
      return 1 - Math.pow(1 - t, 4);
    }

    function tick(now) {
      const elapsed  = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased    = easeOutQuart(progress);
      const current  = Math.round(eased * target);

      el.textContent = current.toLocaleString();

      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = target.toLocaleString();
      }
    }

    requestAnimationFrame(tick);
  }

  function initCounters() {
    const counters = document.querySelectorAll('[data-target]');
    if (!counters.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            animateCounter(entry.target);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.6 }
    );

    counters.forEach(c => observer.observe(c));
  }

  /* ── INSTALL STEPS PREVIEW ANIMATION ────────────────────── */
  function initInstallPreview() {
    const stepsWrap = document.getElementById('install-steps-preview');
    if (!stepsWrap) return;

    const steps = stepsWrap.querySelectorAll('.install__step');
    let currentStep = -1;
    let interval = null;
    let hasStarted = false;

    function runPreview() {
      if (hasStarted) return;
      hasStarted = true;

      interval = setInterval(() => {
        // Mark previous as done
        if (currentStep >= 0 && steps[currentStep]) {
          steps[currentStep].classList.remove('install__step--active');
          steps[currentStep].classList.add('install__step--done');
          steps[currentStep].querySelector('.install__step-icon').textContent = '✓';
        }

        currentStep++;

        if (currentStep >= steps.length) {
          clearInterval(interval);
          // Loop back after pause
          setTimeout(() => {
            steps.forEach(s => {
              s.classList.remove('install__step--active', 'install__step--done');
              s.querySelector('.install__step-icon').textContent = '◈';
            });
            currentStep = -1;
            hasStarted = false;
            // Re-observe
            observer.observe(stepsWrap);
          }, 3000);
          return;
        }

        if (steps[currentStep]) {
          steps[currentStep].classList.add('install__step--active');
        }
      }, 900);
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            runPreview();
            observer.unobserve(stepsWrap);
          }
        });
      },
      { threshold: 0.4 }
    );

    observer.observe(stepsWrap);
  }

  /* ── GENERAL FADE-UP OBSERVER ────────────────────────────── */
  function initGeneralReveal() {
    const elements = document.querySelectorAll(
      '.section__header, .security__content, .install__content, .providers__grid'
    );
    if (!elements.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );

    elements.forEach(el => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(24px)';
      el.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
      observer.observe(el);
    });
  }

  /* ── INIT ALL ────────────────────────────────────────────── */
  function init() {
    initBreachObserver();
    initCardReveals();
    initProtocolSteps();
    initCounters();
    initInstallPreview();
    initGeneralReveal();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();