import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from voice_agent.platform import PlatformService
from voice_agent.storage import SQLiteStore
from voice_agent.tts_engine import TTSEngine, create_tts_engine


class JsonRouter:
    def __init__(
        self,
        service: PlatformService,
        api_token: str | None = None,
        tts_engine: TTSEngine | None = None,
    ) -> None:
        self.service = service
        self.api_token = api_token
        self.tts_engine = tts_engine or create_tts_engine()

    def handle_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict, str | bytes]:
        payload = payload or {}
        headers = headers or {}
        parsed_path = urlparse(path)
        route_path = parsed_path.path
        if method == "GET" and path == "/health":
            return self._json(200, {"status": "ok"})
        if method == "GET" and route_path == "/browser-call":
            return (
                200,
                {"Content-Type": "text/html; charset=utf-8"},
                browser_call_test_page(),
            )
        if method == "GET" and route_path == "/webhooks/exotel/inbound":
            params = {key: values[-1] for key, values in parse_qs(parsed_path.query).items()}
            print("Exotel inbound webhook received")
            return self._json(
                200,
                {
                    "status": "exotel_inbound_received",
                    "call_sid": params.get("CallSid"),
                    "from": params.get("CallFrom") or params.get("From"),
                    "to": params.get("CallTo") or params.get("To"),
                },
            )
        if not self._authorized(headers):
            return self._json(401, {"error": "unauthorized"})
        if method == "POST" and path == "/knowledge":
            return self._json(
                200,
                self.service.add_knowledge(
                    organization_id=str(payload["organization_id"]),
                    text=str(payload["text"]),
                ),
            )
        if method == "POST" and path == "/calls/turn":
            return self._json(
                200,
                self.service.handle_support_turn(
                    organization_id=str(payload["organization_id"]),
                    caller_phone=str(payload["caller_phone"]),
                    text=str(payload["text"]),
                    language=str(payload.get("language", "unknown")),
                ),
            )
        if method == "POST" and path == "/tts/synthesize":
            audio = self.tts_engine.synthesize(
                text=str(payload["text"]),
                language=str(payload.get("language", "en-IN")),
            )
            return 200, {"Content-Type": audio.content_type}, audio.data
        if method == "GET" and path == "/tickets":
            return self._json(200, {"tickets": self.service.list_tickets()})
        return self._json(404, {"error": "not_found", "path": path})

    def _authorized(self, headers: dict[str, str]) -> bool:
        if not self.api_token:
            return True
        return headers.get("X-Voice-Agent-Token") == self.api_token

    def _json(self, status: int, body: dict) -> tuple[int, dict, str]:
        return status, {"Content-Type": "application/json"}, json.dumps(body)


def create_handler(
    service: PlatformService,
    api_token: str | None = None,
    tts_engine: TTSEngine | None = None,
) -> JsonRouter:
    return JsonRouter(service, api_token=api_token, tts_engine=tts_engine)


def browser_call_test_page() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>VoxDesk Browser Call Test</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #070707; color: #f4f4f5; }
    main { max-width: 880px; margin: 0 auto; padding: 40px 20px; }
    .card { background: #151515; border: 1px solid #2b2b2b; border-radius: 18px; padding: 24px; box-shadow: 0 20px 50px rgba(0,0,0,.35); }
    h1 { margin: 0 0 10px; font-size: 30px; }
    p { color: #b9b9c0; line-height: 1.55; }
    label { display: block; margin-top: 18px; color: #d4d4d8; font-size: 14px; }
    input, textarea { width: 100%; box-sizing: border-box; margin-top: 8px; padding: 12px 14px; border: 1px solid #3f3f46; border-radius: 12px; background: #0b0b0b; color: white; font-size: 15px; }
    textarea { min-height: 96px; resize: vertical; }
    .row { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 18px; }
    .inline { display: flex; align-items: center; gap: 10px; margin-top: 18px; color: #d4d4d8; }
    button { border: 0; border-radius: 999px; padding: 12px 18px; background: #fafafa; color: #050505; font-weight: 800; cursor: pointer; }
    button.secondary { background: #27272a; color: #fff; }
    button:disabled { opacity: .45; cursor: not-allowed; }
    select { width: 100%; box-sizing: border-box; margin-top: 8px; padding: 12px 14px; border: 1px solid #3f3f46; border-radius: 12px; background: #0b0b0b; color: white; font-size: 15px; }
    .status { margin-top: 18px; padding: 12px 14px; border-radius: 12px; background: #202020; color: #d4d4d8; }
    .turns { margin-top: 20px; display: grid; gap: 12px; }
    .bubble { padding: 14px 16px; border-radius: 14px; background: #222; }
    .bubble.user { background: #17365d; }
    .bubble.agent { background: #1d3b2a; }
    .meta { font-size: 12px; color: #a1a1aa; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .08em; }
  </style>
</head>
<body>
  <main>
    <section class="card">
      <h1>VoxDesk Browser Call Test</h1>
      <p>This is the local browser version of the phone-call loop: speak → browser STT → backend agent → browser TTS. Use Chrome/Safari with microphone permission.</p>

      <label>API token from .env / VOICE_AGENT_API_TOKEN</label>
      <input id="token" type="password" autocomplete="off" placeholder="Paste token once for local protected endpoints" />

      <label>Organization ID</label>
      <input id="organizationId" value="demo-org" />

      <label>Your phone / caller label</label>
      <input id="callerPhone" value="browser-user" />

      <label>Call language</label>
      <select id="languageSelect">
        <option value="en-IN">English India</option>
        <option value="hi-IN">Hindi India</option>
        <option value="te-IN">Telugu India</option>
      </select>

      <label>Transcript</label>
      <textarea id="transcript" placeholder="Click Start talking, or type here and Send."></textarea>

      <p><strong>Voice:</strong> server-side neural TTS. Browser TTS is disabled.</p>

      <label class="inline">
        <input id="liveMode" type="checkbox" checked style="width:auto; margin:0;" />
        Live conversation mode
      </label>

      <div class="row">
        <button id="startBtn">Start live call</button>
        <button id="stopBtn" class="secondary" disabled>Stop</button>
        <button id="sendBtn" class="secondary">Send typed text</button>
        <button id="clearBtn" class="secondary">Clear</button>
      </div>

      <div id="status" class="status">Ready.</div>
      <div id="turns" class="turns"></div>
    </section>
  </main>

  <script>
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const startBtn = document.getElementById("startBtn");
    const stopBtn = document.getElementById("stopBtn");
    const sendBtn = document.getElementById("sendBtn");
    const clearBtn = document.getElementById("clearBtn");
    const transcript = document.getElementById("transcript");
    const token = document.getElementById("token");
    const organizationId = document.getElementById("organizationId");
    const callerPhone = document.getElementById("callerPhone");
    const languageSelect = document.getElementById("languageSelect");
    const liveMode = document.getElementById("liveMode");
    const statusBox = document.getElementById("status");
    const turns = document.getElementById("turns");
    let recognition = null;
    let callActive = false;
    let agentSpeaking = false;
    let sending = false;
    let lastFinalTranscript = "";
    let currentAudio = null;

    function setStatus(text) { statusBox.textContent = text; }
    function addTurn(who, text) {
      const node = document.createElement("div");
      node.className = "bubble " + who;
      node.innerHTML = `<div class="meta">${who}</div><div></div>`;
      node.querySelector("div:last-child").textContent = text;
      turns.prepend(node);
    }
    function selectedLanguage() {
      return languageSelect.value || "en-IN";
    }
    async function speak(text) {
      if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
      }
      agentSpeaking = true;
      stopListeningOnly();
      setStatus("Generating human-like voice...");
      try {
        const response = await fetch("/tts/synthesize", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Voice-Agent-Token": token.value.trim()
          },
          body: JSON.stringify({
            text,
            language: selectedLanguage()
          })
        });
        if (!response.ok) {
          const error = await response.text();
          throw new Error(error || `TTS failed with ${response.status}`);
        }
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        currentAudio = audio;
        audio.onended = () => {
          URL.revokeObjectURL(audioUrl);
          agentSpeaking = false;
          currentAudio = null;
          restartListeningAfterAgent();
        };
        audio.onerror = () => {
          URL.revokeObjectURL(audioUrl);
          agentSpeaking = false;
          currentAudio = null;
          setStatus("Audio playback failed.");
          restartListeningAfterAgent();
        };
        await audio.play();
      } catch (error) {
        console.error(error);
        setStatus("TTS error: " + error.message);
        agentSpeaking = false;
        restartListeningAfterAgent();
      }
    }
    function restartListeningAfterAgent() {
      if (callActive && liveMode.checked && recognition && !sending) {
        scheduleListeningRestart(350);
      }
    }
    function scheduleListeningRestart(delayMs = 250) {
      if (!callActive || !liveMode.checked || !recognition) return;
      setTimeout(() => {
        if (callActive && liveMode.checked && !agentSpeaking && !sending) {
          startListeningOnly();
        }
      }, delayMs);
    }
    function startListeningOnly() {
      if (!recognition || agentSpeaking || sending) return;
      recognition.lang = selectedLanguage();
      try {
        recognition.start();
      } catch (_error) {
        // Browser throws if recognition is already running. That is safe.
      }
    }
    function stopListeningOnly() {
      if (!recognition) return;
      try {
        recognition.stop();
      } catch (_error) {
        // Stop is best-effort; browser APIs vary.
      }
    }
    async function sendText(text) {
      const clean = text.trim();
      if (!clean || sending) return;
      if (!token.value.trim()) {
        setStatus("Paste VOICE_AGENT_API_TOKEN first.");
        return;
      }
      sending = true;
      addTurn("user", clean);
      setStatus("Thinking...");
      try {
        const response = await fetch("/calls/turn", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Voice-Agent-Token": token.value.trim()
          },
          body: JSON.stringify({
            organization_id: organizationId.value.trim() || "demo-org",
            caller_phone: callerPhone.value.trim() || "browser-user",
            text: clean,
            language: selectedLanguage()
          })
        });
        const data = await response.json();
        if (!response.ok) {
          setStatus(`Backend error ${response.status}: ${data.error || "unknown"}`);
          return;
        }
        addTurn("agent", data.reply);
        setStatus(`Agent replied. Intent: ${data.intent}; Status: ${data.status}; Ticket: ${data.ticket_id || "none"}`);
        speak(data.reply);
      } finally {
        sending = false;
        if (callActive && liveMode.checked && !agentSpeaking) {
          scheduleListeningRestart(300);
        }
      }
    }

    if (!SpeechRecognition) {
      startBtn.disabled = true;
      setStatus("Speech recognition is not available in this browser. Type text and click Send typed text.");
    } else {
      recognition = new SpeechRecognition();
      recognition.lang = selectedLanguage();
      recognition.interimResults = true;
      recognition.continuous = true;
      recognition.onstart = () => {
        startBtn.disabled = true;
        stopBtn.disabled = false;
        setStatus(agentSpeaking ? "Agent speaking..." : "Listening...");
      };
      recognition.onend = () => {
        if (callActive && liveMode.checked && !agentSpeaking && !sending) {
          setStatus("Listening paused; restarting...");
          scheduleListeningRestart(250);
          return;
        }
        startBtn.disabled = callActive;
        stopBtn.disabled = !callActive;
        if (!callActive) setStatus("Stopped.");
      };
      recognition.onerror = (event) => setStatus("Mic/STT error: " + event.error);
      recognition.onresult = (event) => {
        const text = Array.from(event.results)
          .slice(event.resultIndex)
          .map(result => result[0].transcript)
          .join(" ");
        transcript.value = text;
        const latest = event.results[event.results.length - 1];
        if (latest.isFinal) {
          const finalText = latest[0].transcript.trim();
          if (finalText && finalText !== lastFinalTranscript) {
            lastFinalTranscript = finalText;
            stopListeningOnly();
            sendText(finalText);
          }
        }
      };
    }

    startBtn.onclick = () => {
      callActive = true;
      lastFinalTranscript = "";
      setStatus("Starting live conversation...");
      startListeningOnly();
    };
    stopBtn.onclick = () => {
      callActive = false;
      if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
      }
      agentSpeaking = false;
      stopListeningOnly();
    };
    sendBtn.onclick = () => sendText(transcript.value);
    clearBtn.onclick = () => {
      transcript.value = "";
      turns.innerHTML = "";
      lastFinalTranscript = "";
      setStatus("Ready.");
    };
  </script>
</body>
</html>"""


def make_request_handler(router: JsonRouter):
    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._handle({})

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            self._handle(json.loads(body))

        def _handle(self, payload: dict) -> None:
            request_headers = {name: value for name, value in self.headers.items()}
            status, headers, body = router.handle_json(self.command, self.path, payload, request_headers)
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            if isinstance(body, bytes):
                self.wfile.write(body)
            else:
                self.wfile.write(body.encode("utf-8"))

        def log_message(self, format: str, *args) -> None:
            return

    return RequestHandler


def run(
    host: str | None = None,
    port: int | None = None,
    db_path: str | None = None,
) -> None:
    host = host or os.getenv("HOST", "0.0.0.0")
    port = port or int(os.getenv("PORT", "8088"))
    db_path = db_path or os.getenv("DATABASE_PATH", "data/voice_agent.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    service = PlatformService.local(store=SQLiteStore(Path(db_path)))
    router = create_handler(service, api_token=os.getenv("VOICE_AGENT_API_TOKEN"))
    server = ThreadingHTTPServer((host, port), make_request_handler(router))
    print(f"VoxDesk local API running on http://{host}:{port}")
    serve_until_stopped(server)


def serve_until_stopped(server: ThreadingHTTPServer, announce: bool = True) -> None:
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if announce:
            print("\nVoxDesk local API stopped")
    finally:
        server.server_close()
