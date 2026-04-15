/* ============================================================
   SHADOWFORGE — NAVBAR CONTROLLER
   Sticky behavior, mobile menu, active link tracking,
   scroll-based hide/show.
   ============================================================ */

(function ShadowNavbar() {
  'use strict';

  /* ── ELEMENTS ────────────────────────────────────────────── */
  const navbar     = document.getElementById('navbar');
  const burgerBtn  = document.getElementById('burger-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  const navLinks   = document.querySelectorAll('.navbar__link');
  const mobileLinks= document.querySelectorAll('.mobile-menu__link');

  if (!navbar) return;

  /* ── STATE ───────────────────────────────────────────────── */
  let lastScrollY  = 0;
  let isMobileOpen = false;
  let ticking      = false;
  const SCROLL_THRESHOLD = 80;
  const HIDE_THRESHOLD   = 300;

  /* ── SCROLL HANDLER ──────────────────────────────────────── */
  function onScroll() {
    if (!ticking) {
      requestAnimationFrame(updateNavbar);
      ticking = true;
    }
  }

  function updateNavbar() {
    const currentY = window.scrollY;

    // Scrolled state (background opacity)
    if (currentY > SCROLL_THRESHOLD) {
      navbar.classList.add('navbar--scrolled');
    } else {
      navbar.classList.remove('navbar--scrolled');
    }

    // Hide on scroll down, show on scroll up
    if (currentY > HIDE_THRESHOLD) {
      if (currentY > lastScrollY && !isMobileOpen) {
        navbar.classList.add('navbar--hidden');
      } else {
        navbar.classList.remove('navbar--hidden');
      }
    } else {
      navbar.classList.remove('navbar--hidden');
    }

    lastScrollY = currentY;
    ticking = false;

    updateActiveLink();
  }

  /* ── ACTIVE LINK TRACKING ────────────────────────────────── */
  const sections = [];

  function cacheSections() {
    navLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (!href || !href.startsWith('#')) return;
      const section = document.querySelector(href);
      if (section) sections.push({ link, section });
    });
  }

  function updateActiveLink() {
    const scrollMid = window.scrollY + window.innerHeight / 3;

    sections.forEach(({ link, section }) => {
      const top    = section.offsetTop;
      const bottom = top + section.offsetHeight;

      if (scrollMid >= top && scrollMid < bottom) {
        navLinks.forEach(l => l.classList.remove('active'));
        link.classList.add('active');
      }
    });
  }

  /* ── MOBILE MENU ─────────────────────────────────────────── */
  function openMobile() {
    isMobileOpen = true;
    burgerBtn.classList.add('is-active');
    burgerBtn.setAttribute('aria-expanded', 'true');
    mobileMenu.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    navbar.classList.remove('navbar--hidden');
  }

  function closeMobile() {
    isMobileOpen = false;
    burgerBtn.classList.remove('is-active');
    burgerBtn.setAttribute('aria-expanded', 'false');
    mobileMenu.classList.remove('is-open');
    document.body.style.overflow = '';
  }

  function toggleMobile() {
    isMobileOpen ? closeMobile() : openMobile();
  }

  /* ── SMOOTH SCROLL ───────────────────────────────────────── */
  function smoothScroll(href) {
    if (!href || !href.startsWith('#')) return;
    const target = document.querySelector(href);
    if (!target) return;

    const top = target.getBoundingClientRect().top + window.scrollY;
    const offset = parseInt(
      getComputedStyle(document.documentElement)
        .getPropertyValue('--navbar-height') || '72'
    );

    window.scrollTo({
      top: top - offset - 16,
      behavior: 'smooth',
    });
  }

  /* ── BIND EVENTS ─────────────────────────────────────────── */
  function bindEvents() {
    window.addEventListener('scroll', onScroll, { passive: true });

    if (burgerBtn) {
      burgerBtn.addEventListener('click', toggleMobile);
    }

    // Desktop nav links
    navLinks.forEach(link => {
      link.addEventListener('click', e => {
        const href = link.getAttribute('href');
        if (href && href.startsWith('#')) {
          e.preventDefault();
          smoothScroll(href);
        }
      });
    });

    // Mobile nav links
    mobileLinks.forEach(link => {
      link.addEventListener('click', e => {
        const href = link.getAttribute('href');
        closeMobile();
        if (href && href.startsWith('#')) {
          e.preventDefault();
          setTimeout(() => smoothScroll(href), 350);
        }
      });
    });

    // Close mobile on ESC
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && isMobileOpen) closeMobile();
    });

    // Close mobile on overlay click (outside menu)
    document.addEventListener('click', e => {
      if (
        isMobileOpen &&
        !mobileMenu.contains(e.target) &&
        !burgerBtn.contains(e.target)
      ) {
        closeMobile();
      }
    });
  }

  /* ── INIT ────────────────────────────────────────────────── */
  function init() {
    cacheSections();
    bindEvents();
    updateNavbar(); // run once on load
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();