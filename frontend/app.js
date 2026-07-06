/**
 * HerGlory Media CMS — app.js
 * Pure Vanilla JS. No frameworks.
 */

'use strict';

const DEMO_EMAIL = 'admin@herglory.org';
const DEMO_PASSWORD = 'glory2026';

let state = {
  loggedIn: false,
  user: null,
  posts: [],
  mediaFile: null,
  mediaType: null,
  mediaURL: null,
  tiktokConnected: false,
  youtubeConnected: false,
};

// DOM REFS
const ttStatus = document.getElementById('tt-status');
const ttConnectBtn = document.getElementById('tt-connect-btn');
const ytStatus = document.getElementById('yt-status');
const ytConnectBtn = document.getElementById('yt-connect-btn');

const screenLogin = document.getElementById('screen-login');
const screenDashboard = document.getElementById('screen-dashboard');
const screenNewpost = document.getElementById('screen-newpost');
const screenPosting = document.getElementById('screen-posting');

const inpEmail = document.getElementById('inp-email');
const inpPass = document.getElementById('inp-pass');
const loginBtn = document.getElementById('login-btn');
const loginErr = document.getElementById('login-err');
const pwEye = document.getElementById('pw-eye');

const topbarLogout = document.getElementById('topbar-logout');
const topbarUser = document.getElementById('topbar-user');
const goNewPost = document.getElementById('go-new-post');
const statMedia = document.getElementById('stat-media');
const dashDate = document.getElementById('dash-date');
const recentList = document.getElementById('recent-list');
const emptyState = document.getElementById('empty-state');
const navPostBtn = document.getElementById('nav-post-btn');

const backFromPost = document.getElementById('back-from-post');
const dropZone = document.getElementById('drop-zone');
const dropLabelWrap = document.getElementById('drop-label-wrap');
const mediaInput = document.getElementById('media-input');
const mediaPreview = document.getElementById('media-preview');
const previewImg = document.getElementById('preview-img');
const previewVid = document.getElementById('preview-vid');
const audioPreview = document.getElementById('audio-preview');
const previewAudio = document.getElementById('preview-audio');
const audioFilename = document.getElementById('audio-filename');
const audioNote = document.getElementById('audio-note');
const photoModeNote = document.getElementById('photo-mode-note');
const previewBadge = document.getElementById('preview-badge');
const previewRemove = document.getElementById('preview-remove');
const postTitle = document.getElementById('post-title');
const postCaption = document.getElementById('post-caption');
const platformToggles = document.querySelectorAll('.platform-toggle');
const postNowBtn = document.getElementById('post-now-btn');
const postError = document.getElementById('post-error');
const navDashFromPost = document.getElementById('nav-dash-from-post');

const postingThumb = document.getElementById('posting-thumb');
const postingTitleDisplay = document.getElementById('posting-title-display');
const postingPlatforms = document.getElementById('posting-platforms');
const postingLoader = document.getElementById('posting-loader');
const postingDone = document.getElementById('posting-done');
const goDashboardBtn = document.getElementById('go-dashboard-btn');

function switchScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const target = document.getElementById(id);
  if (target) target.classList.add('active');
}

loginBtn.addEventListener('click', handleLogin);
[inpEmail, inpPass].forEach(el => el.addEventListener('keydown', e => {
  if (e.key === 'Enter') handleLogin();
}));

pwEye.addEventListener('click', () => {
  inpPass.type = inpPass.type === 'password' ? 'text' : 'password';
});

async function handleLogin() {
  const email = inpEmail.value.trim();
  const pass = inpPass.value;

  if (email === DEMO_EMAIL && pass === DEMO_PASSWORD) {
    loginErr.setAttribute('hidden', '');
    state.loggedIn = true;
    state.user = { name: 'Pastor Mrs. Lubega', email };
    if (topbarUser) topbarUser.textContent = state.user.name;
    await updateDashboard();
    switchScreen('screen-dashboard');
    await checkPlatformConnections();
  } else {
    loginErr.removeAttribute('hidden');
    loginBtn.style.transition = 'none';
    loginBtn.style.transform = 'translateX(-8px)';
    setTimeout(() => { loginBtn.style.transform = 'translateX(8px)'; }, 80);
    setTimeout(() => { loginBtn.style.transform = ''; loginBtn.style.transition = ''; }, 160);
    inpPass.value = '';
    inpPass.focus();
  }
}

topbarLogout.addEventListener('click', () => {
  state.loggedIn = false;
  state.user = null;
  inpEmail.value = '';
  inpPass.value = '';
  switchScreen('screen-login');
});

async function updateDashboard() {
  if (dashDate) {
    dashDate.textContent = new Date().toLocaleDateString('en-US', {
      weekday: 'short', month: 'short', day: 'numeric'
    });
  }
  if (statMedia) statMedia.textContent = state.posts.length;
  renderRecentPosts();
}

function renderRecentPosts() {
  if (!recentList) return;
  Array.from(recentList.children).forEach(c => {
    if (c.id !== 'empty-state') c.remove();
  });

  if (state.posts.length === 0) {
    if (emptyState) emptyState.removeAttribute('hidden');
    return;
  }

  if (emptyState) emptyState.setAttribute('hidden', '');

  [...state.posts].reverse().forEach((post, i) => {
    const card = document.createElement('div');
    card.className = 'post-card';
    card.style.animationDelay = `${i * 0.05}s`;

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

goNewPost.addEventListener('click', async () => {
  resetNewPostForm();
  switchScreen('screen-newpost');
  setNavActive(screenNewpost, 'new-post');
  await checkPlatformConnections();
});

navPostBtn.addEventListener('click', async () => {
  resetNewPostForm();
  switchScreen('screen-newpost');
  setNavActive(screenNewpost, 'new-post');
  await checkPlatformConnections();
});

async function checkPlatformConnections() {
  // TikTok Card
  const tiktokCard = document.querySelector('.platform-card[data-platform="tiktok"]');
  const ttStatus = document.getElementById('tt-status');
  const ttConnectBtn = document.getElementById('tt-connect-btn');
  let isTikTokConnected = false;

  try {
    const response = await fetch('/api/auth/status/tiktok');
    if (response.ok) {
      const data = await response.json();
      isTikTokConnected = data.connected;
      state.tiktokConnected = isTikTokConnected;
    }
  } catch (error) {
    console.error("TikTok Verification Network Error:", error);
  }

  if (tiktokCard) {
    const toggle = tiktokCard.querySelector('.platform-toggle');
    if (!isTikTokConnected) {
      tiktokCard.classList.add('disabled');
      if (toggle) { toggle.checked = false; toggle.disabled = true; }
      if (ttStatus) ttStatus.textContent = "Account Not Linked";
      if (ttConnectBtn) ttConnectBtn.style.display = "block";
    } else {
      tiktokCard.classList.remove('disabled');
      if (toggle) toggle.disabled = false;
      if (ttStatus) ttStatus.textContent = "Connected";
      if (ttConnectBtn) ttConnectBtn.style.display = "none";
    }
  }

  // YouTube Card
  const youtubeCard = document.querySelector('.platform-card[data-platform="youtube"]');
  const ytStatus = document.getElementById('yt-status');
  const ytConnectBtn = document.getElementById('yt-connect-btn');
  let isYouTubeConnected = false;

  try {
    const response = await fetch('/api/auth/status/youtube');
    if (response.ok) {
      const data = await response.json();
      isYouTubeConnected = data.connected;
      state.youtubeConnected = isYouTubeConnected;
    }
  } catch (error) {
    console.error("YouTube Verification Network Error:", error);
  }

  if (youtubeCard) {
    const toggle = youtubeCard.querySelector('.platform-toggle');
    const isPhoto = state.mediaType === 'photo';

    if (!isYouTubeConnected) {
      youtubeCard.classList.add('disabled');
      if (toggle) { toggle.checked = false; toggle.disabled = true; }
      if (ytStatus) ytStatus.textContent = "Account Not Linked";
      if (ytConnectBtn) ytConnectBtn.style.display = "block";
    } else if (isPhoto) {
      youtubeCard.classList.add('disabled');
      if (toggle) { toggle.checked = false; toggle.disabled = true; }
      if (ytStatus) ytStatus.textContent = "Connected";
      if (ytConnectBtn) ytConnectBtn.style.display = "none";
    } else {
      youtubeCard.classList.remove('disabled');
      if (toggle) toggle.disabled = false;
      if (ytStatus) ytStatus.textContent = "Connected";
      if (ytConnectBtn) ytConnectBtn.style.display = "none";
    }
  }
}

mediaInput.addEventListener('change', () => {
  const file = mediaInput.files[0];
  if (file) loadMediaFile(file);
});

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
    const dt = new DataTransfer();
    dt.items.add(file);
    mediaInput.files = dt.files;
    loadMediaFile(file);
  }
});

function loadMediaFile(file) {
  if (state.mediaURL) URL.revokeObjectURL(state.mediaURL);

  const isVideo = file.type.startsWith('video/');
  const isImage = file.type.startsWith('image/');
  const isAudio = file.type.startsWith('audio/') || /\.(mp3|wav|m4a|aac)$/i.test(file.name);

  if (!isVideo && !isImage && !isAudio) {
    alert('Please select a photo (JPG, PNG), video (MP4, MOV) or audio file (MP3, WAV).');
    return;
  }

  state.mediaFile = file;
  state.mediaType = isVideo ? 'video' : isImage ? 'photo' : 'audio';
  state.mediaURL = URL.createObjectURL(file);

  if (dropLabelWrap) dropLabelWrap.style.visibility = 'hidden';
  if (mediaPreview) mediaPreview.removeAttribute('hidden');
  if (previewBadge) previewBadge.textContent = state.mediaType;

  if (previewImg) previewImg.setAttribute('hidden', '');
  if (previewVid) previewVid.setAttribute('hidden', '');
  if (audioPreview) audioPreview.setAttribute('hidden', '');

  if (isImage && previewImg) {
    previewImg.src = state.mediaURL;
    previewImg.removeAttribute('hidden');
  } else if (isVideo && previewVid) {
    previewVid.src = state.mediaURL;
    previewVid.removeAttribute('hidden');
  } else if (isAudio && audioPreview) {
    if (previewAudio) previewAudio.src = state.mediaURL;
    if (audioFilename) audioFilename.textContent = file.name;
    audioPreview.removeAttribute('hidden');
  }

  if (postTitle && !postTitle.value) {
    postTitle.value = file.name.replace(/\.[^.]+$/, '');
  }

  applyMediaTypeRules();
}

previewRemove.addEventListener('click', () => {
  clearMediaPreview();
});

function clearMediaPreview() {
  if (state.mediaURL) URL.revokeObjectURL(state.mediaURL);
  state.mediaFile = null;
  state.mediaType = null;
  state.mediaURL = null;
  if (mediaInput) mediaInput.value = '';

  if (previewImg) { previewImg.src = ''; previewImg.setAttribute('hidden', ''); }
  if (previewVid) { previewVid.src = ''; previewVid.setAttribute('hidden', ''); }
  if (previewAudio) previewAudio.src = '';
  if (audioPreview) audioPreview.setAttribute('hidden', '');
  if (mediaPreview) mediaPreview.setAttribute('hidden', '');

  if (dropLabelWrap) dropLabelWrap.style.visibility = 'visible';

  applyMediaTypeRules();
}

function applyMediaTypeRules() {
  const isPhoto = state.mediaType === 'photo';

  document.querySelectorAll('.platform-card').forEach(card => {
    const key = card.dataset.platform;
    const toggle = card.querySelector('.platform-toggle');
    const disabledForPhoto = (key === 'youtube');

    if (isPhoto && disabledForPhoto) {
      card.classList.add('disabled');
      if (toggle) toggle.checked = false;
    } else {
      if (key === 'tiktok' && !state.tiktokConnected) {
        card.classList.add('disabled');
      } else if (key === 'youtube' && !state.youtubeConnected) {
        card.classList.add('disabled');
      } else {
        card.classList.remove('disabled');
      }
    }
    if (toggle) card.classList.toggle('enabled', toggle.checked && !card.classList.contains('disabled'));
  });

  if (photoModeNote) photoModeNote.toggleAttribute('hidden', !isPhoto);
  if (audioNote) audioNote.toggleAttribute('hidden', state.mediaType !== 'audio');
}

platformToggles.forEach(toggle => {
  toggle.addEventListener('change', () => {
    const card = toggle.closest('.platform-card');
    if (card.classList.contains('disabled')) {
      toggle.checked = false;
      return;
    }
    card.classList.toggle('enabled', toggle.checked);
  });
  if (toggle.checked) {
    const card = toggle.closest('.platform-card');
    if (card && !card.classList.contains('disabled')) card.classList.add('enabled');
  }
});

function getSelectedPlatforms() {
  return Array.from(platformToggles)
    .filter(t => t.checked)
    .map(t => t.dataset.platform || t.dataset.key || t.value);
}

postNowBtn.addEventListener('click', handlePostNow);

async function handlePostNow() {
  const title = postTitle.value.trim();
  const platforms = getSelectedPlatforms();

  if (!state.mediaFile) {
    alert('Please select a file to post first.');
    return;
  }

  if (!title || platforms.length === 0) {
    if (postError) postError.removeAttribute('hidden');
    setTimeout(() => postError && postError.setAttribute('hidden', ''), 3000);
    if (!title && postTitle) {
      postTitle.focus();
      postTitle.style.borderColor = 'var(--error)';
      setTimeout(() => { if (postTitle) postTitle.style.borderColor = ''; }, 1500);
    }
    return;
  }

  if (postError) postError.setAttribute('hidden', '');

  let workingTitle = title;

  if (state.mediaType === 'audio') {
    switchScreen('screen-posting');

    if (postingDone) postingDone.setAttribute('hidden', '');
    if (postingLoader) postingLoader.removeAttribute('hidden');
    if (postingTitleDisplay) postingTitleDisplay.textContent = 'Converting audio to video asset...';
    if (postingThumb) postingThumb.innerHTML = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>';

    if (postingPlatforms) {
      postingPlatforms.innerHTML = `
        <div class="posting-row">
          <div class="posting-row-logo" style="background: var(--primary); display: flex; align-items: center; justify-content: center;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
          </div>
          <span class="posting-row-name">MoviePy Engine</span>
          <span class="posting-status status-uploading">
            <span class="status-spin"></span> Rendering video file...
          </span>
        </div>
      `;
    }

    const formData = new FormData();
    formData.append('file', state.mediaFile);

    try {
      const response = await fetch('/api/upload-audio', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (data.status !== 'success') {
        alert(`Video generation failed: ${data.message}`);
        switchScreen('screen-newpost');
        return;
      }

      workingTitle = data.video_file;

    } catch (error) {
      alert('Network processing failed. Check backend connection.');
      switchScreen('screen-newpost');
      return;
    }
  } else {
    switchScreen('screen-posting');
  }

  startPosting(workingTitle, platforms);
}

async function startPosting(title, platforms) {
  if (postingDone) postingDone.setAttribute('hidden', '');
  if (postingLoader) postingLoader.removeAttribute('hidden');
  if (postingPlatforms) postingPlatforms.innerHTML = '';
  if (postingTitleDisplay) postingTitleDisplay.textContent = title;

  if (postingThumb) {
    if (state.mediaURL && state.mediaType === 'photo') {
      postingThumb.innerHTML = `<img src="${state.mediaURL}" alt="thumb" />`;
    } else if (state.mediaURL && state.mediaType === 'video') {
      postingThumb.innerHTML = `<video src="${state.mediaURL}" muted></video>`;
    } else {
      postingThumb.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg> * Rendered`;
    }
  }

  const rowMap = {};
  platforms.forEach(p => {
    const row = buildPostingRow(p, 'uploading');
    if (postingPlatforms) postingPlatforms.appendChild(row);
    rowMap[p] = row;
  });

  for (const p of platforms) {
    if (p === 'tiktok') {
      try {
        const response = await fetch('/api/test-publish/tiktok', { method: 'POST' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();
        if (result.status === 'success') {
          updatePostingRow(rowMap[p], 'complete');
        } else {
          updatePostingRow(rowMap[p], 'failed');
          alert(`TikTok Distribution Interrupted: ${result.error || 'Server Processing Error'}`);
        }
      } catch (err) {
        updatePostingRow(rowMap[p], 'failed');
        alert(`Failed to establish route connection to backend: ${err.message}`);
      }
    } else if (p === 'youtube') {
      try {
        //  FIXED: Explicitly targeting our backend endpoint route structure
        const response = await fetch('/api/test-publish/youtube', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({ video_file: title })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();

        // Handle the 202 Accepted status processing loop safely
        if (result.status === 'success' || result.status === 'processing') {
          updatePostingRow(rowMap[p], 'complete');
        } else {
          updatePostingRow(rowMap[p], 'failed');
          alert(`YouTube Distribution Interrupted: ${result.error || 'Server Processing Error'}`);
        }
      } catch (err) {
        updatePostingRow(rowMap[p], 'failed');
        alert(`Failed to establish route connection to backend: ${err.message}`);
      }
    } else {
      const delay = 1200 + Math.random() * 800;
      await new Promise(resolve => setTimeout(resolve, delay));
      const success = Math.random() > 0.05;
      updatePostingRow(rowMap[p], success ? 'complete' : 'failed');
    }
  }

function buildPostingRow(platform, status) {
  const row = document.createElement('div');
  row.className = 'posting-row';
  row.dataset.platform = platform;

  row.innerHTML = `
    <div class="posting-row-logo ${platform}-logo">${platformIconSVG(platform)}</div>
    <span class="posting-row-name">${platformLabel(platform)}</span>
    <span class="posting-status status-uploading">
      <span class="status-spin"></span> Uploading...
    </span>
  `;
  return row;
}

function updatePostingRow(row, status) {
  if (!row) return;
  const statusEl = row.querySelector('.posting-status');
  if (!statusEl) return;
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

goDashboardBtn.addEventListener('click', () => {
  updateDashboard();
  switchScreen('screen-dashboard');
  setNavActive(screenDashboard, 'dashboard');
  resetNewPostForm();
});

backFromPost.addEventListener('click', () => {
  switchScreen('screen-dashboard');
  setNavActive(screenDashboard, 'dashboard');
});

navDashFromPost.addEventListener('click', () => {
  switchScreen('screen-dashboard');
  setNavActive(screenDashboard, 'dashboard');
  updateDashboard();
});

function setNavActive(screenEl, activeKey) {
  if (!screenEl) return;
  screenEl.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.nav === activeKey);
  });
}

function resetNewPostForm() {
  clearMediaPreview();
  if (postTitle) postTitle.value = '';
  if (postCaption) postCaption.value = '';
  if (postError) postError.setAttribute('hidden', '');
  platformToggles.forEach(t => {
    t.checked = true;
  });
  applyMediaTypeRules();
}

function platformLabel(key) {
  const map = {
    tiktok: 'TikTok',
    instagram: 'Instagram',
    youtube: 'YouTube',
    facebook: 'Facebook',
  };
  return map[key] || key;
}

function platformIconSVG(key) {
  const svgs = {
    tiktok: `<svg viewBox="0 0 32 32" width="18" height="18" fill="white"><path d="M21.2 2h-4.4v19.4a4.8 4.8 0 0 1-4.8 4.6 4.8 4.8 0 0 1-4.8-4.8 4.8 4.8 0 0 1 4.8-4.8c.46 0 .9.06 1.32.18V12.1a9.24 9.24 0 0 0-1.32-.1A9.2 9.2 0 0 0 2.8 21.2 9.2 9.2 0 0 0 12 30.4a9.2 9.2 0 0 0 9.2-9.2V11.1a13.5 13.5 0 0 0 8 2.6V9.28A9.24 9.24 0 0 1 21.2 2z"/></svg>`,
    instagram: `<svg viewBox="0 0 24 24" width="18" height="18" fill="white"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4" fill="none" stroke="white" stroke-width="1.5"/><circle cx="17.5" cy="6.5" r="1" fill="white"/></svg>`,
    youtube: `<svg viewBox="0 0 24 24" width="18" height="18" fill="white"><path d="M22.54 6.42a2.78 2.78 0 0 0-1.95-1.96C18.88 4 12 4 12 4s-6.88 0-8.59.46A2.78 2.78 0 0 0 1.46 6.42 29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58 2.78 2.78 0 0 0 1.95 1.96C5.12 20 12 20 12 20s6.88 0 8.59-.46a2.78 2.78 0 0 0 1.95-1.96A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58zM9.75 15.02V8.98L15.5 12l-5.75 3.02z"/></svg>`,
    facebook: `<svg viewBox="0 0 24 24" width="18" height="18" fill="white"><path d="M22 12.06C22 6.51 17.52 2 12 2S2 6.51 2 12.06c0 5 3.66 9.13 8.44 9.94v-7.03H7.9v-2.91h2.54V9.84c0-2.51 1.49-3.9 3.77-3.9 1.09 0 2.24.2 2.24.2v2.47h-1.26c-1.24 0-1.63.77-1.63 1.56v1.87h2.78l-.45 2.91h-2.33V22c4.78-.81 8.44-4.94 8.44-9.94z"/></svg>`,
  };
  return svgs[key] || '';
}

function escHtml(str) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(str).replace(/[&<>"']/g, m => map[m]);
}

let deferredInstallPrompt = null;
const installBanner = document.getElementById('install-banner');
const installBtn = document.getElementById('install-btn');
const installDismiss = document.getElementById('install-dismiss');

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  const dismissed = sessionStorage.getItem('installBannerDismissed');
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
  if (!dismissed && !isStandalone && installBanner) {
    installBanner.removeAttribute('hidden');
  }
});

installBtn?.addEventListener('click', async () => {
  if (!deferredInstallPrompt) return;
  deferredInstallPrompt.prompt();
  const { outcome } = await deferredInstallPrompt.userChoice;
  if (installBanner) installBanner.setAttribute('hidden', '');
  deferredInstallPrompt = null;
  if (outcome === 'accepted') {
    sessionStorage.setItem('installBannerDismissed', 'true');
  }
});

installDismiss?.addEventListener('click', () => {
  if (installBanner) installBanner.setAttribute('hidden', '');
  sessionStorage.setItem('installBannerDismissed', 'true');
});

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => { });
  });
}

// URL INTERCEPTION MODULE
(async function initApp() {
  const urlParams = new URLSearchParams(window.location.search);
  const tkConn = urlParams.get('tiktok_connected') === 'true';
  const ytConn = urlParams.get('youtube_connected') === 'true';

  if (tkConn || ytConn) {
    state.loggedIn = true;
    state.user = { name: 'Pastor Mrs. Lubega', email: DEMO_EMAIL };

    if (tkConn) state.tiktokConnected = true;
    if (ytConn) state.youtubeConnected = true;

    const userDisplay = document.getElementById('topbar-user');
    if (userDisplay) userDisplay.textContent = state.user.name;

    await updateDashboard();
    switchScreen('screen-dashboard'); // FIX: Instantly drop to dashboard loop instead of getting stuck on login screen

    await checkPlatformConnections();
    window.history.replaceState({}, document.title, window.location.pathname);

    if (tkConn) alert("TikTok Account Successfully Linked!");
    if (ytConn) alert("YouTube Channel Successfully Linked!");
  } else {
    switchScreen('screen-login');
  }
})();
}