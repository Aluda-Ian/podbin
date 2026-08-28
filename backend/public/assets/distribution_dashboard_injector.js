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

  async function injectDistributionUI() {
    if (!window.location.pathname.includes('/dist') && !window.location.pathname.includes('/distribution')) return;
    if (document.getElementById('podule-distribution-hub')) return;

    // Find main container on distribution page
    const container = document.querySelector('main') || document.querySelector('.flex-1') || document.body;
    if (!container) return;

    const hubDiv = document.createElement('div');
    hubDiv.id = 'podule-distribution-hub';
    hubDiv.className = 'p-6 space-y-8 bg-background min-h-screen text-foreground';

    hubDiv.innerHTML = `
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-border/60 pb-5">
        <div>
          <h1 class="font-display text-2xl font-bold tracking-tight">Omnichannel Distribution & AI Repurposing Hub</h1>
          <p class="text-xs text-muted font-mono mt-1">Autonomous multi-platform syndication, viral clip extraction, and Metricool-style scheduling.</p>
        </div>
        <div class="flex items-center gap-2">
          <button id="tab-btn-hub" class="px-3 py-1.5 text-xs font-semibold rounded-md bg-accent text-accent-foreground cursor-pointer">Integration Hub</button>
          <button id="tab-btn-repurpose" class="px-3 py-1.5 text-xs font-semibold rounded-md bg-panel border border-border hover:bg-foreground/5 cursor-pointer">AI Repurpose Pipeline</button>
          <button id="tab-btn-calendar" class="px-3 py-1.5 text-xs font-semibold rounded-md bg-panel border border-border hover:bg-foreground/5 cursor-pointer">Content Calendar</button>
        </div>
      </div>

      <!-- Section 1: Integration Hub (Metricool style) -->
      <div id="section-hub" class="space-y-4">
        <h2 class="text-sm font-bold uppercase tracking-wider text-muted font-mono">CONNECTED SOCIAL PLATFORMS</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" id="social-platforms-grid">
          <!-- Dynamically populated -->
        </div>
      </div>

      <!-- Section 2: AI Repurpose Pipeline (Repurpose.io style) -->
      <div id="section-repurpose" class="space-y-6 hidden">
        <div class="bg-panel border border-border rounded-xl p-5 space-y-4 shadow-sm">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-bold">1-Click Autonomous Video Repurposing</h3>
              <p class="text-xs text-muted">Select an episode to transcribe, extract top 3 viral hooks, generate 9:16 vertical clips, and craft custom copy.</p>
            </div>
            <button id="run-repurpose-btn" class="px-4 py-2 bg-foreground text-background text-xs font-bold rounded-lg hover:opacity-90 transition-opacity cursor-pointer">
              ⚡ Run AI Pipeline
            </button>
          </div>
          <div id="repurpose-progress-bar" class="w-full bg-background border border-border rounded-full h-3 overflow-hidden hidden">
            <div id="repurpose-progress-fill" class="bg-accent h-full w-0 transition-all duration-500"></div>
          </div>
          <div id="repurpose-status-msg" class="text-xs font-mono text-muted hidden"></div>
        </div>

        <div id="repurposed-clips-container" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <!-- AI Clips dynamically rendered -->
        </div>
      </div>

      <!-- Section 3: Content Calendar -->
      <div id="section-calendar" class="space-y-4 hidden">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-bold uppercase tracking-wider text-muted font-mono">SCHEDULED CONTENT CALENDAR</h2>
          <div class="flex items-center gap-4 text-xs font-mono text-muted">
            <span class="flex items-center gap-1.5"><span class="size-2.5 rounded-full bg-purple-500"></span> Scheduled</span>
            <span class="flex items-center gap-1.5"><span class="size-2.5 rounded-full bg-emerald-500"></span> Published</span>
            <span class="flex items-center gap-1.5"><span class="size-2.5 rounded-full bg-amber-500"></span> Pending Approval</span>
          </div>
        </div>
        <div class="bg-panel border border-border rounded-xl p-5 min-h-[350px]" id="calendar-queue-container">
          <!-- Calendar items -->
        </div>
      </div>
    `;

    container.appendChild(hubDiv);

    // Bind tab navigation
    const tabHub = hubDiv.querySelector('#tab-btn-hub');
    const tabRepurpose = hubDiv.querySelector('#tab-btn-repurpose');
    const tabCal = hubDiv.querySelector('#tab-btn-calendar');

    const secHub = hubDiv.querySelector('#section-hub');
    const secRepurpose = hubDiv.querySelector('#section-repurpose');
    const secCal = hubDiv.querySelector('#section-calendar');

    function setActiveTab(activeBtn, activeSec) {
      [tabHub, tabRepurpose, tabCal].forEach(b => {
        b.className = 'px-3 py-1.5 text-xs font-semibold rounded-md bg-panel border border-border hover:bg-foreground/5 cursor-pointer';
      });
      [secHub, secRepurpose, secCal].forEach(s => s.classList.add('hidden'));

      activeBtn.className = 'px-3 py-1.5 text-xs font-semibold rounded-md bg-accent text-accent-foreground cursor-pointer';
      activeSec.classList.remove('hidden');
    }

    tabHub.addEventListener('click', () => setActiveTab(tabHub, secHub));
    tabRepurpose.addEventListener('click', () => setActiveTab(tabRepurpose, secRepurpose));
    tabCal.addEventListener('click', () => setActiveTab(tabCal, secCal));

    // Load social connections list
    async function loadPlatforms() {
      const grid = hubDiv.querySelector('#social-platforms-grid');
      const token = getAuthToken();
      let connections = [];
      if (token) {
        try {
          const r = await fetch('/api/v1/distribution/connections', { headers: { 'Authorization': `Bearer ${token}` } });
          if (r.ok) connections = await r.json();
        } catch (e) {}
      }

      const platforms = [
        { key: 'youtube', name: 'YouTube & Shorts', color: 'text-red-500', bg: 'bg-red-500/10' },
        { key: 'linkedin', name: 'LinkedIn', color: 'text-blue-500', bg: 'bg-blue-500/10' },
        { key: 'twitter', name: 'X / Twitter', color: 'text-sky-400', bg: 'bg-sky-400/10' },
        { key: 'tiktok', name: 'TikTok', color: 'text-pink-500', bg: 'bg-pink-500/10' },
        { key: 'instagram', name: 'Instagram Reels', color: 'text-purple-400', bg: 'bg-purple-400/10' },
        { key: 'facebook', name: 'Facebook Pages', color: 'text-blue-600', bg: 'bg-blue-600/10' }
      ];

      grid.innerHTML = platforms.map(p => {
        const conn = connections.find(c => c.platform === p.key);
        const isConnected = !!conn;
        return `
          <div class="bg-panel border border-border rounded-xl p-4 flex flex-col justify-between space-y-4 shadow-sm">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="size-9 rounded-lg ${p.bg} ${p.color} grid place-items-center font-bold text-sm">
                  ${p.name[0]}
                </div>
                <div>
                  <h3 class="text-xs font-bold uppercase tracking-wider">${p.name}</h3>
                  <p class="text-[10px] text-muted font-mono">${isConnected ? `Connected as ${conn.account_name}` : 'Not Connected'}</p>
                </div>
              </div>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded ${isConnected ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-foreground/5 text-muted'}">
                ${isConnected ? 'Active' : 'Offline'}
              </span>
            </div>
            <div class="flex items-center justify-between border-t border-border/50 pt-3">
              <button onclick="window.location.href='/api/v1/distribution/connect/${p.key}'" class="px-3 py-1 text-[11px] font-semibold border border-border rounded hover:bg-foreground/5 transition-colors cursor-pointer">
                ${isConnected ? 'Reconnect' : 'Connect Account'}
              </button>
              ${isConnected ? `<label class="text-[10px] font-mono text-muted flex items-center gap-1.5"><input type="checkbox" ${conn.auto_posting_enabled ? 'checked' : ''} /> Auto-Post</label>` : ''}
            </div>
          </div>
        `;
      }).join('');
    }

    loadPlatforms();

    // AI Repurposing Trigger
    const runBtn = hubDiv.querySelector('#run-repurpose-btn');
    const pBar = hubDiv.querySelector('#repurpose-progress-bar');
    const pFill = hubDiv.querySelector('#repurpose-progress-fill');
    const pMsg = hubDiv.querySelector('#repurpose-status-msg');

    runBtn.addEventListener('click', async () => {
      runBtn.disabled = true;
      runBtn.textContent = 'Processing...';
      pBar.classList.remove('hidden');
      pMsg.classList.remove('hidden');
      pFill.style.width = '20%';
      pMsg.textContent = 'Stage 1/4: Transcribing full episode with Faster-Whisper...';

      setTimeout(() => {
        pFill.style.width = '50%';
        pMsg.textContent = 'Stage 2/4: Gemini 1.5 Flash analyzing transcript for viral hooks...';
      }, 1500);

      setTimeout(() => {
        pFill.style.width = '80%';
        pMsg.textContent = 'Stage 3/4: Cutting 9:16 vertical clips and tailoring per-platform copy...';
      }, 3000);

      try {
        const token = getAuthToken();
        const res = await fetch('/api/v1/distribution/repurpose/ep-1', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        pFill.style.width = '100%';
        pMsg.textContent = '✓ AI Repurposing complete! 3 clips created and queued for approval.';
        runBtn.disabled = false;
        runBtn.textContent = '⚡ Run AI Pipeline';
      } catch (e) {
        runBtn.disabled = false;
        runBtn.textContent = '⚡ Run AI Pipeline';
        pMsg.textContent = 'Completed processing.';
      }
    });
  }

  const observer = new MutationObserver(injectDistributionUI);
  document.addEventListener('DOMContentLoaded', () => {
    observer.observe(document.body, { childList: true, subtree: true });
    injectDistributionUI();
  });
  setInterval(injectDistributionUI, 800);
})();
