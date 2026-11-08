/**
 * SARATHI HUD WebSocket & JSON-RPC 2.0 Client.
 */

export interface ApprovalRequest {
  approval_id: string;
  tool: string;
  description: string;
  arguments: Record<string, any>;
  permission_level: "T0" | "T1" | "T2" | "T3" | string;
}

export interface RpcMessage {
  jsonrpc: "2.0";
  id?: string | number | null;
  method?: string;
  params?: any;
  result?: {
    session_id?: string;
    content?: string;
    reply?: string;
    done?: boolean;
    [key: string]: any;
  };
  error?: {
    code: number;
    message: string;
    data?: any;
  };
}

export interface SarathiClientOptions {
  url?: string;
  maxReconnectAttempts?: number;
  initialReconnectDelayMs?: number;
  maxReconnectDelayMs?: number;
  requestTimeoutMs?: number;
  onDelta?: (requestId: string | number, delta: string) => void;
  onComplete?: (requestId: string | number, content: string, sessionId: string) => void;
  onError?: (requestId: string | number | null, error: { code: number; message: string }) => void;
  onStatusChange?: (status: "connecting" | "connected" | "disconnected" | "reconnecting") => void;
  onEmergencyStop?: (active: boolean) => void;
  onApprovalRequest?: (request: ApprovalRequest) => void;
}

export class SarathiWsClient {
  private url: string;
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts: number;
  private initialReconnectDelayMs: number;
  private maxReconnectDelayMs: number;
  private requestTimeoutMs: number;
  private pendingRequests = new Map<
    string | number,
    {
      resolve: (val: any) => void;
      reject: (err: any) => void;
      timer: ReturnType<typeof setTimeout> | number;
    }
  >();
  private isExplicitClose = false;
  private options: SarathiClientOptions;

  constructor(options: SarathiClientOptions = {}) {
    this.options = options;
    this.url = options.url || "ws://127.0.0.1:8000/ws";
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 10;
    this.initialReconnectDelayMs = options.initialReconnectDelayMs ?? 1000;
    this.maxReconnectDelayMs = options.maxReconnectDelayMs ?? 15000;
    this.requestTimeoutMs = options.requestTimeoutMs ?? 60000;
  }

  public connect(): void {
    this.isExplicitClose = false;
    this.options.onStatusChange?.("connecting");

    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        this.reconnectAttempts = 0;
        this.options.onStatusChange?.("connected");
        console.info("[SARATHI] WebSocket connected to", this.url);
      };

      this.socket.onmessage = (event: MessageEvent<string>) => {
        try {
          const message: RpcMessage = JSON.parse(event.data);
          this.handleIncomingMessage(message);
        } catch (e) {
          console.error("[SARATHI] Malformed incoming message:", event.data);
        }
      };

      this.socket.onclose = () => {
        this.options.onStatusChange?.("disconnected");
        this.cleanupPending(new Error("Connection closed"));
        if (!this.isExplicitClose) {
          this.scheduleReconnect();
        }
      };

      this.socket.onerror = (err) => {
        console.warn("[SARATHI] WebSocket error:", err);
      };
    } catch (err) {
      this.scheduleReconnect();
    }
  }

  private handleIncomingMessage(msg: RpcMessage): void {
    if (msg.method === "chat.delta" && msg.params) {
      const reqId = msg.params.id;
      const text = msg.params.text || "";
      this.options.onDelta?.(reqId, text);
      return;
    }

    if (msg.method === "chat.approval_request" && msg.params) {
      this.options.onApprovalRequest?.(msg.params as ApprovalRequest);
      return;
    }

    if (msg.id != null) {
      const pending = this.pendingRequests.get(msg.id);
      if (pending) {
        clearTimeout(pending.timer as any);
        this.pendingRequests.delete(msg.id);

        if (msg.error) {
          this.options.onError?.(msg.id, msg.error);
          pending.reject(new Error(`[${msg.error.code}] ${msg.error.message}`));
        } else if (msg.result) {
          if (msg.result.done && msg.result.content != null) {
            this.options.onComplete?.(
              msg.id,
              msg.result.content,
              msg.result.session_id || "default"
            );
          }
          pending.resolve(msg.result);
        }
      }
    } else if (msg.error) {
      this.options.onError?.(null, msg.error);
    }
  }

  public sendChat(
    text: string,
    sessionId = "default",
    requestId: string | number = Date.now().toString()
  ): Promise<any> {
    return this.call("chat.send", {
      session_id: sessionId,
      message: text,
    }, requestId);
  }

  public sendApprovalResponse(approvalId: string, approved: boolean): Promise<any> {
    return this.call("chat.approval_response", {
      approval_id: approvalId,
      approved,
    });
  }

  public triggerEmergencyStop(): Promise<any> {
    return this.call("emergency_stop.trigger", {});
  }

  public resetEmergencyStop(): Promise<any> {
    return this.call("emergency_stop.reset", {});
  }

  public getEmergencyStopStatus(): Promise<{ active: boolean }> {
    return this.call("emergency_stop.status", {});
  }

  public listSessions(): Promise<any> {
    return this.call("sessions.list", {});
  }

  public loadSession(sessionId: string): Promise<any> {
    return this.call("session.load", { session_id: sessionId });
  }

  public call(method: string, params: any, id: string | number = Date.now().toString()): Promise<any> {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return Promise.reject(new Error("SARATHI WebSocket is not connected"));
    }

    const payload: RpcMessage = {
      jsonrpc: "2.0",
      id,
      method,
      params,
    };

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`SARATHI RPC call timed out for method: ${method}`));
      }, this.requestTimeoutMs);

      this.pendingRequests.set(id, { resolve, reject, timer });
      this.socket!.send(JSON.stringify(payload));
    });
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("[SARATHI] Max reconnection attempts reached.");
      return;
    }

    this.options.onStatusChange?.("reconnecting");
    const delay = Math.min(
      this.initialReconnectDelayMs * Math.pow(1.5, this.reconnectAttempts) + Math.random() * 500,
      this.maxReconnectDelayMs
    );

    this.reconnectAttempts++;
    setTimeout(() => {
      if (!this.isExplicitClose) {
        this.connect();
      }
    }, delay);
  }

  private cleanupPending(error: Error): void {
    for (const [id, req] of this.pendingRequests.entries()) {
      clearTimeout(req.timer as any);
      req.reject(error);
    }
    this.pendingRequests.clear();
  }

  public disconnect(): void {
    this.isExplicitClose = true;
    this.cleanupPending(new Error("Client disconnected"));
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}
