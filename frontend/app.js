// VoxDesk Frontend Controller — Redesigned UI + Preserved Backend Logic
(() => {
  // ─── CONFIG & STATE ───────────────────────────────────────────────
  const state = {
    apiUrl: localStorage.getItem("voxdesk_api_url") ||
      (window.location.port === "3001" ? "/api" : "http://127.0.0.1:8088"),
    apiToken: localStorage.getItem("voxdesk_api_token") || "voxdesk_secret_token_2026",
    orgId: localStorage.getItem("voxdesk_org_id") || "demo-org",
    callerPhone: localStorage.getItem("voxdesk_caller_phone") || "+91 98765 43210",
    theme: localStorage.getItem("voxdesk_theme") || "system",
    isCalling: false,
    isSpeaking: false,
    activeTab: "voice-console",
    recognition: null,
    audioContext: null,
    analyser: null,
    waveformPhase: 0,
    animFrameId: null,
  };

  // ─── DOM REFS ─────────────────────────────────────────────────────
  const $ = id => document.getElementById(id);

  const serverStatusBadge  = $("serverStatusBadge");
  const serverStatusText   = $("serverStatusText");
  const orgIdInput         = $("orgIdInput");
  const callerPhoneInput   = $("callerPhoneInput");
  const callLanguage       = $("callLanguage");
  const startCallBtn       = $("startCallBtn");
  const endCallBtn         = $("endCallBtn");
  const textTurnInput      = $("textTurnInput");
  const sendTurnBtn        = $("sendTurnBtn");
  const dialogueContainer  = $("dialogueContainer");
  const clearChatBtn       = $("clearChatBtn");
  const avatarCircle       = $("avatarCircle");
  const agentStatePill     = $("agentStatePill");
  const callStatusText     = $("callStatusText");
  const callSubLabel       = $("callSubLabel");

  const radarIntent    = $("radarIntent");
  const radarStatus    = $("radarStatus");
  const radarActions   = $("radarActions");
  const radarTicketBox = $("radarTicketBox");
  const radarTicketId  = $("radarTicketId");

  const ticketCountBadge    = $("ticketCountBadge");
  const knowledgeCountBadge = $("knowledgeCountBadge");
  const callsCountBadge     = $("callsCountBadge");
  const ticketsGrid         = $("ticketsGrid");
  const knowledgeListContainer = $("knowledgeListContainer");
  const callsListContainer  = $("callsListContainer");
  const addKnowledgeForm    = $("addKnowledgeForm");
  const docTextInput        = $("docTextInput");
  const ttsAudioPlayer      = $("ttsAudioPlayer");

  const settingsModal    = $("settingsModal");
  const openSettingsBtn  = $("openSettingsBtn");
  const closeSettingsBtn = $("closeSettingsBtn");
  const saveSettingsBtn  = $("saveSettingsBtn");
  const apiUrlInput      = $("apiUrlInput");
  const apiTokenInput    = $("apiTokenInput");
  const themeToggleBtn   = $("themeToggleBtn");

  const canvas = $("waveformCanvas");
  const ctx    = canvas ? canvas.getContext("2d") : null;

  // ─── INIT ─────────────────────────────────────────────────────────
  function init() {
    orgIdInput.value       = state.orgId;
    callerPhoneInput.value = state.callerPhone;
    apiUrlInput.value      = state.apiUrl;
    apiTokenInput.value    = state.apiToken;

    applyTheme(state.theme, /* persist */ false);
    setupThemeUI(state.theme);

    setupTabs();
    setupEventListeners();
    setupCanvasAnimation();
    setupSpeechRecognition();

    pingBackend();
    setInterval(pingBackend, 6000);
    loadAllData();
  }

  // ─── THEME ────────────────────────────────────────────────────────
  function applyTheme(themeVal, persist = true) {
    let resolved = themeVal;
    if (themeVal === "system") {
      resolved = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    document.documentElement.setAttribute("data-theme", resolved);
    if (persist) {
      localStorage.setItem("voxdesk_theme", themeVal);
      state.theme = themeVal;
    }
    // Update canvas colors on next draw
  }

  function setupThemeUI(themeVal) {
    // Update theme opt buttons in modal
    ["dark", "light", "system"].forEach(v => {
      const btn = $(`themeOpt${v.charAt(0).toUpperCase() + v.slice(1)}`);
      if (btn) btn.setAttribute("aria-pressed", (themeVal === v).toString());
    });
  }

  function cycleTheme() {
    const order = ["dark", "light", "system"];
    const next  = order[(order.indexOf(state.theme) + 1) % order.length];
    applyTheme(next);
    setupThemeUI(next);
  }

  // ─── HTTP ─────────────────────────────────────────────────────────
  async function apiFetch(endpoint, options = {}) {
    const url = state.apiUrl.replace(/\/+$/, "") + endpoint;
    const headers = {
      "Content-Type": "application/json",
      ...(state.apiToken ? { "X-Voice-Agent-Token": state.apiToken } : {}),
      ...(options.headers || {}),
    };
    return fetch(url, { ...options, headers });
  }

  // ─── BACKEND PING ─────────────────────────────────────────────────
  async function pingBackend() {
    try {
      const res = await apiFetch("/health", { method: "GET" });
      if (res.ok) {
        serverStatusBadge.className = "status-pill connected";
        serverStatusText.textContent = "Engine Connected";
      } else {
        throw new Error("HTTP " + res.status);
      }
    } catch {
      serverStatusBadge.className = "status-pill error";
      serverStatusText.textContent = "Engine Offline";
    }
  }

  // ─── DATA LOADING ─────────────────────────────────────────────────
  async function loadAllData() {
    loadTickets();
    loadKnowledge();
    loadCalls();
  }

  async function loadTickets() {
    try {
      const res = await apiFetch("/tickets");
      if (res.ok) {
        const data    = await res.json();
        const tickets = data.tickets || [];
        ticketCountBadge.textContent = tickets.length;
        renderTickets(tickets);
      }
    } catch (e) {
      console.warn("Failed to load tickets", e);
    }
  }

  function renderTickets(tickets) {
    if (!ticketsGrid) return;
    if (tickets.length === 0) {
      ticketsGrid.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon" aria-hidden="true">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/>
            </svg>
          </div>
          <strong>No tickets yet</strong>
          <span>Tickets appear automatically when callers report unresolved issues.</span>
        </div>`;
      return;
    }

    ticketsGrid.innerHTML = tickets.map((t, i) => `
      <div class="ticket-card" role="listitem" style="animation-delay:${i * 50}ms">
        <div class="ticket-header">
          <span class="ticket-id">${escapeHtml(t.id)}</span>
          <span class="ticket-status-badge">OPEN</span>
        </div>
        <div class="ticket-title">${escapeHtml(t.title)}</div>
        <div class="ticket-desc">${escapeHtml(t.description)}</div>
        <div class="ticket-footer">
          <div class="ticket-footer-item">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.19 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.11 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.09 8.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
            ${escapeHtml(t.caller_phone)}
          </div>
          <div class="ticket-footer-item">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>
            ${escapeHtml(t.call_id)}
          </div>
        </div>
      </div>
    `).join("");
  }

  async function loadKnowledge() {
    try {
      const res = await apiFetch(`/knowledge?organization_id=${encodeURIComponent(state.orgId)}`);
      if (res.ok) {
        const data = await res.json();
        const docs  = data.knowledge || [];
        knowledgeCountBadge.textContent = docs.length;
        renderKnowledge(docs);
      }
    } catch (e) {
      console.warn("Failed to load knowledge", e);
    }
  }

  function renderKnowledge(docs) {
    if (!knowledgeListContainer) return;
    if (docs.length === 0) {
      knowledgeListContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon" aria-hidden="true">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/>
            </svg>
          </div>
          <strong>No knowledge indexed</strong>
          <span>Add policies or FAQs using the form to get started.</span>
        </div>`;
      return;
    }

    knowledgeListContainer.innerHTML = docs.map((d, i) => `
      <div class="doc-card" role="listitem" style="animation-delay:${i * 40}ms">
        <div class="doc-meta">
          <span class="doc-id">#${escapeHtml(String(d.id))}</span>
          <span class="doc-org">${escapeHtml(d.organization_id)}</span>
        </div>
        <div class="doc-text">${escapeHtml(d.text)}</div>
      </div>
    `).join("");
  }

  async function loadCalls() {
    try {
      const res = await apiFetch(`/calls?organization_id=${encodeURIComponent(state.orgId)}`);
      if (res.ok) {
        const data  = await res.json();
        const calls = data.calls || [];
        callsCountBadge.textContent = calls.length;
        renderCalls(calls);
      }
    } catch (e) {
      console.warn("Failed to load calls", e);
    }
  }

  function renderCalls(calls) {
    if (!callsListContainer) return;
    if (calls.length === 0) {
      callsListContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon" aria-hidden="true">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.19 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.11 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.09 8.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>
            </svg>
          </div>
          <strong>No calls recorded</strong>
          <span>Call transcripts will appear here after sessions complete.</span>
        </div>`;
      return;
    }

    callsListContainer.innerHTML = calls.map((c, i) => `
      <div class="call-item" role="listitem" style="animation-delay:${i * 50}ms">
        <div class="call-meta-row">
          <span class="call-id-chip">${escapeHtml(c.id)}</span>
          <div class="call-meta-chips">
            <span class="call-chip">${escapeHtml(c.language || "—")}</span>
            <span class="call-chip">${escapeHtml(c.caller_phone || "—")}</span>
          </div>
        </div>
        <div class="call-turns">
          ${(c.turns || []).length === 0
            ? `<div class="call-turn-line" style="color:var(--text-muted)">No turns recorded.</div>`
            : (c.turns || []).map(t => `<div class="call-turn-line">${escapeHtml(t)}</div>`).join("")}
        </div>
      </div>
    `).join("");
  }

  // ─── TURN HANDLING (preserved backend logic) ───────────────────────
  async function handleTurn(text) {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();

    appendMessage("customer", cleanText);
    setAgentState("thinking", "AI is evaluating response & policies…", "");

    try {
      const payload = {
        organization_id: state.orgId,
        caller_phone:    state.callerPhone,
        text:            cleanText,
        language:        callLanguage.value,
      };

      const res = await apiFetch("/calls/turn", {
        method: "POST",
        body:   JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("HTTP error " + res.status);

      const decision = await res.json();

      // Update Radar with flash animation
      updateRadarItem("radarIntentItem",  () => { radarIntent.textContent  = decision.intent  || "—"; });
      updateRadarItem("radarStatusItem",  () => { radarStatus.textContent  = decision.status  || "—"; });
      updateRadarItem("radarActionsItem", () => { radarActions.textContent = (decision.actions || []).join(", ") || "REPLY"; });

      if (decision.ticket_id) {
        radarTicketBox.style.display = "flex";
        updateRadarItem("radarTicketBox", () => { radarTicketId.textContent = decision.ticket_id; });
        loadTickets();
      }

      appendMessage("agent", decision.reply);
      await playTTS(decision.reply, callLanguage.value);
      loadCalls();

    } catch (err) {
      appendMessage("agent", "Error connecting to AI engine: " + err.message);
      setAgentState("error", "Connection error", "Check backend settings");
      return;
    } finally {
      if (state.isCalling) {
        setAgentState("listening", "Listening — speak into your microphone", "Live call active");
      } else {
        setAgentState("idle", "Ready to start voice conversation", "");
      }
    }
  }

  function updateRadarItem(itemId, updateFn) {
    const el = $(itemId);
    if (!el) return;
    updateFn();
    el.classList.add("updated");
    setTimeout(() => el.classList.remove("updated"), 800);
  }

  // ─── TTS (preserved) ─────────────────────────────────────────────
  async function playTTS(text, lang) {
    try {
      const res = await apiFetch("/tts/synthesize", {
        method: "POST",
        body:   JSON.stringify({ text, language: lang }),
      });

      if (res.ok) {
        const blob     = await res.blob();
        const audioUrl = URL.createObjectURL(blob);
        ttsAudioPlayer.src = audioUrl;
        state.isSpeaking = true;
        setAgentState("speaking", "AI Agent is speaking…", "");
        await ttsAudioPlayer.play().catch(() => {});
        ttsAudioPlayer.onended = () => {
          state.isSpeaking = false;
        };
      }
    } catch (e) {
      console.warn("TTS playback fallback", e);
    }
  }

  // ─── DIALOGUE MESSAGES ────────────────────────────────────────────
  function appendMessage(speaker, text) {
    // Remove empty state
    const empty = dialogueContainer.querySelector(".dialogue-empty");
    if (empty) empty.remove();

    const row = document.createElement("div");
    row.className = `msg-row ${speaker}`;
    row.innerHTML = `
      <div class="msg-label">${speaker === "customer" ? "Caller" : "VoxDesk AI"}</div>
      <div class="msg-bubble">${escapeHtml(text)}</div>
    `;

    dialogueContainer.appendChild(row);

    // Auto-scroll — only if near bottom
    const nearBottom = dialogueContainer.scrollHeight - dialogueContainer.scrollTop - dialogueContainer.clientHeight < 80;
    if (nearBottom) {
      dialogueContainer.scrollTop = dialogueContainer.scrollHeight;
    }
  }

  // ─── AGENT STATE ──────────────────────────────────────────────────
  function setAgentState(stateKey, status, subLabel) {
    // State badge
    agentStatePill.setAttribute("data-state", stateKey);
    agentStatePill.querySelector(".state-text").textContent = stateKey.toUpperCase();

    // Visualizer text
    if (callStatusText) callStatusText.textContent = status;
    if (callSubLabel)   callSubLabel.textContent   = subLabel || "";

    // Avatar class
    const avatar = avatarCircle;
    avatar.className = `agent-avatar state-${stateKey}`;

    // Visualizer border
    const wrap = document.getElementById("visualizerWrap");
    if (wrap) {
      wrap.classList.remove("active-call", "speaking");
      if (stateKey === "listening" || stateKey === "connecting" || stateKey === "thinking") {
        wrap.classList.add("active-call");
      } else if (stateKey === "speaking") {
        wrap.classList.add("speaking");
      }
    }
  }

  // ─── SPEECH RECOGNITION (preserved) ──────────────────────────────
  function setupSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.warn("Web Speech API not supported in this browser.");
      return;
    }

    const rec        = new SpeechRec();
    rec.continuous   = true;
    rec.interimResults = false;

    rec.onresult = (event) => {
      const last = event.results.length - 1;
      const text = event.results[last][0].transcript;
      if (text && text.trim()) handleTurn(text.trim());
    };

    rec.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
    };

    rec.onend = () => {
      if (state.isCalling) {
        try { rec.start(); } catch (_) {}
      }
    };

    state.recognition = rec;
  }

  // ─── CALL START / END (preserved + new state) ─────────────────────
  function startCall() {
    state.isCalling = true;
    startCallBtn.disabled = true;
    endCallBtn.disabled   = false;

    setAgentState("connecting", "Connecting to voice session…", "");

    setTimeout(() => {
      if (state.isCalling) {
        setAgentState("listening", "Live call active — speak now", "Microphone active");
      }
    }, 800);

    if (state.recognition) {
      state.recognition.lang = callLanguage.value;
      try {
        state.recognition.start();
      } catch (e) {
        console.warn("Recognition already running", e);
      }
    }
  }

  function endCall() {
    state.isCalling  = false;
    state.isSpeaking = false;
    startCallBtn.disabled = false;
    endCallBtn.disabled   = true;

    setAgentState("idle", "Call terminated. Ready.", "");

    if (state.recognition) {
      try { state.recognition.stop(); } catch (_) {}
    }
  }

  // ─── TABS (preserved + indicator) ────────────────────────────────
  function setupTabs() {
    document.querySelectorAll(".nav-tab").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-tab").forEach(b => {
          b.classList.remove("active");
          b.setAttribute("aria-selected", "false");
        });
        document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));

        btn.classList.add("active");
        btn.setAttribute("aria-selected", "true");
        const targetId = btn.getAttribute("data-tab");
        const panel    = document.getElementById(targetId);
        if (panel) panel.classList.add("active");
        state.activeTab = targetId;
      });
    });
  }

  // ─── EVENT LISTENERS ──────────────────────────────────────────────
  function setupEventListeners() {
    startCallBtn.addEventListener("click", startCall);
    endCallBtn.addEventListener("click",   endCall);

    sendTurnBtn.addEventListener("click", () => {
      const val = textTurnInput.value;
      if (val.trim()) {
        handleTurn(val.trim());
        textTurnInput.value = "";
      }
    });

    textTurnInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendTurnBtn.click();
      }
    });

    clearChatBtn.addEventListener("click", () => {
      dialogueContainer.innerHTML = `
        <div class="dialogue-empty" id="dialogueEmpty">
          <div class="dialogue-empty-icon" aria-hidden="true">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          </div>
          <p>Dialogue streams here in real-time as calls progress.</p>
        </div>`;
    });

    // Knowledge Form
    addKnowledgeForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text    = docTextInput.value.trim();
      if (!text) return;

      const saveBtn = $("saveDocBtn");
      saveBtn.disabled = true;

      const origContent = saveBtn.innerHTML;
      saveBtn.innerHTML = `
        <span class="spinner" style="width:14px;height:14px;border-width:2px" aria-hidden="true"></span>
        Indexing…`;

      try {
        const res = await apiFetch("/knowledge", {
          method: "POST",
          body:   JSON.stringify({ organization_id: state.orgId, text }),
        });

        if (res.ok) {
          docTextInput.value = "";
          await loadKnowledge();
        } else {
          alert("Error adding knowledge: " + res.statusText);
        }
      } catch (err) {
        alert("Failed to add knowledge: " + err.message);
      } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = origContent;
      }
    });

    // Refresh buttons
    $("refreshTicketsBtn")?.addEventListener("click",   loadTickets);
    $("refreshKnowledgeBtn")?.addEventListener("click", loadKnowledge);
    $("refreshCallsBtn")?.addEventListener("click",     loadCalls);

    // Settings Modal
    openSettingsBtn.addEventListener("click",  () => settingsModal.showModal());
    closeSettingsBtn.addEventListener("click", () => settingsModal.close());
    settingsModal.addEventListener("click",    (e) => {
      if (e.target === settingsModal) settingsModal.close();
    });

    saveSettingsBtn.addEventListener("click", () => {
      state.apiUrl   = apiUrlInput.value.trim() || "http://127.0.0.1:8088";
      state.apiToken = apiTokenInput.value.trim();
      localStorage.setItem("voxdesk_api_url",   state.apiUrl);
      localStorage.setItem("voxdesk_api_token", state.apiToken);
      settingsModal.close();
      pingBackend();
      loadAllData();
    });

    // Theme buttons in modal
    document.querySelectorAll(".theme-opt-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const val = btn.getAttribute("data-theme-val");
        applyTheme(val);
        setupThemeUI(val);
      });
    });

    // Theme toggle in header cycles themes
    if (themeToggleBtn) {
      themeToggleBtn.addEventListener("click", cycleTheme);
    }

    // Org / phone inputs
    orgIdInput.addEventListener("change", () => {
      state.orgId = orgIdInput.value.trim() || "demo-org";
      localStorage.setItem("voxdesk_org_id", state.orgId);
      loadAllData();
    });

    callerPhoneInput.addEventListener("change", () => {
      state.callerPhone = callerPhoneInput.value.trim() || "+91 98765 43210";
      localStorage.setItem("voxdesk_caller_phone", state.callerPhone);
    });

    // Respect OS theme change when in system mode
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (state.theme === "system") applyTheme("system", false);
    });
  }

  // ─── WAVEFORM CANVAS (enhanced) ───────────────────────────────────
  function setupCanvasAnimation() {
    if (!canvas || !ctx) return;

    function resize() {
      const rect = canvas.parentElement.getBoundingClientRect();
      canvas.width  = rect.width;
      canvas.height = rect.height;
    }

    const ro = new ResizeObserver(resize);
    ro.observe(canvas.parentElement);
    resize();

    function getThemeColors() {
      const isDark = document.documentElement.getAttribute("data-theme") === "dark";
      return {
        idle:    isDark ? "rgba(56,189,248,0.18)"  : "rgba(14,165,233,0.2)",
        active:  isDark ? "rgba(14,165,233,0.55)"  : "rgba(14,165,233,0.6)",
        speak:   isDark ? "rgba(16,185,129,0.6)"   : "rgba(16,185,129,0.65)",
        think:   isDark ? "rgba(99,102,241,0.5)"   : "rgba(99,102,241,0.55)",
        center:  isDark ? "rgba(255,255,255,0.06)"  : "rgba(0,0,0,0.05)",
      };
    }

    function draw() {
      state.animFrameId = requestAnimationFrame(draw);
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      state.waveformPhase += state.isSpeaking ? 0.07 : state.isCalling ? 0.05 : 0.025;

      const w   = canvas.width;
      const h   = canvas.height;
      const mid = h / 2;
      const c   = getThemeColors();

      let amp, baseColor, layers;

      if (state.isSpeaking) {
        amp = h * 0.28; baseColor = c.speak; layers = 4;
      } else if (state.isCalling) {
        amp = h * 0.18; baseColor = c.active; layers = 3;
      } else {
        amp = h * 0.055; baseColor = c.idle; layers = 2;
      }

      // Center line
      ctx.beginPath();
      ctx.moveTo(0, mid);
      ctx.lineTo(w, mid);
      ctx.strokeStyle = c.center;
      ctx.lineWidth = 1;
      ctx.stroke();

      // Sine wave layers
      for (let layer = 0; layer < layers; layer++) {
        ctx.beginPath();
        ctx.lineWidth  = Math.max(1.2, 2.2 - layer * 0.4);

        const alpha = 1 - layer * 0.22;
        ctx.strokeStyle = baseColor.replace(/[\d.]+\)$/, m => {
          const num = parseFloat(m);
          return (num * alpha).toFixed(2) + ")";
        });

        const phaseOff = layer * 1.05;
        const freqMul  = 9 + layer * 1.5;
        const layerAmp = amp * (1 - layer * 0.18);

        ctx.moveTo(0, mid);
        for (let x = 0; x <= w; x += 3) {
          const nx  = x / w;
          const env = Math.sin(nx * Math.PI); // pin edges
          const y   = mid + Math.sin(nx * freqMul + state.waveformPhase + phaseOff) * layerAmp * env;
          x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
    }

    draw();
  }

  // ─── UTILITY ──────────────────────────────────────────────────────
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // ─── BOOT ─────────────────────────────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
