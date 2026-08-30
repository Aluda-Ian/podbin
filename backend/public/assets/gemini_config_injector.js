/**
 * gemini_config_injector.js
 *
 * Injects Google Gemini API and Google OAuth configuration cards into the
 * Admin API Configuration and Settings pages.
 * Ensures cards persist across React component re-renders, route transitions, and theme switches.
 */
(function() {
  'use strict';

  function getAuthToken() {
    try {
      const stored = localStorage.getItem('podule_auth_token') || localStorage.getItem('token') || localStorage.getItem('auth_token');
      if (stored) return stored.replace(/^"|"$/g, '');
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && k.toLowerCase().includes('token')) {
          const val = localStorage.getItem(k);
          if (val && val.length > 20) return val.replace(/^"|"$/g, '');
        }
      }
    } catch (e) {}
    return '';
  }

  let cachedGeminiKey = localStorage.getItem('podule_gemini_key') || '';
  let cachedClientId = localStorage.getItem('podule_google_client_id') || '';
  let cachedClientSecret = localStorage.getItem('podule_google_client_secret') || '';

  function isConfigPage() {
    const p = (window.location.pathname || '') + (window.location.hash || '');
    return p.includes('api-config') || p.includes('api-keys') || p.includes('settings') || p.includes('/admin');
  }

  function injectCards() {
    if (!isConfigPage()) return;

    // Find the cards grid container
    const grid = document.querySelector('form .grid') ||
                 document.querySelector('.grid.grid-cols-1') ||
                 document.querySelector('[class*="grid-cols-"]') ||
                 document.querySelector('.grid');
    if (!grid) return;

    // Deduplicate existing cards
    const geminiCards = document.querySelectorAll('#gemini-api-card');
    if (geminiCards.length > 1) {
      for (let i = 1; i < geminiCards.length; i++) geminiCards[i].remove();
    }
    const oauthCards = document.querySelectorAll('#google-oauth-card');
    if (oauthCards.length > 1) {
      for (let i = 1; i < oauthCards.length; i++) oauthCards[i].remove();
    }

    const token = getAuthToken();

    // -------------------------------------------------------------
    // 1. Google Gemini API Card
    // -------------------------------------------------------------
    if (!grid.contains(document.getElementById('gemini-api-card'))) {
      const card = document.createElement('div');
      card.id = 'gemini-api-card';
      card.className = 'bg-panel border border-border rounded-xl p-5 space-y-4 flex flex-col justify-between shadow-sm hover:border-foreground/5 transition-all';
      card.innerHTML = `
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="size-8 rounded-lg bg-purple-500/10 border border-purple-500/25 grid place-items-center text-purple-400 font-bold text-xs">
                AI
              </div>
              <div>
                <h2 class="text-xs font-bold text-foreground uppercase tracking-wider">GOOGLE GEMINI API (PRIMARY)</h2>
                <p class="text-[10px] text-muted">Primary Transcription & Multimodal AI</p>
              </div>
            </div>
            <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer" class="text-[10px] text-muted hover:text-foreground font-mono flex items-center gap-1 hover:underline text-xs">
              Get API Key ↗
            </a>
          </div>
          <p class="text-xs text-muted leading-relaxed">
            Handles primary audio/video transcription, title generation, show notes, and social clips with Gemini 1.5 Flash.
          </p>
          <div class="space-y-1.5 pt-2">
            <label class="text-[10px] font-mono text-muted uppercase tracking-wider">API SECRET KEY</label>
            <div class="relative">
              <input id="gemini-key-input" type="password" value="${cachedGeminiKey}" placeholder="AIza..." class="w-full bg-background border border-border rounded-md pl-3 pr-10 py-2 text-xs font-mono outline-none focus:border-accent transition-colors text-foreground" />
              <button id="toggle-gemini-key" type="button" class="absolute right-3 top-2.5 text-muted hover:text-foreground cursor-pointer text-xs">
                👁️
              </button>
            </div>
          </div>
        </div>
        <div class="space-y-3 pt-4 border-t border-border/50">
          <div class="flex items-center justify-between">
            <button id="test-gemini-btn" type="button" class="px-2.5 py-1 text-[10px] font-semibold border border-border rounded hover:bg-foreground/5 text-muted hover:text-foreground transition-colors inline-flex items-center gap-1.5 cursor-pointer">
              Test Connection
            </button>
            <span id="gemini-status-badge" class="text-[10px] font-mono flex items-center gap-1 hidden">
              <span id="gemini-status-text">Active</span>
            </span>
          </div>
          <div id="gemini-msg-box" class="p-2 rounded font-mono text-[9px] hidden"></div>
        </div>
      `;

      grid.appendChild(card);

      const input = card.querySelector('#gemini-key-input');
      const toggleBtn = card.querySelector('#toggle-gemini-key');
      const testBtn = card.querySelector('#test-gemini-btn');
      const statusBadge = card.querySelector('#gemini-status-badge');
      const statusText = card.querySelector('#gemini-status-text');
      const msgBox = card.querySelector('#gemini-msg-box');

      toggleBtn.addEventListener('click', () => {
        input.type = input.type === 'password' ? 'text' : 'password';
      });

      testBtn.addEventListener('click', async () => {
        const val = input.value.trim();
        if (!val) {
          msgBox.className = 'p-2 rounded font-mono text-[9px] bg-red-500/10 text-red-400 border border-red-500/20';
          msgBox.textContent = 'Please enter a Gemini API Key first.';
          msgBox.classList.remove('hidden');
          return;
        }
        testBtn.disabled = true;
        testBtn.textContent = 'Testing...';
        try {
          const tok = getAuthToken();
          const res = await fetch('/api/v1/settings/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${tok}` },
            body: JSON.stringify({ provider: 'gemini', api_key: val })
          });
          const data = await res.json();
          testBtn.disabled = false;
          testBtn.textContent = 'Test Connection';

          if (res.ok && (data.status === 'success' || data.success)) {
            statusBadge.className = 'text-[10px] font-mono flex items-center gap-1 text-emerald-400';
            statusText.textContent = '✓ Active';
            statusBadge.classList.remove('hidden');

            msgBox.className = 'p-2 rounded font-mono text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
            msgBox.textContent = data.message || 'Successfully authenticated connection with Google Gemini AI.';
            msgBox.classList.remove('hidden');

            localStorage.setItem('podule_gemini_key', val);
            cachedGeminiKey = val;

            await fetch('/api/v1/admin/api-keys', {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${tok}` },
              body: JSON.stringify({ gemini: val })
            });
          } else {
            statusBadge.className = 'text-[10px] font-mono flex items-center gap-1 text-red-400';
            statusText.textContent = '✗ Fail';
            statusBadge.classList.remove('hidden');

            msgBox.className = 'p-2 rounded font-mono text-[9px] bg-red-500/10 text-red-400 border border-red-500/20';
            msgBox.textContent = data.detail || data.message || 'Connection verification failed.';
            msgBox.classList.remove('hidden');
          }
        } catch (e) {
          testBtn.disabled = false;
          testBtn.textContent = 'Test Connection';
          msgBox.className = 'p-2 rounded font-mono text-[9px] bg-red-500/10 text-red-400 border border-red-500/20';
          msgBox.textContent = 'Network error during connection test.';
          msgBox.classList.remove('hidden');
        }
      });

      // Fetch live key from server
      if (token) {
        fetch('/api/v1/admin/api-keys', { headers: { 'Authorization': `Bearer ${token}` } })
          .then(r => r.ok ? r.json() : null)
          .then(data => {
            if (data && data.gemini && input && !input.value) {
              input.value = data.gemini;
              cachedGeminiKey = data.gemini;
              localStorage.setItem('podule_gemini_key', data.gemini);
            }
          })
          .catch(() => {});
      }
    }

    // -------------------------------------------------------------
    // 2. Google OAuth Setup Card
    // -------------------------------------------------------------
    if (!grid.contains(document.getElementById('google-oauth-card'))) {
      const oauthCard = document.createElement('div');
      oauthCard.id = 'google-oauth-card';
      oauthCard.className = 'bg-panel border border-border rounded-xl p-5 space-y-4 flex flex-col justify-between shadow-sm hover:border-foreground/5 transition-all';
      oauthCard.innerHTML = `
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="size-8 rounded-lg bg-blue-500/10 border border-blue-500/25 grid place-items-center text-blue-400 font-bold text-xs">
                G
              </div>
              <div>
                <h2 class="text-xs font-bold text-foreground uppercase tracking-wider">GOOGLE OAUTH SETUP</h2>
                <p class="text-[10px] text-muted">Sign In & Sign Up with Google</p>
              </div>
            </div>
            <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noreferrer" class="text-[10px] text-muted hover:text-foreground font-mono flex items-center gap-1 hover:underline text-xs">
              Google Console ↗
            </a>
          </div>
          <p class="text-xs text-muted leading-relaxed">
            Configure Google OAuth credentials to enable 1-click Sign In and Sign Up with Google across auth pages.
          </p>
          <div class="space-y-2 pt-1">
            <div>
              <label class="text-[10px] font-mono text-muted uppercase tracking-wider">CLIENT ID</label>
              <input id="google-client-id-input" type="text" value="${cachedClientId}" placeholder="...apps.googleusercontent.com" class="w-full bg-background border border-border rounded-md px-3 py-1.5 text-xs font-mono outline-none focus:border-accent transition-colors text-foreground mt-1" />
            </div>
            <div>
              <label class="text-[10px] font-mono text-muted uppercase tracking-wider">CLIENT SECRET</label>
              <input id="google-client-secret-input" type="password" value="${cachedClientSecret}" placeholder="GOCSPX-..." class="w-full bg-background border border-border rounded-md px-3 py-1.5 text-xs font-mono outline-none focus:border-accent transition-colors text-foreground mt-1" />
            </div>
          </div>
        </div>
        <div class="space-y-3 pt-4 border-t border-border/50">
          <div class="flex items-center justify-between">
            <button id="save-google-oauth-btn" type="button" class="px-3 py-1.5 text-xs font-semibold bg-foreground text-background rounded hover:bg-foreground/90 transition-colors inline-flex items-center gap-1.5 cursor-pointer">
              Save Google OAuth Setup
            </button>
            <span id="google-oauth-status" class="text-[10px] font-mono text-emerald-400 hidden">✓ Saved</span>
          </div>
          <div id="google-oauth-msg" class="p-2 rounded font-mono text-[9px] hidden"></div>
        </div>
      `;

      grid.appendChild(oauthCard);

      const cidInput = oauthCard.querySelector('#google-client-id-input');
      const secretInput = oauthCard.querySelector('#google-client-secret-input');
      const saveBtn = oauthCard.querySelector('#save-google-oauth-btn');
      const statusSpan = oauthCard.querySelector('#google-oauth-status');
      const msgBox = oauthCard.querySelector('#google-oauth-msg');

      saveBtn.addEventListener('click', async () => {
        const cid = cidInput.value.trim();
        const sec = secretInput.value.trim();

        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving...';
        try {
          const tok = getAuthToken();
          let settingsPayload = { integration_credentials: {} };
          try {
            const getResp = await fetch('/api/v1/settings', { headers: { 'Authorization': `Bearer ${tok}` } });
            if (getResp.ok) settingsPayload = await getResp.json();
          } catch (e) {}

          settingsPayload.integration_credentials = settingsPayload.integration_credentials || {};
          settingsPayload.integration_credentials.google = {
            client_id: cid,
            client_secret: sec
          };

          const saveResp = await fetch('/api/v1/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${tok}` },
            body: JSON.stringify(settingsPayload)
          });

          saveBtn.disabled = false;
          saveBtn.textContent = 'Save Google OAuth Setup';

          if (saveResp.ok) {
            statusSpan.classList.remove('hidden');
            msgBox.className = 'p-2 rounded font-mono text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
            msgBox.textContent = 'Google OAuth configuration saved successfully! Sign in with Google is now active.';
            msgBox.classList.remove('hidden');

            cachedClientId = cid;
            cachedClientSecret = sec;
            localStorage.setItem('podule_google_client_id', cid);
            localStorage.setItem('podule_google_client_secret', sec);
          } else {
            msgBox.className = 'p-2 rounded font-mono text-[9px] bg-red-500/10 text-red-400 border border-red-500/20';
            msgBox.textContent = 'Failed to save Google OAuth configuration.';
            msgBox.classList.remove('hidden');
          }
        } catch (e) {
          saveBtn.disabled = false;
          saveBtn.textContent = 'Save Google OAuth Setup';
          msgBox.className = 'p-2 rounded font-mono text-[9px] bg-red-500/10 text-red-400 border border-red-500/20';
          msgBox.textContent = 'Network error saving Google OAuth setup.';
          msgBox.classList.remove('hidden');
        }
      });

      // Fetch live settings from server
      if (token) {
        fetch('/api/v1/settings', { headers: { 'Authorization': `Bearer ${token}` } })
          .then(r => r.ok ? r.json() : null)
          .then(data => {
            if (data && data.integration_credentials && data.integration_credentials.google) {
              const g = data.integration_credentials.google;
              if (cidInput && g.client_id && !cidInput.value) {
                cidInput.value = g.client_id;
                cachedClientId = g.client_id;
                localStorage.setItem('podule_google_client_id', g.client_id);
              }
              if (secretInput && g.client_secret && !secretInput.value) {
                secretInput.value = g.client_secret;
                cachedClientSecret = g.client_secret;
                localStorage.setItem('podule_google_client_secret', g.client_secret);
              }
            }
          })
          .catch(() => {});
      }
    }
  }

  function handleAdminAnalyticsRedirect() {
    if (window.location.pathname === '/admin/analytics') {
      window.location.replace('/analytics');
    }
  }

  const observer = new MutationObserver(() => {
    handleAdminAnalyticsRedirect();
    injectCards();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      handleAdminAnalyticsRedirect();
      observer.observe(document.body, { childList: true, subtree: true });
      injectCards();
    });
  } else {
    handleAdminAnalyticsRedirect();
    observer.observe(document.body, { childList: true, subtree: true });
    injectCards();
  }

  setInterval(() => {
    handleAdminAnalyticsRedirect();
    injectCards();
  }, 800);
})();
