/**
 * HerGlory Media CMS — app.js
 * Pure Vanilla JS. No frameworks.
 *
 * Flow:
 *  Login → Dashboard → New Post (configure) → Posting progress → Dashboard
 *
 * NOTE: All API calls are SIMULATED (setTimeout).
 * When the FastAPI backend is ready, replace the simulate* functions
 * with real fetch() calls to your endpoints.
 */

'use strict';

/* ══════════════════════════════════════════════════
   CREDENTIALS (hardcoded for v1 demo)
   TODO: Replace with real FastAPI JWT auth endpoint
══════════════════════════════════════════════════ */
const DEMO_EMAIL    = 'admin@herglory.org';
const DEMO_PASSWORD = 'glory2026';

/* ══════════════════════════════════════════════════
   IN-MEMORY STATE
══════════════════════════════════════════════════ */
let state = {
  loggedIn:    false,
  user:        null,
  posts:       [],           // list of submitted posts
  mediaFile:   null,         // currently selected File object
  mediaType:   null,         // 'photo' | 'video'
  mediaURL:    null,         // object URL for preview
};

/* ══════════════════════════════════════════════════
   DOM REFS
══════════════════════════════════════════════════ */
// Screens
const screenLogin    = document.getElementById('screen-login');
const screenDashboard= document.getElementById('screen-dashboard');
const screenNewpost  = document.getElementById('screen-newpost');
const screenPosting  = document.getElementById('screen-posting');

// Login
const inpEmail       = document.getElementById('inp-email');
const inpPass        = document.getElementById('inp-pass');
const loginBtn       = document.getElementById('login-btn');
const loginErr       = document.getElementById('login-err');
const pwEye          = document.getElementById('pw-eye');

// Dashboard
const topbarLogout   = document.getElementById('topbar-logout');
const topbarUser     = document.getElementById('topbar-user');
const goNewPost      = document.getElementById('go-new-post');
const statMedia      = document.getElementById('stat-media');
const dashDate       = document.getElementById('dash-date');
const recentList     = document.getElementById('recent-list');
const emptyState     = document.getElementById('empty-state');
const navPostBtn     = document.getElementById('nav-post-btn');

// New post
const backFromPost   = document.getElementById('back-from-post');
const dropZone       = document.getElementById('drop-zone');
const dropLabelWrap  = document.getElementById('drop-label-wrap');
const mediaInput     = document.getElementById('media-input');
const mediaPreview   = document.getElementById('media-preview');
const previewImg     = document.getElementById('preview-img');
const previewVid     = document.getElementById('preview-vid');
const audioPreview   = document.getElementById('audio-preview');
const previewAudio   = document.getElementById('preview-audio');
const audioFilename  = document.getElementById('audio-filename');
const audioNote      = document.getElementById('audio-note');
const photoModeNote  = document.getElementById('photo-mode-note');
const previewBadge   = document.getElementById('preview-badge');
const previewRemove  = document.getElementById('preview-remove');
const postTitle      = document.getElementById('post-title');
const postCaption    = document.getElementById('post-caption');
const platformToggles= document.querySelectorAll('.platform-toggle');
const postNowBtn     = document.getElementById('post-now-btn');
const postError      = document.getElementById('post-error');
const navDashFromPost= document.getElementById('nav-dash-from-post');

// Posting screen
const postingThumb   = document.getElementById('posting-thumb');
const postingTitleDisplay = document.getElementById('posting-title-display');
const postingPlatforms = document.getElementById('posting-platforms');
const postingLoader  = document.getElementById('posting-loader');
const postingDone    = document.getElementById('posting-done');
const goDashboardBtn = document.getElementById('go-dashboard-btn');


/* ══════════════════════════════════════════════════
   SCREEN ROUTER
   switchScreen(id) — id matches the DOM id e.g. 'screen-login'
══════════════════════════════════════════════════ */
function switchScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}


/* ══════════════════════════════════════════════════
   LOGIN
══════════════════════════════════════════════════ */
loginBtn.addEventListener('click', handleLogin);
[inpEmail, inpPass].forEach(el => el.addEventListener('keydown', e => {
  if (e.key === 'Enter') handleLogin();
}));

pwEye.addEventListener('click', () => {
  inpPass.type = inpPass.type === 'password' ? 'text' : 'password';
});

function handleLogin() {
  const email = inpEmail.value.trim();
  const pass  = inpPass.value;

  /*
   * TODO (FastAPI): Replace with:
   * const res = await fetch('/api/auth/login', {
   *   method: 'POST',
   *   headers: { 'Content-Type': 'application/json' },
   *   body: JSON.stringify({ email, password: pass })
   * });
   * const data = await res.json();
   * if (!res.ok) { show error }
   * else { store JWT token, proceed }
   */

  if (email === DEMO_EMAIL && pass === DEMO_PASSWORD) {
    loginErr.setAttribute('hidden', '');
    state.loggedIn = true;
    state.user = { name: 'Pastor Mrs. Lubega', email };
    topbarUser.textContent = state.user.name;
    updateDashboard();
    switchScreen('screen-dashboard');
  } else {
    loginErr.removeAttribute('hidden');
    // Shake the button
    loginBtn.style.transition = 'none';
    loginBtn.style.transform = 'translateX(-8px)';
    setTimeout(() => { loginBtn.style.transform = 'translateX(8px)'; }, 80);
    setTimeout(() => { loginBtn.style.transform = ''; loginBtn.style.transition = ''; }, 160);
    inpPass.value = '';
    inpPass.focus();
  }
}


/* ══════════════════════════════════════════════════
   LOGOUT
══════════════════════════════════════════════════ */
topbarLogout.addEventListener('click', () => {
  state.loggedIn = false;
  state.user     = null;
  inpEmail.value = '';
  inpPass.value  = '';
  switchScreen('screen-login');
});


/* ══════════════════════════════════════════════════
   DASHBOARD
══════════════════════════════════════════════════ */
function updateDashboard() {
  // Date
  dashDate.textContent = new Date().toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric'
  });

  // Stats
  statMedia.textContent = state.posts.length;

  // Recent posts list
  renderRecentPosts();
}

function renderRecentPosts() {
  // Clear everything except the empty state div
  Array.from(recentList.children).forEach(c => {
    if (c.id !== 'empty-state') c.remove();
  });

  if (state.posts.length === 0) {
    emptyState.removeAttribute('hidden');
    return;
  }

  emptyState.setAttribute('hidden', '');

  // Show newest first
  [...state.posts].reverse().forEach((post, i) => {
    const card = document.createElement('div');
    card.className = 'post-card';
    card.style.animationDelay = `${i * 0.05}s`;

    // Thumbnail
    let thumbHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>';
    if (post.mediaType === 'audio') {
      thumbHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>';
    } else if (post.mediaURL) {
      if (post.mediaType === 'photo') {
        thumbHTML = `<img src="${post.mediaURL}" alt="${escHtml(post.title)}" />`;
      } else {
        thumbHTML = `<video src="${post.mediaURL}" muted></video>`;
      }
    }

    // Platform pills
    const pillsHTML = post.platforms.map(p => `
      <span class="platform-pill pill-${p}">${platformLabel(p)}</span>
    `).join('');

    card.innerHTML = `
      <div class="post-card-thumb">${thumbHTML}</div>
      <div class="post-card-info">
        <div class="post-card-title">${escHtml(post.title)}</div>
        <div class="post-card-platforms">${pillsHTML}</div>
        <div class="post-card-meta">${post.date} · ${post.mediaType}</div>
      </div>
    `;

    recentList.appendChild(card);
  });
}

// Navigate to new post screen
goNewPost.addEventListener('click', () => {
  resetNewPostForm();
  switchScreen('screen-newpost');
  setNavActive(screenNewpost, 'new-post');
});

navPostBtn.addEventListener('click', () => {
  resetNewPostForm();
  switchScreen('screen-newpost');
  setNavActive(screenNewpost, 'new-post');
});


/* ══════════════════════════════════════════════════
   NEW POST — MEDIA SELECTION
   FIX: The previous version attached a click listener on the
   whole drop-zone AND had a full-cover hidden <input>, so a
   single tap fired the native picker via the input's own click
   AND the parent's click handler (which called .click() again),
   causing a double-open. The remove button's click also bubbled
   up into that same handler, re-opening the picker instead of
   just clearing the preview.
   FIX: Now the <label for="media-input"> is the ONLY click
   trigger (native, no JS needed to open the picker). The preview
   + remove button live as a SEPARATE absolutely-positioned layer
   that sits on top and is NOT inside the label, so clicks on the
   remove button never bubble into a picker-opening element.
══════════════════════════════════════════════════ */

mediaInput.addEventListener('change', () => {
  const file = mediaInput.files[0];
  if (file) loadMediaFile(file);
});

// Drag & drop support (still works on the outer drop-zone)
dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer?.files[0];
  if (file) {
    // Reflect dropped file into the input so mediaInput.files stays in sync
    const dt = new DataTransfer();
    dt.items.add(file);
    mediaInput.files = dt.files;
    loadMediaFile(file);
  }
});

function loadMediaFile(file) {
  // Revoke previous object URL to avoid memory leaks
  if (state.mediaURL) URL.revokeObjectURL(state.mediaURL);

  const isVideo = file.type.startsWith('video/');
  const isImage = file.type.startsWith('image/');
  const isAudio = file.type.startsWith('audio/');

  if (!isVideo && !isImage && !isAudio) {
    alert('Please select a photo (JPG, PNG), video (MP4, MOV) or audio file (MP3, WAV).');
    return;
  }

  state.mediaFile = file;
  state.mediaType = isVideo ? 'video' : isImage ? 'photo' : 'audio';
  state.mediaURL  = URL.createObjectURL(file);

  // Hide the picker label, show the preview layer on top of it
  dropLabelWrap.style.visibility = 'hidden';
  mediaPreview.removeAttribute('hidden');
  previewBadge.textContent = state.mediaType;

  // Reset all preview elements first
  previewImg.setAttribute('hidden', '');
  previewVid.setAttribute('hidden', '');
  audioPreview.setAttribute('hidden', '');

  if (isImage) {
    previewImg.src = state.mediaURL;
    previewImg.removeAttribute('hidden');
  } else if (isVideo) {
    previewVid.src = state.mediaURL;
    previewVid.removeAttribute('hidden');
  } else {
    // Audio
    previewAudio.src = state.mediaURL;
    audioFilename.textContent = file.name;
    audioPreview.removeAttribute('hidden');
  }

  // Auto-fill title from filename (strip extension)
  if (!postTitle.value) {
    postTitle.value = file.name.replace(/\.[^.]+$/, '');
  }

  applyMediaTypeRules();
}

// Remove media — separate element, NOT nested inside the picker label,
// so this click can never re-trigger the file picker.
previewRemove.addEventListener('click', () => {
  clearMediaPreview();
});

function clearMediaPreview() {
  if (state.mediaURL) URL.revokeObjectURL(state.mediaURL);
  state.mediaFile = null;
  state.mediaType = null;
  state.mediaURL  = null;
  mediaInput.value = '';

  previewImg.src = '';
  previewVid.src = '';
  previewAudio.src = '';
  previewImg.setAttribute('hidden', '');
  previewVid.setAttribute('hidden', '');
  audioPreview.setAttribute('hidden', '');
  mediaPreview.setAttribute('hidden', '');

  // Restore the picker label
  dropLabelWrap.style.visibility = 'visible';

  applyMediaTypeRules();
}

/* ══════════════════════════════════════════════════
   PLATFORM AVAILABILITY RULES BY MEDIA TYPE
   - photo  → YouTube & YouTube Shorts unsupported (auto-disabled)
   - video  → all platforms supported
   - audio  → all platforms supported, but converted to a
              waveform video server-side before posting
══════════════════════════════════════════════════ */
function applyMediaTypeRules() {
  const isPhoto = state.mediaType === 'photo';

  document.querySelectorAll('.platform-card').forEach(card => {
    const key = card.dataset.platform;
    const toggle = card.querySelector('.platform-toggle');
    const disabledForPhoto = (key === 'youtube' || key === 'ytshorts');

    if (isPhoto && disabledForPhoto) {
      card.classList.add('disabled');
      toggle.checked = false;
    } else {
      card.classList.remove('disabled');
    }
    card.classList.toggle('enabled', toggle.checked && !card.classList.contains('disabled'));
  });

  // Show/hide the photo-mode notice
  photoModeNote.toggleAttribute('hidden', !isPhoto);

  // Show/hide the audio conversion notice
  audioNote.toggleAttribute('hidden', state.mediaType !== 'audio');
}


/* ══════════════════════════════════════════════════
   NEW POST — PLATFORM TOGGLES
══════════════════════════════════════════════════ */
platformToggles.forEach(toggle => {
  toggle.addEventListener('change', () => {
    const card = toggle.closest('.platform-card');
    // Ignore toggle attempts on disabled cards (shouldn't fire due to
    // pointer-events:none, but guard anyway for keyboard/script access)
    if (card.classList.contains('disabled')) {
      toggle.checked = false;
      return;
    }
    card.classList.toggle('enabled', toggle.checked);
  });
  // Set initial state
  if (toggle.checked) toggle.closest('.platform-card').classList.add('enabled');
});

function getSelectedPlatforms() {
  return Array.from(platformToggles)
    .filter(t => t.checked)
    .map(t => t.dataset.key);
}


/* ══════════════════════════════════════════════════
   NEW POST — POST NOW
══════════════════════════════════════════════════ */
postNowBtn.addEventListener('click', handlePostNow);

function handlePostNow() {
  const title     = postTitle.value.trim();
  const platforms = getSelectedPlatforms();

  // Validation
  if (!title || platforms.length === 0) {
    postError.removeAttribute('hidden');
    setTimeout(() => postError.setAttribute('hidden', ''), 3000);
    if (!title) { postTitle.focus(); postTitle.style.borderColor = 'var(--error)'; setTimeout(() => postTitle.style.borderColor = '', 1500); }
    return;
  }

  postError.setAttribute('hidden', '');

  // Switch to posting screen and start the simulation
  switchScreen('screen-posting');
  startPosting(title, platforms);
}


/* ══════════════════════════════════════════════════
   POSTING SCREEN — SIMULATED UPLOAD PROGRESS
   TODO: Replace simulatePlatformPost() with real
   fetch('/api/posts/create', { method:'POST', body: formData })
   when FastAPI backend is ready.
══════════════════════════════════════════════════ */
function startPosting(title, platforms) {
  // Reset posting screen
  postingDone.setAttribute('hidden', '');
  postingLoader.removeAttribute('hidden');
  postingPlatforms.innerHTML = '';
  postingTitleDisplay.textContent = title;

  // Show media thumb on posting screen
  if (state.mediaURL && state.mediaType === 'photo') {
    postingThumb.innerHTML = `<img src="${state.mediaURL}" alt="thumb" />`;
  } else if (state.mediaURL && state.mediaType === 'video') {
    postingThumb.innerHTML = `<video src="${state.mediaURL}" muted></video>`;
  } else if (state.mediaURL && state.mediaType === 'audio') {
    postingThumb.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>`;
  } else {
    postingThumb.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`;
  }

  // Build platform rows — all start as "Uploading..."
  const rowMap = {};
  platforms.forEach(p => {
    const row = buildPostingRow(p, 'uploading');
    postingPlatforms.appendChild(row);
    rowMap[p] = row;
  });

  /*
   * Simulate staggered upload results per platform.
   * In production: use real SSE (Server-Sent Events) or polling
   * from your FastAPI backend to get live status per platform.
   */
  let completed = 0;
  platforms.forEach((p, i) => {
    // Each platform resolves at a different delay to feel real
    const delay = 1200 + i * 900 + Math.random() * 500;
    setTimeout(() => {
      // 90% success rate in demo
      const success = Math.random() > 0.1;
      updatePostingRow(rowMap[p], success ? 'complete' : 'failed');
      completed++;

      if (completed === platforms.length) {
        // All done
        setTimeout(() => {
          postingLoader.setAttribute('hidden', '');
          postingDone.removeAttribute('hidden');

          // Save post to state
          state.posts.push({
            id:        Date.now(),
            title,
            caption:   postCaption.value.trim(),
            platforms,
            mediaType: state.mediaType || 'photo',
            mediaURL:  state.mediaURL,
            date:      new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
          });
        }, 600);
      }
    }, delay);
  });
}

function buildPostingRow(platform, status) {
  const row = document.createElement('div');
  row.className = 'posting-row';
  row.dataset.platform = platform;

  row.innerHTML = `
    <div class="posting-row-logo ${platform}-logo">${platformIconSVG(platform)}</div>
    <span class="posting-row-name">${platformLabel(platform)}</span>
    <span class="posting-status status-uploading">
      <span class="status-spin"></span> Uploading…
    </span>
  `;
  return row;
}

function updatePostingRow(row, status) {
  const statusEl = row.querySelector('.posting-status');
  if (status === 'complete') {
    statusEl.className = 'posting-status status-complete';
    statusEl.innerHTML = '✓ Complete';
  } else if (status === 'failed') {
    statusEl.className = 'posting-status status-failed';
    statusEl.innerHTML = '✕ Failed';
  } else if (status === 'queued') {
    statusEl.className = 'posting-status status-queued';
    statusEl.innerHTML = '⏳ Queued';
  }
}

// Return to dashboard after posting
goDashboardBtn.addEventListener('click', () => {
  updateDashboard();
  switchScreen('screen-dashboard');
  setNavActive(screenDashboard, 'dashboard');
  resetNewPostForm();
});


/* ══════════════════════════════════════════════════
   NAVIGATION — Back / Bottom nav
══════════════════════════════════════════════════ */
backFromPost.addEventListener('click', () => {
  switchScreen('screen-dashboard');
  setNavActive(screenDashboard, 'dashboard');
});

navDashFromPost.addEventListener('click', () => {
  switchScreen('screen-dashboard');
  setNavActive(screenDashboard, 'dashboard');
  updateDashboard();
});

// Keep bottom nav active state in sync
function setNavActive(screenEl, activeKey) {
  screenEl.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.nav === activeKey);
  });
}


/* ══════════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════════ */
function resetNewPostForm() {
  clearMediaPreview();
  postTitle.value   = '';
  postCaption.value = '';
  postError.setAttribute('hidden', '');
  // Reset toggles to default (all on except ytshorts)
  platformToggles.forEach(t => {
    t.checked = t.dataset.key !== 'ytshorts';
  });
  // clearMediaPreview() already calls applyMediaTypeRules(), which will
  // re-sync .enabled/.disabled classes based on current toggle states
  applyMediaTypeRules();
}

function platformLabel(key) {
  const map = {
    tiktok:    'TikTok',
    instagram: 'Instagram',
    youtube:   'YouTube',
    ytshorts:  'YouTube Shorts',
    facebook:  'Facebook',
  };
  return map[key] || key;
}

// Minimal inline SVG per platform (for posting screen rows)
function platformIconSVG(key) {
  const svgs = {
    tiktok: `<svg viewBox="0 0 32 32" width="18" height="18" fill="white"><path d="M21.2 2h-4.4v19.4a4.8 4.8 0 0 1-4.8 4.6 4.8 4.8 0 0 1-4.8-4.8 4.8 4.8 0 0 1 4.8-4.8c.46 0 .9.06 1.32.18V12.1a9.24 9.24 0 0 0-1.32-.1A9.2 9.2 0 0 0 2.8 21.2 9.2 9.2 0 0 0 12 30.4a9.2 9.2 0 0 0 9.2-9.2V11.1a13.5 13.5 0 0 0 8 2.6V9.28A9.24 9.24 0 0 1 21.2 2z"/></svg>`,
    instagram: `<svg viewBox="0 0 24 24" width="18" height="18" fill="white"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4" fill="none" stroke="white" stroke-width="1.5"/><circle cx="17.5" cy="6.5" r="1" fill="white"/></svg>`,
    youtube: `<svg viewBox="0 0 24 24" width="18" height="18" fill="white"><path d="M22.54 6.42a2.78 2.78 0 0 0-1.95-1.96C18.88 4 12 4 12 4s-6.88 0-8.59.46A2.78 2.78 0 0 0 1.46 6.42 29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58 2.78 2.78 0 0 0 1.95 1.96C5.12 20 12 20 12 20s6.88 0 8.59-.46a2.78 2.78 0 0 0 1.95-1.96A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58zM9.75 15.02V8.98L15.5 12l-5.75 3.02z"/></svg>`,
    ytshorts: `<svg viewBox="0 0 24 24" width="18" height="18" fill="white"><path d="M22.54 6.42a2.78 2.78 0 0 0-1.95-1.96C18.88 4 12 4 12 4s-6.88 0-8.59.46A2.78 2.78 0 0 0 1.46 6.42 29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58 2.78 2.78 0 0 0 1.95 1.96C5.12 20 12 20 12 20s6.88 0 8.59-.46a2.78 2.78 0 0 0 1.95-1.96A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58zM9.75 15.02V8.98L15.5 12l-5.75 3.02z"/></svg>`,
    facebook: `<svg viewBox="0 0 24 24" width="18" height="18" fill="white"><path d="M22 12.06C22 6.51 17.52 2 12 2S2 6.51 2 12.06c0 5 3.66 9.13 8.44 9.94v-7.03H7.9v-2.91h2.54V9.84c0-2.51 1.49-3.9 3.77-3.9 1.09 0 2.24.2 2.24.2v2.47h-1.26c-1.24 0-1.63.77-1.63 1.56v1.87h2.78l-.45 2.91h-2.33V22c4.78-.81 8.44-4.94 8.44-9.94z"/></svg>`,
  };
  return svgs[key] || '';
}

function escHtml(str) {
  const map = { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' };
  return String(str).replace(/[&<>"']/g, m => map[m]);
}


/* ══════════════════════════════════════════════════
   PWA — INSTALL PROMPT & SERVICE WORKER
   The 'beforeinstallprompt' event fires on Chrome/Edge/Android
   when the app meets installability criteria (manifest + SW +
   HTTPS). We capture it, stash it, and trigger it from our own
   "Install" button in the dashboard banner — this gives a much
   nicer UX than the browser's auto-popup.
   iOS Safari doesn't fire this event at all (Apple's choice);
   "Add to Home Screen" there is manual via the Share sheet, so
   the banner simply won't appear on iOS — that's expected.
══════════════════════════════════════════════════ */
let deferredInstallPrompt = null;

const installBanner  = document.getElementById('install-banner');
const installBtn     = document.getElementById('install-btn');
const installDismiss = document.getElementById('install-dismiss');

window.addEventListener('beforeinstallprompt', (e) => {
  // Prevent the default mini-infobar from appearing automatically
  e.preventDefault();
  deferredInstallPrompt = e;

  // Only show the banner if the user hasn't dismissed it before
  // and isn't already running the installed app
  const dismissed = sessionStorage.getItem('installBannerDismissed');
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches;

  if (!dismissed && !isStandalone) {
    installBanner.removeAttribute('hidden');
  }
});

installBtn?.addEventListener('click', async () => {
  if (!deferredInstallPrompt) return;
  deferredInstallPrompt.prompt();
  const { outcome } = await deferredInstallPrompt.userChoice;
  // Hide banner regardless of outcome — prompt can only be used once
  installBanner.setAttribute('hidden', '');
  deferredInstallPrompt = null;
  if (outcome === 'accepted') {
    sessionStorage.setItem('installBannerDismissed', 'true');
  }
});

installDismiss?.addEventListener('click', () => {
  installBanner.setAttribute('hidden', '');
  sessionStorage.setItem('installBannerDismissed', 'true');
});

// If the app gets installed via any path, hide the banner & remember it
window.addEventListener('appinstalled', () => {
  installBanner.setAttribute('hidden', '');
  sessionStorage.setItem('installBannerDismissed', 'true');
});

// Register service worker for offline support + installability
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {
      // Fails silently if served from file:// or unsupported context —
      // the app still works fully online without it.
    });
  });
}


/* ══════════════════════════════════════════════════
   INIT
══════════════════════════════════════════════════ */
switchScreen('screen-login');
