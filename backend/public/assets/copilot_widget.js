(function() {
  console.log("PodBin Safe Non-Intrusive Right-Sidebar Copilot Initializing...");

  // Floating Copilot Toggle Button (Monochrome Black & White)
  const button = document.createElement("button");
  button.id = "podbin-copilot-btn";
  button.innerHTML = "✦ <b>AI Copilot</b>";
  button.style.cssText = `
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 99998;
    background: #000000;
    color: #ffffff;
    padding: 12px 20px;
    border-radius: 9999px;
    border: 1px solid #27272a;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    font-family: system-ui, -apple-system, sans-serif;
    font-size: 13.5px;
    font-weight: 600;
    cursor: pointer;
    display: none;
    align-items: center;
    gap: 8px;
    transition: transform 0.2s, background 0.2s, border-color 0.2s;
  `;
  button.onmouseover = () => {
    button.style.transform = "scale(1.05)";
    button.style.background = "#09090b";
    button.style.borderColor = "#3f3f46";
  };
  button.onmouseout = () => {
    button.style.transform = "scale(1)";
    button.style.background = "#000000";
    button.style.borderColor = "#27272a";
  };

  // Docked Right Sidebar Copilot Container (Monochrome Dark)
  const drawer = document.createElement("div");
  drawer.id = "podbin-copilot-drawer";
  drawer.style.cssText = `
    position: fixed;
    top: 0;
    right: 0;
    width: 400px;
    max-width: 100vw;
    height: 100vh;
    z-index: 99999;
    background: #000000;
    color: #ffffff;
    border-left: 1px solid #27272a;
    box-shadow: -10px 0 35px rgba(0, 0, 0, 0.7);
    display: none;
    flex-direction: column;
    overflow: hidden;
    font-family: system-ui, -apple-system, sans-serif;
  `;

  // Sidebar Header
  const header = document.createElement("div");
  header.style.cssText = `
    padding: 16px;
    background: #09090b;
    border-bottom: 1px solid #27272a;
    display: flex;
    align-items: center;
    justify-content: space-between;
    shrink: 0;
  `;
  header.innerHTML = `
    <div style="display:flex; align-items:center; gap:10px;">
      <div style="width:28px; height:28px; border-radius:8px; background:#18181b; border:1px solid #27272a; display:grid; place-items:center; font-size:13px; color:#ffffff;">✦</div>
      <span style="font-size:14px; font-weight:600; color:#ffffff; tracking-tight:true;">New AI Chat</span>
    </div>
    <div style="display:flex; align-items:center; gap:8px;">
      <select id="copilot-provider-select" style="background:#18181b; color:#ffffff; border:1px solid #27272a; border-radius:6px; padding:4px 8px; font-size:11px; cursor:pointer;">
        <option value="openai">OpenAI (gpt-4o)</option>
        <option value="anthropic">Anthropic (claude-3-5-sonnet)</option>
        <option value="ollama">Ollama (Local llama3)</option>
        <option value="deepseek">DeepSeek (deepseek-chat)</option>
        <option value="gemini">Google Gemini (gemini-2.5-flash)</option>
      </select>
      <button id="copilot-close-btn" title="Close sidebar" style="background:none; border:none; color:#a1a1aa; font-size:18px; cursor:pointer; padding:2px 6px; border-radius:4px;">✕</button>
    </div>
  `;

  // Main Chat & Messages Scroll Container
  const messagesArea = document.createElement("div");
  messagesArea.id = "copilot-messages";
  messagesArea.style.cssText = `
    flex: 1;
    padding: 20px 16px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
    font-size: 13px;
    background: #000000;
  `;

  // Notion-AI style Initial Welcome Screen
  const welcomeCard = document.createElement("div");
  welcomeCard.id = "copilot-welcome-card";
  welcomeCard.style.cssText = `
    margin-top: 24px;
    margin-bottom: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 12px;
  `;
  welcomeCard.innerHTML = `
    <div style="width:56px; height:56px; border-radius:50%; background:#18181b; border:1px solid #27272a; display:grid; place-items:center; font-size:24px; color:#ffffff;">🤖</div>
    <h3 style="font-size:16px; font-weight:600; color:#ffffff; margin:0;">How can I help you today?</h3>
    <p style="font-size:12px; color:#a1a1aa; margin:0; max-width:280px; line-height:1.4;">Automate podcast tasks, video clipping, and social distribution using natural language prompts.</p>
  `;
  messagesArea.appendChild(welcomeCard);

  // Quick Action Chips Container
  const chipsWrapper = document.createElement("div");
  chipsWrapper.id = "copilot-chips-wrapper";
  chipsWrapper.style.cssText = `
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
    margin-bottom: 12px;
  `;

  const chips = [
    { icon: "✂️", label: "Cut video snippet (01:20 to 02:45)", prompt: "Cut video from 01:20 to 02:45 on episode EP-1" },
    { icon: "📅", label: "Schedule clip for TikTok & YouTube", prompt: "Schedule clip for TikTok and YouTube tomorrow at 5pm" },
    { icon: "💬", label: "Add animated captions to clips", prompt: "Add animated burn-in captions to episode EP-1 clips" },
    { icon: "📊", label: "Analyze episode insights & talking points", prompt: "Analyze episode insights and extract 3 key talking points" }
  ];

  chips.forEach(c => {
    const chipBtn = document.createElement("button");
    chipBtn.style.cssText = `
      background: #18181b;
      color: #ffffff;
      border: 1px solid #27272a;
      padding: 10px 14px;
      border-radius: 10px;
      font-size: 12px;
      text-align: left;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 10px;
      transition: background 0.2s, border-color 0.2s;
    `;
    chipBtn.onmouseover = () => {
      chipBtn.style.background = "#27272a";
      chipBtn.style.borderColor = "#3f3f46";
    };
    chipBtn.onmouseout = () => {
      chipBtn.style.background = "#18181b";
      chipBtn.style.borderColor = "#27272a";
    };
    chipBtn.innerHTML = `<span>${c.icon}</span> <span style="flex:1;">${c.label}</span>`;
    chipBtn.onclick = () => {
      input.value = c.prompt;
      footer.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    };
    chipsWrapper.appendChild(chipBtn);
  });
  messagesArea.appendChild(chipsWrapper);

  // Footer Input Form (Monochrome Input Bar)
  const footer = document.createElement("form");
  footer.id = "copilot-form";
  footer.style.cssText = `
    padding: 14px 16px;
    background: #09090b;
    border-top: 1px solid #27272a;
    display: flex;
    flex-direction: column;
    gap: 8px;
    shrink: 0;
  `;

  const inputContainer = document.createElement("div");
  inputContainer.style.cssText = `
    display: flex;
    align-items: center;
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 12px;
    padding: 6px 12px;
    gap: 8px;
  `;

  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Do anything with AI...";
  input.style.cssText = `
    flex: 1;
    background: transparent;
    border: none;
    color: #ffffff;
    font-size: 13px;
    outline: none;
    padding: 6px 0;
  `;

  const sendBtn = document.createElement("button");
  sendBtn.type = "submit";
  sendBtn.innerHTML = "↑";
  sendBtn.style.cssText = `
    background: #ffffff;
    color: #000000;
    border: none;
    border-radius: 8px;
    width: 28px;
    height: 28px;
    display: grid;
    place-items: center;
    font-weight: 700;
    font-size: 14px;
    cursor: pointer;
    shrink: 0;
    transition: opacity 0.2s;
  `;

  inputContainer.appendChild(input);
  inputContainer.appendChild(sendBtn);

  const subMeta = document.createElement("div");
  subMeta.style.cssText = `
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 10px;
    color: #71717a;
    padding: 0 4px;
  `;
  subMeta.innerHTML = `
    <span>✦ PodBin Copilot Sidebar</span>
    <span style="background:#27272a; color:#ffffff; padding:2px 6px; border-radius:4px; border:1px solid #3f3f46;">Auto Mode</span>
  `;

  footer.appendChild(inputContainer);
  footer.appendChild(subMeta);

  drawer.appendChild(header);
  drawer.appendChild(messagesArea);
  drawer.appendChild(footer);

  // Toggle Drawer logic
  button.onclick = () => {
    const isHidden = drawer.style.display === "none";
    drawer.style.display = isHidden ? "flex" : "none";
  };

  // Form Submit Handler
  footer.onsubmit = async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    // Hide initial welcome card & prompt chips on first chat message
    const welcome = document.getElementById("copilot-welcome-card");
    const chipsBox = document.getElementById("copilot-chips-wrapper");
    if (welcome) welcome.style.display = "none";
    if (chipsBox) chipsBox.style.display = "none";

    // Append User Message (White Pill on Dark)
    const uMsg = document.createElement("div");
    uMsg.style.cssText = `
      align-self: flex-end;
      background: #ffffff;
      color: #000000;
      padding: 10px 14px;
      border-radius: 14px 14px 2px 14px;
      max-width: 85%;
      line-height: 1.4;
      font-size: 13px;
      font-weight: 500;
    `;
    uMsg.innerText = text;
    messagesArea.appendChild(uMsg);
    input.value = "";
    messagesArea.scrollTop = messagesArea.scrollHeight;

    // Loading Indicator
    const loadingMsg = document.createElement("div");
    loadingMsg.style.cssText = `
      align-self: flex-start;
      background: #18181b;
      color: #a1a1aa;
      padding: 10px 14px;
      border-radius: 14px 14px 14px 2px;
      font-style: italic;
      font-size: 12px;
      border: 1px solid #27272a;
    `;
    loadingMsg.innerText = "Processing instruction...";
    messagesArea.appendChild(loadingMsg);
    messagesArea.scrollTop = messagesArea.scrollHeight;

    const providerSelect = document.getElementById("copilot-provider-select");
    const selectedProvider = providerSelect ? providerSelect.value : "openai";

    try {
      const resp = await fetch("/api/v1/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: text,
          provider: selectedProvider
        })
      });
      const data = await resp.json();
      if (messagesArea.contains(loadingMsg)) {
        messagesArea.removeChild(loadingMsg);
      }

      // Append Assistant Response
      const aMsg = document.createElement("div");
      aMsg.style.cssText = `
        align-self: flex-start;
        background: #18181b;
        color: #ffffff;
        padding: 12px 14px;
        border-radius: 14px 14px 14px 2px;
        max-width: 90%;
        line-height: 1.45;
        font-size: 13px;
        border: 1px solid #27272a;
      `;
      let contentHtml = `<div>${data.response || "Task processed successfully."}</div>`;

      if (data.tool_result && data.tool_result.status === "success") {
        contentHtml += `
          <div style="margin-top:10px; padding:8px 12px; background:#27272a; color:#ffffff; border-radius:8px; font-size:12px; font-weight:500; border:1px solid #3f3f46;">
            ✓ Action Applied: <strong>${data.tool_result.action}</strong><br/>
            ${data.tool_result.message || ""}
          </div>
        `;
      }

      aMsg.innerHTML = contentHtml;
      messagesArea.appendChild(aMsg);
      messagesArea.scrollTop = messagesArea.scrollHeight;

    } catch (err) {
      if (messagesArea.contains(loadingMsg)) {
        messagesArea.removeChild(loadingMsg);
      }
      const errMsg = document.createElement("div");
      errMsg.style.cssText = `
        align-self: flex-start;
        background: #27272a;
        color: #fca5a5;
        padding: 10px 14px;
        border-radius: 14px;
        font-size: 12px;
        border: 1px solid #3f3f46;
      `;
      errMsg.innerText = "Error executing instruction. Ensure backend is active.";
      messagesArea.appendChild(errMsg);
      messagesArea.scrollTop = messagesArea.scrollHeight;
    }
  };

  // Ensure AI Copilot is only visible when navigating within Dashboard routes
  function isDashboardRoute() {
    const path = window.location.pathname.toLowerCase();
    const hash = window.location.hash.toLowerCase();
    return path.startsWith('/dashboard') || path.includes('/dashboard') || hash.includes('dashboard');
  }

  function updateVisibility() {
    const show = isDashboardRoute();
    if (show) {
      if (button.style.display === "none") {
        button.style.display = "flex";
      }
    } else {
      button.style.display = "none";
      drawer.style.display = "none";
    }
  }

  // Defer DOM insertion until AFTER React hydration has safely completed
  function initWidget() {
    if (document.getElementById("podbin-copilot-btn")) return;
    if (!document.body) return;

    document.body.appendChild(button);
    document.body.appendChild(drawer);

    const closeBtn = document.getElementById("copilot-close-btn");
    if (closeBtn) {
      closeBtn.onclick = () => {
        drawer.style.display = "none";
      };
    }

    updateVisibility();
  }

  // Listen to browser navigation events safely without overriding native history methods
  window.addEventListener("popstate", updateVisibility);
  window.addEventListener("hashchange", updateVisibility);
  setInterval(updateVisibility, 300);

  // Mount after hydration completes
  if (document.readyState === "complete" || document.readyState === "interactive") {
    setTimeout(initWidget, 500);
  } else {
    window.addEventListener("DOMContentLoaded", () => setTimeout(initWidget, 500));
    window.addEventListener("load", () => setTimeout(initWidget, 500));
  }
})();
