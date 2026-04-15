/* ============================================================
   SHADOWFORGE — PLATFORM DETECTION UTILITY
   Detects OS, browser, device type.
   Used by install page and analytics.
   ============================================================ */

(function ShadowPlatformDetect() {
  'use strict';

  /* ── DETECTION ENGINE ────────────────────────────────────── */
  const PlatformDetect = {

    ua: navigator.userAgent,
    platform: navigator.platform || '',

    /* OS Detection */
    getOS() {
      const ua = this.ua.toLowerCase();
      if (ua.includes('android'))           return 'android';
      if (ua.includes('iphone') ||
          ua.includes('ipad'))              return 'ios';
      if (ua.includes('win'))               return 'windows';
      if (ua.includes('mac'))               return 'macos';
      if (ua.includes('linux'))             return 'linux';
      if (ua.includes('cros'))              return 'chromeos';
      return 'unknown';
    },

    /* Browser Detection */
    getBrowser() {
      const ua = this.ua.toLowerCase();
      if (ua.includes('firefox'))           return 'firefox';
      if (ua.includes('edg/'))              return 'edge';
      if (ua.includes('opr/') ||
          ua.includes('opera'))             return 'opera';
      if (ua.includes('chrome'))            return 'chrome';
      if (ua.includes('safari'))            return 'safari';
      return 'unknown';
    },

    /* Device type */
    getDevice() {
      const ua = this.ua.toLowerCase();
      if (/(mobi|android|iphone|ipad)/i.test(ua)) return 'mobile';
      if (/(tablet|ipad)/i.test(ua))               return 'tablet';
      return 'desktop';
    },

    /* Arch (best effort) */
    getArch() {
      const ua = this.ua;
      if (ua.includes('arm64') ||
          ua.includes('aarch64') ||
          ua.includes('Apple'))             return 'arm64';
      if (ua.includes('x86_64') ||
          ua.includes('Win64') ||
          ua.includes('WOW64'))             return 'x64';
      if (ua.includes('x86'))               return 'x86';
      return 'x64'; // default
    },

    /* Full info object */
    getInfo() {
      return {
        os:      this.getOS(),
        browser: this.getBrowser(),
        device:  this.getDevice(),
        arch:    this.getArch(),
        mobile:  this.getDevice() !== 'desktop',
        touch:   'ontouchstart' in window,
        lang:    navigator.language || 'en',
        online:  navigator.onLine,
        cores:   navigator.hardwareConcurrency || 1,
        memory:  navigator.deviceMemory || 'unknown',
      };
    },

    /* Map OS to downloadable platform key */
    toForgeKey(os) {
      const map = {
        windows:  'windows',
        macos:    'macos',
        linux:    'linux',
        android:  'android',
        ios:      'web',
        chromeos: 'linux',
        unknown:  'windows',
      };
      return map[os] || 'windows';
    },
  };

  /* ── INJECT META TAG ─────────────────────────────────────── */
  function injectPlatformMeta() {
    const info = PlatformDetect.getInfo();

    // Add to body as data attributes for CSS targeting
    document.body.dataset.os     = info.os;
    document.body.dataset.device = info.device;
    document.body.dataset.mobile = info.mobile;

    // Console info (dev)
    if (window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1') {
      console.log('[ShadowForge] Platform Info:', info);
    }

    // Store globally
    window.ShadowPlatform = {
      info,
      forgeKey: PlatformDetect.toForgeKey(info.os),
    };
  }

  /* ── INIT ────────────────────────────────────────────────── */
  function init() {
    injectPlatformMeta();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose globally
  window.PlatformDetect = PlatformDetect;

})();