/**
 * React Hook for SARATHI HUD Chat & Streaming (Phase 2 with Interactive Approvals).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { ApprovalRequest, SarathiWsClient } from "./sarathi_ws_client";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  isStreaming?: boolean;
  name?: string;
}

export function useSarathiChat(sessionId = "default", wsUrl = "ws://127.0.0.1:8000/ws") {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<{ id: string; title: string; updated_at: string }[]>([]);
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected" | "reconnecting">("disconnected");
  const [isEmergencyStop, setIsEmergencyStop] = useState<boolean>(false);
  const [pendingApproval, setPendingApproval] = useState<ApprovalRequest | null>(null);
  const [error, setError] = useState<string | null>(null);

  const clientRef = useRef<SarathiWsClient | null>(null);

  const refreshSessions = useCallback(async () => {
    if (clientRef.current) {
      try {
        const res = await clientRef.current.listSessions();
        if (res && res.sessions) {
          setSessions(res.sessions);
        }
      } catch (e) {
        // Ignore error if disconnected
      }
    }
  }, []);

  useEffect(() => {
    const client = new SarathiWsClient({
      url: wsUrl,
      onDelta: (requestId, delta) => {
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.role === "assistant" && lastMsg.isStreaming) {
            return [
              ...prev.slice(0, -1),
              { ...lastMsg, content: lastMsg.content + delta },
            ];
          } else {
            return [
              ...prev,
              {
                id: requestId.toString(),
                role: "assistant",
                content: delta,
                isStreaming: true,
              },
            ];
          }
        });
      },
      onComplete: (requestId, content) => {
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.role === "assistant") {
            return [
              ...prev.slice(0, -1),
              { ...lastMsg, content, isStreaming: false },
            ];
          }
          return [
            ...prev,
            { id: requestId.toString(), role: "assistant", content, isStreaming: false },
          ];
        });
        refreshSessions();
      },
      onApprovalRequest: (request) => {
        console.info("[SARATHI HUD] Received approval request:", request);
        setPendingApproval(request);
      },
      onError: (_requestId, err) => {
        setError(`[${err.code}] ${err.message}`);
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.isStreaming) {
            return prev.slice(0, -1);
          }
          return prev;
        });
      },
      onStatusChange: (newStatus) => {
        setStatus(newStatus);
        if (newStatus === "connected") {
          setError(null);
          // Check emergency stop
          client.getEmergencyStopStatus().then((s) => {
            if (s) setIsEmergencyStop(s.active);
          }).catch(() => {});
          refreshSessions();
        }
      },
    });

    client.connect();
    clientRef.current = client;

    // Load initial messages for session
    client.loadSession(sessionId).then((res) => {
      if (res && res.messages) {
        const mapped: ChatMessage[] = res.messages.map((m: any, idx: number) => ({
          id: `history-${idx}`,
          role: m.role,
          content: m.content,
          name: m.name,
          isStreaming: false,
        }));
        setMessages(mapped);
      }
    }).catch(() => {});

    return () => {
      client.disconnect();
    };
  }, [sessionId, wsUrl, refreshSessions]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || !clientRef.current) return;
      setError(null);
      const reqId = Date.now().toString();

      setMessages((prev) => [
        ...prev,
        { id: `user-${reqId}`, role: "user", content: text },
        { id: `assistant-${reqId}`, role: "assistant", content: "", isStreaming: true },
      ]);

      try {
        await clientRef.current.sendChat(text, sessionId, reqId);
      } catch (err: any) {
        setError(err.message);
      }
    },
    [sessionId]
  );

  const respondApproval = useCallback(
    async (approvalId: string, approved: boolean) => {
      if (!clientRef.current) return;
      try {
        await clientRef.current.sendApprovalResponse(approvalId, approved);
      } catch (err: any) {
        console.warn("Failed to send approval response:", err);
      } finally {
        setPendingApproval(null);
      }
    },
    []
  );

  const triggerStop = useCallback(async () => {
    if (clientRef.current) {
      await clientRef.current.triggerEmergencyStop();
      setIsEmergencyStop(true);
      setPendingApproval(null);
    }
  }, []);

  const resetStop = useCallback(async () => {
    if (clientRef.current) {
      await clientRef.current.resetEmergencyStop();
      setIsEmergencyStop(false);
    }
  }, []);

  const switchSession = useCallback(async (newSessionId: string) => {
    if (!clientRef.current) return;
    try {
      const res = await clientRef.current.loadSession(newSessionId);
      if (res && res.messages) {
        setMessages(res.messages.map((m: any, idx: number) => ({
          id: `history-${idx}`,
          role: m.role,
          content: m.content,
          name: m.name,
          isStreaming: false,
        })));
      }
    } catch (e) {
      console.warn("Failed to load session:", e);
    }
  }, []);

  return {
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
  };
}
