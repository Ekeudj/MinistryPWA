/**
 * HerGlory Media CMS — app_3.js
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
  metaConnected: false,
};

// DOM REFS
const ttStatus = document.getElementById('tt-status');
const ttConnectBtn = document.getElementById('tt-connect-btn');
const ytStatus = document.getElementById('yt-status');
const ytConnectBtn = document.getElementById('yt-connect-btn');
const metaStatus = document.getElementById('meta-status');
const metaConnectBtn = document.getElementById('meta-connect-btn');

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
    loginBtn.style.transform = 'translateX(-8px)';
    setTimeout(() => { loginBtn.style.transform = 'translateX(8px)'; }, 80);
    setTimeout(() => { loginBtn.style.transform = ''; }, 160);
    inpPass.value = '';
    inpPass.focus();
  }
}

topbarLogout.addEventListener('click', () => {
  state.loggedIn = false;
  state.user = null;
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

    let thumbHTML = '';
    if (post.mediaType === 'audio') {
      thumbHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>';
    } else if (post.mediaURL) {
      thumbHTML = post.mediaType === 'photo' ? `<img src="${post.mediaURL}" />` : `<video src="${post.mediaURL}"></video>`;
    }

    const pillsHTML = post.platforms.map(p => `<span class="platform-pill pill-${p}">${platformLabel(p)}</span>`).join('');

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
  await checkPlatformConnections();
});

navPostBtn.addEventListener('click', async () => {
  resetNewPostForm();
  switchScreen('screen-newpost');
  await checkPlatformConnections();
});

async function checkPlatformConnections() {
  // TikTok Connection Card
  try {
    const response = await fetch('/api/auth/status/tiktok');
    if (response.ok) {
      const data = await response.json();
      state.tiktokConnected = data.connected;
    }
  } catch (err) { console.error(err); }

  const tiktokCard = document.querySelector('.platform-card[data-platform="tiktok"]');
  if (tiktokCard) {
    const toggle = tiktokCard.querySelector('.platform-toggle');
    if (!state.tiktokConnected) {
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

  // YouTube Connection Card
  try {
    const response = await fetch('/api/auth/status/youtube');
    if (response.ok) {
      const data = await response.json();
      state.youtubeConnected = data.connected;
    }
  } catch (err) { console.error(err); }

  const youtubeCard = document.querySelector('.platform-card[data-platform="youtube"]');
  if (youtubeCard) {
    const toggle = youtubeCard.querySelector('.platform-toggle');
    if (!state.youtubeConnected) {
      youtubeCard.classList.add('disabled');
      if (toggle) { toggle.checked = false; toggle.disabled = true; }
      if (ytStatus) ytStatus.textContent = "Account Not Linked";
      if (ytConnectBtn) ytConnectBtn.style.display = "block";
    } else {
      youtubeCard.classList.remove('disabled');
      if (toggle) toggle.disabled = false;
      if (ytStatus) ytStatus.textContent = "Connected";
      if (ytConnectBtn) ytConnectBtn.style.display = "none";
    }
  }

  // Meta (Facebook + Instagram) Connection Card — one shared token/connection
  // gates both the Facebook and Instagram destination toggles.
  try {
    const response = await fetch('/api/auth/status/meta');
    if (response.ok) {
      const data = await response.json();
      state.metaConnected = data.connected;
    }
  } catch (err) { console.error(err); }

  const metaCard = document.querySelector('.platform-card[data-platform="meta"]');
  if (metaCard) {
    const subToggles = metaCard.querySelectorAll('.platform-toggle');
    if (!state.metaConnected) {
      metaCard.classList.add('disabled');
      subToggles.forEach(t => { t.checked = false; t.disabled = true; });
      if (metaStatus) metaStatus.textContent = "Account Not Linked";
      if (metaConnectBtn) metaConnectBtn.style.display = "block";
    } else {
      metaCard.classList.remove('disabled');
      subToggles.forEach(t => { t.disabled = false; });
      if (metaStatus) metaStatus.textContent = "Connected";
      if (metaConnectBtn) metaConnectBtn.style.display = "none";
    }
  }
}

mediaInput.addEventListener('change', () => {
  const file = mediaInput.files[0];
  if (file) loadMediaFile(file);
});

function loadMediaFile(file) {
  if (state.mediaURL) URL.revokeObjectURL(state.mediaURL);

  const isVideo = file.type.startsWith('video/');
  const isImage = file.type.startsWith('image/');
  const isAudio = file.type.startsWith('audio/') || /\.(mp3|wav|m4a|aac)$/i.test(file.name);

  state.mediaFile = file;
  state.mediaType = isVideo ? 'video' : isImage ? 'photo' : 'audio';
  state.mediaURL = URL.createObjectURL(file);

  if (dropLabelWrap) dropLabelWrap.style.visibility = 'hidden';
  if (mediaPreview) mediaPreview.removeAttribute('hidden');

  if (previewImg) previewImg.setAttribute('hidden', '');
  if (previewVid) previewVid.setAttribute('hidden', '');
  if (audioPreview) audioPreview.setAttribute('hidden', '');

  if (isImage && previewImg) {
    previewImg.src = state.mediaURL; previewImg.removeAttribute('hidden');
  } else if (isVideo && previewVid) {
    previewVid.src = state.mediaURL; previewVid.removeAttribute('hidden');
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

previewRemove.addEventListener('click', () => { clearMediaPreview(); });

function clearMediaPreview() {
  if (state.mediaURL) URL.revokeObjectURL(state.mediaURL);
  state.mediaFile = null; state.mediaType = null; state.mediaURL = null;
  if (mediaInput) mediaInput.value = '';
  if (mediaPreview) mediaPreview.setAttribute('hidden', '');
  if (dropLabelWrap) dropLabelWrap.style.visibility = 'visible';
  applyMediaTypeRules();
}

function applyMediaTypeRules() {
  document.querySelectorAll('.platform-card').forEach(card => {
    const key = card.dataset.platform;
    const toggle = card.querySelector('.platform-toggle');
    if (key === 'tiktok' && !state.tiktokConnected) card.classList.add('disabled');
    else if (key === 'youtube' && !state.youtubeConnected) card.classList.add('disabled');
    else if (key === 'meta' && !state.metaConnected) card.classList.add('disabled');
    else card.classList.remove('disabled');
  });
}

function getSelectedPlatforms() {
  // BUG FIX 9: checkboxes use data-key="tiktok"/"youtube" in the HTML, not data-platform,
  // and an unset checkbox .value defaults to "on" — so this was always returning
  // ["on","on"] instead of ["tiktok","youtube"], causing everything to fall into
  // the "else = youtube" branch downstream.
  return Array.from(platformToggles).filter(t => t.checked).map(t => t.dataset.key);
}

postNowBtn.addEventListener('click', handlePostNow);

async function handlePostNow() {
  const title = postTitle.value.trim();
  const platforms = getSelectedPlatforms();

  if (!state.mediaFile) { return alert('Select file first.'); }
  if (!title || platforms.length === 0) { return; }

  let workingTitle = title;
  switchScreen('screen-posting');

  if (postingLoader) postingLoader.removeAttribute('hidden');
  // BUG FIX 13: bring back the audio-specific status message that used to show
  // while the audio was being converted into a video before upload.
  if (postingTitleDisplay) {
    postingTitleDisplay.textContent = state.mediaType === 'audio'
      ? 'Converting audio to video...'
      : 'Uploading operational media assets...';
  }

  const formData = new FormData();
  formData.append('file', state.mediaFile);

  // Dynamic distribution route handling
  const endpoint = state.mediaType === 'audio' ? '/api/upload-audio' : '/api/upload-video';

  try {
    const response = await fetch(`${window.location.origin}${endpoint}`, {
      method: 'POST',
      body: formData
    });
    const data = await response.json();
    if (response.status !== 200) {
      alert(`Asset storage verification failed: ${data.message}`);
      switchScreen('screen-newpost');
      return;
    }
    workingTitle = data.video_file;
  } catch (err) {
    alert('Network processing failed. Check backend connection.');
    switchScreen('screen-newpost');
    return;
  }

  startPosting(workingTitle, platforms);
}

async function startPosting(title, platforms) {
  if (postingPlatforms) postingPlatforms.innerHTML = '';

  const rowMap = {};
  platforms.forEach(p => {
    const row = document.createElement('div');
    row.className = 'posting-row';
    row.innerHTML = `<span>${platformLabel(p)}</span><span class="posting-status">Uploading...</span>`;
    postingPlatforms.appendChild(row);
    rowMap[p] = row;
  });

  const PUBLISH_ENDPOINTS = {
    tiktok: '/api/test-publish/tiktok',
    youtube: '/api/test-publish/youtube',
    facebook: '/api/test-publish/facebook',
    instagram: '/api/test-publish/instagram',
  };

  for (const p of platforms) {
    const endpoint = PUBLISH_ENDPOINTS[p];
    try {
      const response = await fetch(`${window.location.origin}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // BUG FIX 10: send the user's actual title/caption so the backend doesn't
        // fall back to its hardcoded default text.
        body: JSON.stringify({
          "video_file": title,
          "title": postTitle.value.trim(),
          "description": postCaption.value.trim(),
           "media_type": state.mediaType
        })
      });
      const result = await response.json();
      if (response.ok) {
        rowMap[p].querySelector('.posting-status').textContent = '✓ Success';
      } else {
        rowMap[p].querySelector('.posting-status').textContent = '✕ Failed';
      }
    } catch (e) {
      rowMap[p].querySelector('.posting-status').textContent = '✕ Network Error';
    }
  }

  if (postingLoader) postingLoader.setAttribute('hidden', '');
  if (postingDone) postingDone.removeAttribute('hidden');

  state.posts.push({
    title,
    mediaType: state.mediaType,
    platforms,
    date: new Date().toLocaleDateString(),
    mediaURL: state.mediaURL
  });
}

goDashboardBtn.addEventListener('click', () => {
  updateDashboard();
  switchScreen('screen-dashboard');
  resetNewPostForm();
});

function resetNewPostForm() {
  clearMediaPreview();
  if (postTitle) postTitle.value = '';
  applyMediaTypeRules();
}

function platformLabel(key) {
  const labels = { tiktok: 'TikTok', youtube: 'YouTube', facebook: 'Facebook', instagram: 'Instagram' };
  return labels[key] || key;
}

function escHtml(str) {
  return String(str).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}

(async function initApp() {
  await checkPlatformConnections();
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('tiktok_connected') === 'true' || urlParams.get('youtube_connected') === 'true' || urlParams.get('meta_connected') === 'true') {
    state.loggedIn = true;
    await updateDashboard();
    switchScreen('screen-dashboard');
    window.history.replaceState({}, document.title, window.location.pathname);
  } else {
    switchScreen('screen-login');
  }
})();