(function() {
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

  async function injectGoogleCards() {
    if (!window.location.pathname.includes('/admin/api-config') && !window.location.pathname.includes('/settings')) return;

    // Find the card grid container safely
    const grid = document.querySelector('form .grid') || document.querySelector('.grid') || document.querySelector('[class*="grid-cols"]');
    if (!grid) return;

    const token = getAuthToken();

    // -------------------------------------------------------------
    // 1. Inject Gemini API Card
    // -------------------------------------------------------------
    if (!document.getElementById('gemini-api-card')) {
      let currentGeminiKey = '';
      if (token) {
        try {
          const resp = await fetch('/api/v1/admin/api-keys', {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (resp.ok) {
            const data = await resp.json();
            currentGeminiKey = data.gemini || '';
          }
        } catch (e) {}
      }

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
                <h2 class="text-xs font-bold text-foreground uppercase tracking-wider">GOOGLE GEMINI API</h2>
                <p class="text-[10px] text-muted">Multimodal & transcription AI</p>
              </div>
            </div>
            <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer" class="text-[10px] text-muted hover:text-foreground font-mono flex items-center gap-1 hover:underline text-xs">
              Get API Key ↗
            </a>
          </div>
          <p class="text-xs text-muted leading-relaxed">
            Powers multimodal audio/video transcription, episode title creation, show notes, and social snippets with Gemini 1.5 Flash.
          </p>
          <div class="space-y-1.5 pt-2">
            <label class="text-[10px] font-mono text-muted uppercase tracking-wider">API SECRET KEY</label>
            <div class="relative">
              <input id="gemini-key-input" type="password" value="${currentGeminiKey}" placeholder="AIza..." class="w-full bg-background border border-border rounded-md pl-3 pr-10 py-2 text-xs font-mono outline-none focus:border-accent transition-colors text-foreground" />
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

          if (res.ok && data.status === 'success') {
            statusBadge.className = 'text-[10px] font-mono flex items-center gap-1 text-emerald-400';
            statusText.textContent = '✓ Active';
            statusBadge.classList.remove('hidden');

            msgBox.className = 'p-2 rounded font-mono text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
            msgBox.textContent = data.message || 'Successfully authenticated connection with Google Gemini AI.';
            msgBox.classList.remove('hidden');

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
    }

    // -------------------------------------------------------------
    // 2. Inject Google OAuth Sign Up / Login Setup Card
    // -------------------------------------------------------------
    if (!document.getElementById('google-oauth-card')) {
      let currentClientId = '';
      let currentClientSecret = '';
      if (token) {
        try {
          const resp = await fetch('/api/v1/settings', {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (resp.ok) {
            const data = await resp.json();
            const g = data.integration_credentials?.google || {};
            currentClientId = g.client_id || '';
            currentClientSecret = g.client_secret || '';
          }
        } catch (e) {}
      }

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
              <input id="google-client-id-input" type="text" value="${currentClientId}" placeholder="...apps.googleusercontent.com" class="w-full bg-background border border-border rounded-md px-3 py-1.5 text-xs font-mono outline-none focus:border-accent transition-colors text-foreground mt-1" />
            </div>
            <div>
              <label class="text-[10px] font-mono text-muted uppercase tracking-wider">CLIENT SECRET</label>
              <input id="google-client-secret-input" type="password" value="${currentClientSecret}" placeholder="GOCSPX-..." class="w-full bg-background border border-border rounded-md px-3 py-1.5 text-xs font-mono outline-none focus:border-accent transition-colors text-foreground mt-1" />
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
          // Fetch current settings first
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
    }
  }

  function handleAdminAnalyticsRedirect() {
    if (window.location.pathname === '/admin/analytics') {
      window.location.replace('/analytics');
    }
  }

  // Observe DOM changes safely for client-side routing
  const observer = new MutationObserver(() => {
    handleAdminAnalyticsRedirect();
    injectGoogleCards();
  });

  document.addEventListener('DOMContentLoaded', () => {
    handleAdminAnalyticsRedirect();
    observer.observe(document.body, { childList: true, subtree: true });
    injectGoogleCards();
  });

  setInterval(() => {
    handleAdminAnalyticsRedirect();
    injectGoogleCards();
  }, 800);
})();
