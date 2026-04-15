/* ============================================================
   SHADOWFORGE — INSTALL PAGE SEQUENCE CONTROLLER
   Manages all 3 stages:
   Stage 1: Cinematic loading steps
   Stage 2: "Are You Sure?" horror confirm
   Stage 3: Download progress
   ============================================================ */

(function ShadowInstallSequence() {
  'use strict';

  /* ── STEP DEFINITIONS ────────────────────────────────────── */
  const LOADING_STEPS = [
    {
      id:       'step-check',
      label:    'Checking System Requirements',
      duration: 1200,
      logs: [
        { text: '» Scanning hardware...', cls: 'install-log__line--info' },
        { text: '✓ RAM: 4GB+ detected', cls: 'install-log__line--ok' },
        { text: '✓ OS compatibility confirmed', cls: 'install-log__line--ok' },
      ],
    },
    {
      id:       'step-verify',
      label:    'Verifying Environment',
      duration: 1400,
      logs: [
        { text: '» Verifying system integrity...', cls: 'install-log__line--info' },
        { text: '✓ No conflicts detected', cls: 'install-log__line--ok' },
        { text: '✓ Sandbox environment secured', cls: 'install-log__line--ok' },
      ],
    },
    {
      id:       'step-prepare',
      label:    'Preparing Forge Core',
      duration: 1600,
      logs: [
        { text: '» Unpacking core modules...', cls: 'install-log__line--info' },
        { text: '✓ Agent core loaded', cls: 'install-log__line--ok' },
        { text: '✓ Sandbox permissions applied', cls: 'install-log__line--ok' },
      ],
    },
    {
      id:       'step-modules',
      label:    'Loading AI Modules',
      duration: 1800,
      logs: [
        { text: '» Initializing AI providers...', cls: 'install-log__line--info' },
        { text: '✓ OpenRouter — connected', cls: 'install-log__line--ok' },
        { text: '✓ Groq — connected', cls: 'install-log__line--ok' },
        { text: '✓ Mistral — connected', cls: 'install-log__line--ok' },
        { text: '⚡ 8 providers ready', cls: '' },
      ],
    },
    {
      id:       'step-providers',
      label:    'Connecting AI Providers',
      duration: 1300,
      logs: [
        { text: '» Testing provider endpoints...', cls: 'install-log__line--info' },
        { text: '✓ Fallback chain configured', cls: 'install-log__line--ok' },
        { text: '✓ Auto-switch enabled', cls: 'install-log__line--ok' },
      ],
    },
    {
      id:       'step-finalize',
      label:    'Finalizing Configuration',
      duration: 1000,
      logs: [
        { text: '» Writing configuration...', cls: 'install-log__line--info' },
        { text: '✓ .env template created', cls: 'install-log__line--ok' },
        { text: '✓ SYSTEM READY', cls: 'install-log__line--ok' },
      ],
    },
  ];

  /* ── STATE ───────────────────────────────────────────────── */
  let selectedPlatform = null;
  let currentStepIndex = 0;
  let totalDuration = LOADING_STEPS.reduce((s, step) => s + step.duration, 0);
  let elapsedDuration = 0;

  /* ── ELEMENTS ────────────────────────────────────────────── */
  const stages = {
    loading:  document.getElementById('stage-loading'),
    confirm:  document.getElementById('stage-confirm'),
    download: document.getElementById('stage-download'),
  };

  const progressFill  = document.getElementById('progress-fill');
  const progressPct   = document.getElementById('progress-pct');
  const progressStatus= document.getElementById('progress-status');
  const installLog    = document.getElementById('install-log');
  const installProgressBar = document.getElementById('install-progress-bar');

  const confirmYesBtn = document.getElementById('confirm-yes-btn');
  const confirmNoBtn  = document.getElementById('confirm-no-btn');
  const platformBtns  = document.querySelectorAll('.platform-btn');

  const downloadFill      = document.getElementById('download-fill');
  const downloadPct       = document.getElementById('download-pct');
  const downloadStatus    = document.getElementById('download-status');
  const downloadLog       = document.getElementById('download-log');
  const downloadSpeed     = document.getElementById('download-speed');
  const downloadTitle     = document.getElementById('download-title');
  const downloadPlatLabel = document.getElementById('download-platform-label');
  const downloadProgressBar = document.getElementById('download-progress-bar');

  /* ── STAGE MANAGER ───────────────────────────────────────── */
  function showStage(name) {
    Object.entries(stages).forEach(([key, el]) => {
      if (!el) return;
      el.classList.remove('is-active');
    });
    if (stages[name]) {
      stages[name].classList.add('is-active');
    }
  }

  /* ── LOG MANAGER ─────────────────────────────────────────── */
  function addLog(container, text, cls = '') {
    if (!container) return;
    const line = document.createElement('span');
    line.className = 'install-log__line ' + cls;
    line.textContent = text;
    container.appendChild(line);
    container.scrollTop = container.scrollHeight;
  }

  /* ── PROGRESS UPDATE ─────────────────────────────────────── */
  function setProgress(fill, pct, bar, percent) {
    const p = Math.round(Math.min(100, Math.max(0, percent)));
    if (fill) fill.style.width = p + '%';
    if (pct)  pct.textContent  = p + '%';
    if (bar)  bar.setAttribute('aria-valuenow', p);
  }

  /* ── STEP MANAGER ────────────────────────────────────────── */
  function setStepState(stepEl, state) {
    if (!stepEl) return;
    stepEl.classList.remove(
      'install-step-item--active',
      'install-step-item--done'
    );

    const icon   = stepEl.querySelector('.install-step-item__icon');
    const status = stepEl.querySelector('.install-step-item__status');

    if (state === 'active') {
      stepEl.classList.add('install-step-item--active');
      if (icon)   icon.textContent   = '⟳';
      if (status) status.textContent = 'RUNNING';
      stepEl.style.opacity = '1';
    } else if (state === 'done') {
      stepEl.classList.add('install-step-item--done');
      if (icon)   icon.textContent   = '✓';
      if (status) status.textContent = 'DONE';
    } else {
      stepEl.style.opacity = '0.3';
      if (icon)   icon.textContent   = '⊡';
      if (status) status.textContent = 'PENDING';
    }
  }

  /* ── RUN LOADING SEQUENCE ────────────────────────────────── */
  async function runLoadingSequence() {
    for (let i = 0; i < LOADING_STEPS.length; i++) {
      const step   = LOADING_STEPS[i];
      const stepEl = document.getElementById(step.id);

      currentStepIndex = i;

      // Activate current step
      setStepState(stepEl, 'active');
      if (progressStatus) progressStatus.textContent = step.label.toUpperCase();

      // Add logs with small delays
      for (let j = 0; j < step.logs.length; j++) {
        await delay(step.duration / (step.logs.length + 1));
        addLog(installLog, step.logs[j].text, step.logs[j].cls);

        // Update progress
        elapsedDuration += step.duration / (step.logs.length + 1);
        const pct = (elapsedDuration / totalDuration) * 100;
        setProgress(progressFill, progressPct, installProgressBar, pct);
      }

      // Mark done
      setStepState(stepEl, 'done');
    }

    // Final progress
    setProgress(progressFill, progressPct, installProgressBar, 100);
    if (progressStatus) progressStatus.textContent = 'COMPLETE';

    await delay(600);

    // Transition to confirm stage
    showStage('confirm');
  }

  /* ── PLATFORM SELECTION ──────────────────────────────────── */
  function initPlatformSelection() {
    platformBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        platformBtns.forEach(b => {
          b.classList.remove('is-selected');
          b.setAttribute('aria-pressed', 'false');
        });
        btn.classList.add('is-selected');
        btn.setAttribute('aria-pressed', 'true');
        selectedPlatform = btn.dataset.platform;

        // Enable confirm button
        if (confirmYesBtn) {
          confirmYesBtn.disabled = false;
        }
      });
    });
  }

  /* ── DOWNLOAD SEQUENCE ───────────────────────────────────── */
  const PLATFORM_LABELS = {
    windows: { name: 'Windows',     ext: '.exe',      icon: '🪟' },
    macos:   { name: 'macOS',       ext: '.dmg',      icon: '🍎' },
    linux:   { name: 'Linux',       ext: '.AppImage', icon: '🐧' },
    android: { name: 'Android APK', ext: '.apk',      icon: '📱' },
    web:     { name: 'Web App',     ext: '.pwa',      icon: '🌐' },
    all:     { name: 'All Platforms','ext': 'bundle',  icon: '⚡' },
  };

  const DOWNLOAD_LOGS = [
    { text: '» Connecting to GitHub Releases...',       cls: 'install-log__line--info',  pct: 5  },
    { text: '✓ Release tag found: v2.5.0',              cls: 'install-log__line--ok',    pct: 15 },
    { text: '» Fetching build artifact...',             cls: 'install-log__line--info',  pct: 25 },
    { text: '✓ Checksum verified',                      cls: 'install-log__line--ok',    pct: 40 },
    { text: '» Downloading package...',                 cls: 'install-log__line--info',  pct: 55 },
    { text: '✓ 25% — 50% — 75% — 90%',                cls: 'install-log__line--ok',    pct: 85 },
    { text: '✓ Download complete',                      cls: 'install-log__line--ok',    pct: 95 },
    { text: '⚡ Opening installer...',                  cls: '',                          pct: 100 },
  ];

  async function runDownloadSequence() {
    const info = PLATFORM_LABELS[selectedPlatform] || PLATFORM_LABELS.windows;

    // Update download stage UI
    if (downloadTitle)
      downloadTitle.textContent = `DOWNLOADING ${info.name.toUpperCase()}`;
    if (downloadPlatLabel)
      downloadPlatLabel.textContent = `[ ${info.icon} ${info.name} ${info.ext} ]`;

    showStage('download');

    for (const log of DOWNLOAD_LOGS) {
      await delay(600 + Math.random() * 400);
      addLog(downloadLog, log.text, log.cls);
      setProgress(downloadFill, downloadPct, downloadProgressBar, log.pct);

      if (downloadStatus) {
        downloadStatus.textContent = log.pct < 100
          ? `DOWNLOADING... ${log.pct}%`
          : 'COMPLETE';
      }

      // Fake speed indicator
      if (downloadSpeed && log.pct > 10 && log.pct < 100) {
        const speed = (2.4 + Math.random() * 8).toFixed(1);
        downloadSpeed.textContent = `${speed} MB/s — GitHub CDN`;
      }
    }

    // Final state
    if (downloadSpeed) downloadSpeed.textContent = '— Download Complete —';

    await delay(1000);

    // Redirect to GitHub releases
    triggerGitHubDownload(selectedPlatform);
  }

  function triggerGitHubDownload(platform) {
    const GITHUB_RELEASE_BASE =
      'https://github.com/YOUR_USERNAME/shadowforge-os/releases/latest/download/';

    const FILES = {
      windows: 'ShadowForge-Setup-Windows.exe',
      macos:   'ShadowForge-macOS.dmg',
      linux:   'ShadowForge-Linux.AppImage',
      android: 'ShadowForge-Android.apk',
      web:     'ShadowForge-Web.zip',
      all:     'ShadowForge-All-Platforms.zip',
    };

    const filename = FILES[platform] || FILES.windows;
    const url = GITHUB_RELEASE_BASE + filename;

    // Create invisible anchor and click
    const a = document.createElement('a');
    a.href     = url;
    a.download = filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // Show completion message
    if (downloadLog) {
      addLog(
        downloadLog,
        '✓ Browser download started. Check your downloads folder.',
        'install-log__line--ok'
      );
    }
  }

  /* ── CONFIRM ACTIONS ─────────────────────────────────────── */
  function initConfirmActions() {
    if (confirmYesBtn) {
      confirmYesBtn.addEventListener('click', () => {
        if (!selectedPlatform) return;
        runDownloadSequence();
      });
    }

    if (confirmNoBtn) {
      confirmNoBtn.addEventListener('click', () => {
        window.location.href = 'index.html';
      });
    }
  }

  /* ── UTILITY ─────────────────────────────────────────────── */
  function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /* ── AUTO-DETECT PLATFORM ────────────────────────────────── */
  function autoDetectPlatform() {
    const ua = navigator.userAgent.toLowerCase();
    let detected = 'windows';

    if (ua.includes('android'))           detected = 'android';
    else if (ua.includes('iphone') ||
             ua.includes('ipad'))          detected = 'web';
    else if (ua.includes('mac'))           detected = 'macos';
    else if (ua.includes('linux'))         detected = 'linux';
    else if (ua.includes('win'))           detected = 'windows';

    // Pre-select detected platform
    const detectedBtn = document.querySelector(
      `.platform-btn[data-platform="${detected}"]`
    );

    if (detectedBtn) {
      detectedBtn.classList.add('is-selected');
      detectedBtn.setAttribute('aria-pressed', 'true');
      selectedPlatform = detected;

      // Add badge
      const badge = document.createElement('span');
      badge.style.cssText = `
        position:absolute; top:-8px; right:-8px;
        background:#ff0015; color:#fff;
        font-size:0.55rem; padding:2px 5px;
        border-radius:2px; letter-spacing:0.1em;
        font-family:'Share Tech Mono',monospace;
      `;
      badge.textContent = 'DETECTED';
      detectedBtn.style.position = 'relative';
      detectedBtn.appendChild(badge);

      // Enable confirm button
      if (confirmYesBtn) confirmYesBtn.disabled = false;
    }
  }

  /* ── INIT ────────────────────────────────────────────────── */
  function init() {
    if (!stages.loading) return;

    initPlatformSelection();
    initConfirmActions();

    // Start loading sequence after short delay
    setTimeout(() => {
      runLoadingSequence().then(() => {
        autoDetectPlatform();
      });
    }, 500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();