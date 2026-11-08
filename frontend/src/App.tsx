import React, { useState, useRef, useEffect } from "react";
import { useSarathiChat } from "./useSarathiChat";
import { WelcomeScreen } from "./WelcomeScreen";
import "./styles.css";

export function App() {
  const [showWelcome, setShowWelcome] = useState<boolean>(true);
  const [currentSession, setCurrentSession] = useState("default");
  const [inputVal, setInputVal] = useState("");
  const [isPushToTalkActive, setIsPushToTalkActive] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  const {
    messages,
    sendMessage,
    status,
    sessions,
    isEmergencyStop,
    pendingApproval,
    respondApproval,
    triggerStop,
    resetStop,
    switchSession,
    error,
  } = useSarathiChat(currentSession);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!inputVal.trim()) return;
    sendMessage(inputVal);
    setInputVal("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSend();
    }
  };

  const handleNewSession = () => {
    const newId = `session-${Date.now().toString(36)}`;
    setCurrentSession(newId);
    switchSession(newId);
  };

  return (
    <div className="hud-container">
      {/* Reference-Matched Welcome Screen */}
      {showWelcome && (
        <WelcomeScreen
          onEnter={() => setShowWelcome(false)}
          autoTransitionDelay={3800}
        />
      )}

      {/* Interactive Tool Approval Modal */}
      {pendingApproval && (
        <div className="modal-overlay">
          <div className="approval-card">
            <div>
              <span className="approval-badge">
                {pendingApproval.permission_level} // APPROVAL REQUIRED
              </span>
              <h2 className="approval-title">Execute Tool: {pendingApproval.tool}</h2>
            </div>

            <div className="approval-desc">
              {pendingApproval.description}
            </div>

            <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>
              Proposed Arguments:
            </div>
            <div className="approval-args">
              {JSON.stringify(pendingApproval.arguments, null, 2)}
            </div>

            <div className="approval-actions">
              <button
                className="btn-deny"
                onClick={() => respondApproval(pendingApproval.approval_id, false)}
              >
                DENY & ABORT
              </button>
              <button
                className="btn-approve"
                onClick={() => respondApproval(pendingApproval.approval_id, true)}
              >
                APPROVE & EXECUTE
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sidebar */}
      <aside className="hud-sidebar">
        <div
          className="sidebar-header"
          onClick={() => setShowWelcome(true)}
          style={{ cursor: "pointer" }}
          title="Click to view Welcome Screen"
        >
          <div className="logo-tag">YOUR AI COMPANION</div>
          <h1 className="app-title" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ color: "#00c8c8", fontSize: "16px" }}>✦</span> SARATHI
          </h1>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
            Guiding Your Ideas Forward
          </div>
        </div>

        <div style={{ padding: "12px" }}>
          <button
            onClick={handleNewSession}
            style={{
              width: "100%",
              padding: "10px",
              background: "rgba(0, 240, 255, 0.12)",
              border: "1px solid rgba(0, 240, 255, 0.4)",
              color: "#00f0ff",
              borderRadius: "6px",
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "13px",
            }}
          >
            + NEW SESSION
          </button>
        </div>

        <div className="session-list">
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "8px", textTransform: "uppercase" }}>
            Active Sessions
          </div>
          <div
            className={`session-item ${currentSession === "default" ? "active" : ""}`}
            onClick={() => {
              setCurrentSession("default");
              switchSession("default");
            }}
          >
            default (Active Core)
          </div>
          {sessions
            .filter((s) => s.id !== "default")
            .map((s) => (
              <div
                key={s.id}
                className={`session-item ${currentSession === s.id ? "active" : ""}`}
                onClick={() => {
                  setCurrentSession(s.id);
                  switchSession(s.id);
                }}
              >
                {s.title || s.id}
              </div>
            ))}
        </div>
      </aside>

      {/* Main Area */}
      <main className="hud-main">
        {/* Top Header */}
        <header className="hud-topbar">
          <div className="system-status">
            <span
              className={`status-pill ${
                status === "connected"
                  ? "status-connected"
                  : status === "reconnecting"
                  ? "status-reconnecting"
                  : "status-disconnected"
              }`}
            >
              <span className="pulse-dot" />
              {status === "connected"
                ? "DAEMON ONLINE (127.0.0.1:8000)"
                : status === "reconnecting"
                ? "RECONNECTING DAEMON..."
                : "DAEMON OFFLINE"}
            </span>

            <span style={{ fontSize: "12px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              SESSION: {currentSession}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button
              onClick={() => setShowWelcome(true)}
              style={{
                background: "rgba(0, 200, 200, 0.1)",
                border: "1px solid rgba(0, 200, 200, 0.3)",
                color: "#00c8c8",
                padding: "6px 12px",
                borderRadius: "4px",
                fontSize: "11px",
                fontWeight: 600,
                letterSpacing: "1px",
                cursor: "pointer",
              }}
              title="View Welcome Screen"
            >
              ✦ WELCOME
            </button>
            {isEmergencyStop ? (
              <button className="e-stop-btn e-stop-active-btn" onClick={resetStop}>
                STOP ACTIVE // CLICK TO RESET
              </button>
            ) : (
              <button className="e-stop-btn" onClick={triggerStop}>
                CIRCUIT STOP
              </button>
            )}
          </div>
        </header>

        {/* Error Notification Banner */}
        {error && (
          <div className="alert-bar">
            <strong>Warning:</strong> {error}
          </div>
        )}

        {/* Chat Stream Viewport */}
        <div className="chat-viewport">
          {messages.length === 0 && (
            <div style={{ textAlign: "center", color: "var(--text-muted)", marginTop: "40px" }}>
              <div style={{ fontSize: "18px", color: "var(--accent-cyan)", marginBottom: "8px" }}>
                SARATHI Core Ready
              </div>
              <div style={{ fontSize: "13px" }}>
                WebSocket connected. Ready for text conversation, local tool execution, or voice push-to-talk.
              </div>
            </div>
          )}

          {messages.map((m) => (
            <div
              key={m.id}
              className={`msg-row ${
                m.role === "user"
                  ? "msg-user"
                  : m.role === "tool"
                  ? "msg-tool"
                  : "msg-assistant"
              }`}
            >
              <div style={{ fontSize: "10px", color: "var(--text-muted)", marginBottom: "4px", textTransform: "uppercase" }}>
                {m.role === "tool" ? `TOOL [${m.name || "executed"}]` : m.role}
              </div>
              <div className="msg-bubble">
                {m.content}
                {m.isStreaming && <span className="cursor-blink" />}
              </div>
            </div>
          ))}
          <div ref={chatBottomRef} />
        </div>

        {/* Footer Control Bar */}
        <footer className="hud-footer">
          <input
            className="chat-input"
            type="text"
            placeholder={
              isEmergencyStop
                ? "Emergency Stop is active. Reset to resume operations."
                : "Enter command or message for SARATHI..."
            }
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isEmergencyStop}
          />

          <button
            className="action-btn"
            onClick={handleSend}
            disabled={isEmergencyStop || !inputVal.trim()}
          >
            TRANSMIT
          </button>

          <button
            className={`ptt-btn ${isPushToTalkActive ? "active" : ""}`}
            onMouseDown={() => setIsPushToTalkActive(true)}
            onMouseUp={() => setIsPushToTalkActive(false)}
            onMouseLeave={() => setIsPushToTalkActive(false)}
            title="Push-to-Talk (Hold to speak)"
            disabled={isEmergencyStop}
          >
            {isPushToTalkActive ? "LISTENING..." : "PTT MIC"}
          </button>
        </footer>
      </main>
    </div>
  );
}

export default App;
