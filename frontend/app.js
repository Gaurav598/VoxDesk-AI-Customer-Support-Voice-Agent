// VoxDesk Dedicated Frontend Controller
(() => {
  // Config & State
  const state = {
    apiUrl: localStorage.getItem("voxdesk_api_url") || (window.location.port === "3001" ? "/api" : "http://127.0.0.1:8088"),
    apiToken: localStorage.getItem("voxdesk_api_token") || "voxdesk_secret_token_2026",
    orgId: localStorage.getItem("voxdesk_org_id") || "demo-org",
    callerPhone: localStorage.getItem("voxdesk_caller_phone") || "+91 98765 43210",
    isCalling: false,
    isSpeaking: false,
    activeTab: "voice-console",
    recognition: null,
    audioContext: null,
    analyser: null,
    waveformPhase: 0,
  };

  // DOM Elements
  const serverStatusBadge = document.getElementById("serverStatusBadge");
  const serverStatusText = document.getElementById("serverStatusText");
  const orgIdInput = document.getElementById("orgIdInput");
  const callerPhoneInput = document.getElementById("callerPhoneInput");
  const callLanguage = document.getElementById("callLanguage");
  const startCallBtn = document.getElementById("startCallBtn");
  const endCallBtn = document.getElementById("endCallBtn");
  const textTurnInput = document.getElementById("textTurnInput");
  const sendTurnBtn = document.getElementById("sendTurnBtn");
  const dialogueContainer = document.getElementById("dialogueContainer");
  const clearChatBtn = document.getElementById("clearChatBtn");
  const avatarCircle = document.getElementById("avatarCircle");
  const agentStatePill = document.getElementById("agentStatePill");
  const callStatusText = document.getElementById("callStatusText");
  
  // Radar Elements
  const radarIntent = document.getElementById("radarIntent");
  const radarStatus = document.getElementById("radarStatus");
  const radarActions = document.getElementById("radarActions");
  const radarTicketBox = document.getElementById("radarTicketBox");
  const radarTicketId = document.getElementById("radarTicketId");

  // Badges & Views
  const ticketCountBadge = document.getElementById("ticketCountBadge");
  const knowledgeCountBadge = document.getElementById("knowledgeCountBadge");
  const callsCountBadge = document.getElementById("callsCountBadge");
  const ticketsGrid = document.getElementById("ticketsGrid");
  const knowledgeListContainer = document.getElementById("knowledgeListContainer");
  const callsListContainer = document.getElementById("callsListContainer");
  const addKnowledgeForm = document.getElementById("addKnowledgeForm");
  const docTextInput = document.getElementById("docTextInput");
  const ttsAudioPlayer = document.getElementById("ttsAudioPlayer");

  // Settings Modal Elements
  const settingsModal = document.getElementById("settingsModal");
  const openSettingsBtn = document.getElementById("openSettingsBtn");
  const closeSettingsBtn = document.getElementById("closeSettingsBtn");
  const saveSettingsBtn = document.getElementById("saveSettingsBtn");
  const apiUrlInput = document.getElementById("apiUrlInput");
  const apiTokenInput = document.getElementById("apiTokenInput");

  // Canvas Waveform
  const canvas = document.getElementById("waveformCanvas");
  const ctx = canvas ? canvas.getContext("2d") : null;

  // Initialize
  function init() {
    orgIdInput.value = state.orgId;
    callerPhoneInput.value = state.callerPhone;
    apiUrlInput.value = state.apiUrl;
    apiTokenInput.value = state.apiToken;

    setupTabs();
    setupEventListeners();
    setupCanvasAnimation();
    setupSpeechRecognition();
    
    // Initial data fetches & status ping
    pingBackend();
    setInterval(pingBackend, 6000);
    loadAllData();
  }

  // HTTP Helper with auth
  async function apiFetch(endpoint, options = {}) {
    // If running under nginx proxy, fallback to relative URL or direct backend URL
    const url = state.apiUrl.replace(/\/+$/, "") + endpoint;
    const headers = {
      "Content-Type": "application/json",
      ...(state.apiToken ? { "X-Voice-Agent-Token": state.apiToken } : {}),
      ...(options.headers || {})
    };

    return fetch(url, { ...options, headers });
  }

  // Ping Backend Health
  async function pingBackend() {
    try {
      const res = await apiFetch("/health", { method: "GET" });
      if (res.ok) {
        serverStatusBadge.className = "status-indicator";
        serverStatusText.textContent = "Engine Connected (8088)";
      } else {
        throw new Error("HTTP " + res.status);
      }
    } catch (err) {
      serverStatusBadge.className = "status-indicator error";
      serverStatusText.textContent = "Engine Offline";
    }
  }

  // Load Tickets, Knowledge, Calls
  async function loadAllData() {
    loadTickets();
    loadKnowledge();
    loadCalls();
  }

  async function loadTickets() {
    try {
      const res = await apiFetch("/tickets");
      if (res.ok) {
        const data = await res.json();
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
      ticketsGrid.innerHTML = `<div class="empty-state">No support tickets generated yet. Start a call and simulate an issue to see tickets appear automatically!</div>`;
      return;
    }

    ticketsGrid.innerHTML = tickets.map(t => `
      <div class="ticket-card">
        <div class="ticket-top">
          <span class="ticket-id">${t.id}</span>
          <span class="badge-version">OPEN</span>
        </div>
        <div class="ticket-title">${escapeHtml(t.title)}</div>
        <div class="ticket-desc">${escapeHtml(t.description)}</div>
        <div class="ticket-footer">
          <span>Caller: ${escapeHtml(t.caller_phone)}</span>
          <span>Call: ${escapeHtml(t.call_id)}</span>
        </div>
      </div>
    `).join("");
  }

  async function loadKnowledge() {
    try {
      const res = await apiFetch(`/knowledge?organization_id=${encodeURIComponent(state.orgId)}`);
      if (res.ok) {
        const data = await res.json();
        const docs = data.knowledge || [];
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
      knowledgeListContainer.innerHTML = `<div class="empty-state">No knowledge indexed for ${escapeHtml(state.orgId)}. Add policies or FAQs using the form!</div>`;
      return;
    }

    knowledgeListContainer.innerHTML = docs.map(d => `
      <div class="doc-card">
        <div class="doc-id">${d.id} • ${escapeHtml(d.organization_id)}</div>
        <div class="doc-text">${escapeHtml(d.text)}</div>
      </div>
    `).join("");
  }

  async function loadCalls() {
    try {
      const res = await apiFetch(`/calls?organization_id=${encodeURIComponent(state.orgId)}`);
      if (res.ok) {
        const data = await res.json();
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
      callsListContainer.innerHTML = `<div class="empty-state">No call logs recorded yet.</div>`;
      return;
    }

    callsListContainer.innerHTML = calls.map(c => `
      <div class="call-item">
        <div class="call-header-meta">
          <span class="call-id-badge">${c.id}</span>
          <span class="badge-version">${c.language} • ${c.caller_phone}</span>
        </div>
        <div class="call-turns-wrapper">
          ${(c.turns || []).map(turn => `<div>${escapeHtml(turn)}</div>`).join("")}
        </div>
      </div>
    `).join("");
  }

  // Handle Turn Submission
  async function handleTurn(text) {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();

    // Append customer message
    appendBubble("customer", cleanText);

    // Update status
    agentStatePill.textContent = "THINKING";
    agentStatePill.className = "live-pill";
    callStatusText.textContent = "AI is evaluating response & policies...";

    try {
      const payload = {
        organization_id: state.orgId,
        caller_phone: state.callerPhone,
        text: cleanText,
        language: callLanguage.value,
      };

      const res = await apiFetch("/calls/turn", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("HTTP error " + res.status);
      }

      const decision = await res.json();

      // Update Radar
      radarIntent.textContent = decision.intent || "—";
      radarStatus.textContent = decision.status || "—";
      radarActions.textContent = (decision.actions || []).join(", ") || "REPLY";

      if (decision.ticket_id) {
        radarTicketBox.style.display = "block";
        radarTicketId.textContent = decision.ticket_id;
        loadTickets();
      }

      // Append agent reply
      appendBubble("agent", decision.reply);

      // Play synthesized voice
      await playTTS(decision.reply, callLanguage.value);

      // Refresh calls history
      loadCalls();

    } catch (err) {
      appendBubble("agent", "Error connecting to AI engine: " + err.message);
    } finally {
      if (state.isCalling) {
        agentStatePill.textContent = "LISTENING";
        agentStatePill.className = "live-pill listening";
        callStatusText.textContent = "Listening to your voice (speak now)...";
      } else {
        agentStatePill.textContent = "IDLE";
        agentStatePill.className = "live-pill";
        callStatusText.textContent = "Ready to start call";
      }
    }
  }

  // Play TTS
  async function playTTS(text, lang) {
    try {
      const res = await apiFetch("/tts/synthesize", {
        method: "POST",
        body: JSON.stringify({ text, language: lang }),
      });

      if (res.ok) {
        const blob = await res.blob();
        const audioUrl = URL.createObjectURL(blob);
        ttsAudioPlayer.src = audioUrl;
        state.isSpeaking = true;
        await ttsAudioPlayer.play().catch(() => {});
        ttsAudioPlayer.onended = () => {
          state.isSpeaking = false;
        };
      }
    } catch (e) {
      console.warn("TTS playback fallback", e);
    }
  }

  // Dialogue Append
  function appendBubble(speaker, text) {
    const placeholder = dialogueContainer.querySelector(".chat-placeholder");
    if (placeholder) placeholder.remove();

    const bubble = document.createElement("div");
    bubble.className = `dialogue-bubble ${speaker}`;
    bubble.innerHTML = `
      <div class="bubble-meta">${speaker === "customer" ? "Caller" : "VoxDesk AI Agent"}</div>
      <div class="bubble-body">${escapeHtml(text)}</div>
    `;

    dialogueContainer.appendChild(bubble);
    dialogueContainer.scrollTop = dialogueContainer.scrollHeight;
  }

  // Web Speech API
  function setupSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.warn("Web Speech API not supported in this browser.");
      return;
    }

    const rec = new SpeechRec();
    rec.continuous = true;
    rec.interimResults = false;

    rec.onresult = (event) => {
      const last = event.results.length - 1;
      const text = event.results[last][0].transcript;
      if (text && text.trim()) {
        handleTurn(text.trim());
      }
    };

    rec.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
    };

    rec.onend = () => {
      if (state.isCalling) {
        // Restart if still in call mode
        try { rec.start(); } catch (_) {}
      }
    };

    state.recognition = rec;
  }

  // Start / End Call
  function startCall() {
    state.isCalling = true;
    startCallBtn.disabled = true;
    endCallBtn.disabled = false;
    avatarCircle.classList.add("active");
    agentStatePill.textContent = "LISTENING";
    agentStatePill.className = "live-pill calling";
    callStatusText.textContent = "Live call active — speak into your microphone!";

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
    state.isCalling = false;
    state.isSpeaking = false;
    startCallBtn.disabled = false;
    endCallBtn.disabled = true;
    avatarCircle.classList.remove("active");
    agentStatePill.textContent = "IDLE";
    agentStatePill.className = "live-pill";
    callStatusText.textContent = "Call terminated. Ready.";

    if (state.recognition) {
      try { state.recognition.stop(); } catch (_) {}
    }
  }

  // Tabs Navigation
  function setupTabs() {
    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => {
          b.classList.remove("active");
          b.setAttribute("aria-selected", "false");
        });
        document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));

        btn.classList.add("active");
        btn.setAttribute("aria-selected", "true");
        const targetId = btn.getAttribute("data-tab");
        const panel = document.getElementById(targetId);
        if (panel) panel.classList.add("active");
        state.activeTab = targetId;
      });
    });
  }

  // Setup Event Listeners
  function setupEventListeners() {
    startCallBtn.addEventListener("click", startCall);
    endCallBtn.addEventListener("click", endCall);

    sendTurnBtn.addEventListener("click", () => {
      const val = textTurnInput.value;
      if (val.trim()) {
        handleTurn(val.trim());
        textTurnInput.value = "";
      }
    });

    textTurnInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        sendTurnBtn.click();
      }
    });

    clearChatBtn.addEventListener("click", () => {
      dialogueContainer.innerHTML = `
        <div class="chat-placeholder">
          <p>Speech will stream here in real-time as dialogue progresses.</p>
        </div>
      `;
    });

    // Knowledge Form Submit
    addKnowledgeForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = docTextInput.value.trim();
      if (!text) return;

      const saveBtn = document.getElementById("saveDocBtn");
      saveBtn.disabled = true;
      saveBtn.textContent = "Indexing...";

      try {
        const res = await apiFetch("/knowledge", {
          method: "POST",
          body: JSON.stringify({
            organization_id: state.orgId,
            text: text,
          }),
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
        saveBtn.textContent = "Index & Store Document";
      }
    });

    // Refresh Buttons
    document.getElementById("refreshTicketsBtn")?.addEventListener("click", loadTickets);
    document.getElementById("refreshKnowledgeBtn")?.addEventListener("click", loadKnowledge);
    document.getElementById("refreshCallsBtn")?.addEventListener("click", loadCalls);

    // Settings Modal
    openSettingsBtn.addEventListener("click", () => settingsModal.showModal());
    closeSettingsBtn.addEventListener("click", () => settingsModal.close());
    saveSettingsBtn.addEventListener("click", () => {
      state.apiUrl = apiUrlInput.value.trim() || "http://127.0.0.1:8088";
      state.apiToken = apiTokenInput.value.trim();
      localStorage.setItem("voxdesk_api_url", state.apiUrl);
      localStorage.setItem("voxdesk_api_token", state.apiToken);
      settingsModal.close();
      pingBackend();
      loadAllData();
    });

    orgIdInput.addEventListener("change", () => {
      state.orgId = orgIdInput.value.trim() || "demo-org";
      localStorage.setItem("voxdesk_org_id", state.orgId);
      loadAllData();
    });

    callerPhoneInput.addEventListener("change", () => {
      state.callerPhone = callerPhoneInput.value.trim() || "+91 98765 43210";
      localStorage.setItem("voxdesk_caller_phone", state.callerPhone);
    });
  }

  // Waveform Canvas Animation
  function setupCanvasAnimation() {
    if (!canvas || !ctx) return;

    function resize() {
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
    }
    window.addEventListener("resize", resize);
    resize();

    function draw() {
      requestAnimationFrame(draw);
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      state.waveformPhase += 0.04;
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      // Color and amplitude based on state
      let amp = 8;
      let strokeColor = "rgba(56, 189, 248, 0.25)";

      if (state.isSpeaking) {
        amp = 32;
        strokeColor = "rgba(16, 185, 129, 0.75)";
      } else if (state.isCalling) {
        amp = 20;
        strokeColor = "rgba(239, 68, 68, 0.65)";
      }

      // Draw 3 layered sine waves
      for (let layer = 0; layer < 3; layer++) {
        ctx.beginPath();
        ctx.lineWidth = 2 - layer * 0.4;
        ctx.strokeStyle = strokeColor;

        const phaseOffset = layer * 1.2;
        const layerAmp = amp * (1 - layer * 0.25);

        for (let x = 0; x < width; x += 4) {
          const normX = x / width;
          const envelope = Math.sin(normX * Math.PI); // Pin edges to zero
          const y = centerY + Math.sin(normX * 12 + state.waveformPhase + phaseOffset) * layerAmp * envelope;

          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
    }

    draw();
  }

  // Utility
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Run on DOM Ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
