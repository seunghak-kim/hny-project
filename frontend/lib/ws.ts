/**
 * WebSocket Client for Real-time Communication
 * Handles connection, reconnection, and message queuing
 */

import { ExecutionStepState } from './types';

// WebSocket Message Types (Server → Client)
export type WSMessageType =
  | 'connected'
  | 'planning_start'
  | 'plan_ready'
  | 'execution_start'
  | 'todo_created'
  | 'todo_updated'
  | 'step_start'
  | 'step_progress'
  | 'step_complete'
  | 'final_response'
  | 'error';

export interface WSMessage {
  type: WSMessageType;
  timestamp: string;
  [key: string]: any;
}

// WebSocket Message Types (Client → Server)
export interface WSQueryMessage {
  type: 'query';
  query: string;
  enable_checkpointing: boolean;
}

export interface WSInterruptResponseMessage {
  type: 'interrupt_response';
  action: 'approve' | 'modify';
  modified_todos?: ExecutionStepState[];
}

export interface WSTodoSkipMessage {
  type: 'todo_skip';
  todo_id: string;
}

export type WSClientMessage = WSQueryMessage | WSInterruptResponseMessage | WSTodoSkipMessage;

// WebSocket Client Configuration
export interface WSClientConfig {
  baseUrl: string; // e.g., "ws://localhost:8000"
  sessionId: string;
  onMessage: (message: WSMessage) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (error: Error) => void;
  reconnectInterval?: number; // milliseconds
  maxReconnectAttempts?: number;
}

// WebSocket Client State
type WSClientState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

/**
 * WebSocket Client Class
 */
export class ChatWSClient {
  private config: WSClientConfig;
  private ws: WebSocket | null = null;
  private state: WSClientState = 'disconnected';
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private messageQueue: WSClientMessage[] = [];

  constructor(config: WSClientConfig) {
    this.config = {
      reconnectInterval: 2000,
      maxReconnectAttempts: 5,
      ...config,
    };
  }

  /**
   * WebSocket 연결
   */
  connect(): void {
    if (this.state === 'connected' || this.state === 'connecting') {
      console.warn('[ChatWSClient] Already connected or connecting');
      return;
    }

    this.state = 'connecting';
    const wsUrl = `${this.config.baseUrl}/api/v1/chat/ws/${this.config.sessionId}`;

    console.log(`[ChatWSClient] Connecting to ${wsUrl}...`);

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[ChatWSClient] ✅ Connected');
        this.state = 'connected';
        this.reconnectAttempts = 0;

        // Flush queued messages
        this._flushMessageQueue();

        if (this.config.onConnected) {
          this.config.onConnected();
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          console.log(`[ChatWSClient] 📥 Received: ${message.type}`, message);
          this.config.onMessage(message);
        } catch (error) {
          console.error('[ChatWSClient] Failed to parse message:', error);
        }
      };

      this.ws.onerror = (event) => {
        console.error('[ChatWSClient] ❌ WebSocket error:', event);
        if (this.config.onError) {
          this.config.onError(new Error('WebSocket error'));
        }
      };

      this.ws.onclose = (event) => {
        console.log(`[ChatWSClient] Connection closed (code: ${event.code})`);
        this.state = 'disconnected';
        this.ws = null;

        if (this.config.onDisconnected) {
          this.config.onDisconnected();
        }

        // Reconnect if not intentionally closed
        if (event.code !== 1000 && event.code !== 1005) {
          this._attemptReconnect();
        }
      };
    } catch (error) {
      console.error('[ChatWSClient] Failed to create WebSocket:', error);
      this.state = 'disconnected';
      if (this.config.onError) {
        this.config.onError(error as Error);
      }
    }
  }

  /**
   * WebSocket 연결 해제
   */
  disconnect(): void {
    console.log('[ChatWSClient] Disconnecting...');

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.state = 'disconnected';
    this.reconnectAttempts = 0;
  }

  /**
   * 메시지 전송 (연결 없으면 큐잉)
   */
  send(message: WSClientMessage): void {
    if (this.state === 'connected' && this.ws) {
      try {
        this.ws.send(JSON.stringify(message));
        console.log(`[ChatWSClient] 📤 Sent: ${message.type}`, message);
      } catch (error) {
        console.error('[ChatWSClient] Failed to send message:', error);
        this.messageQueue.push(message);
      }
    } else {
      console.log(`[ChatWSClient] 📦 Queued: ${message.type} (state: ${this.state})`);
      this.messageQueue.push(message);
    }
  }

  /**
   * 연결 상태 확인
   */
  isConnected(): boolean {
    return this.state === 'connected';
  }

  /**
   * 현재 상태 반환
   */
  getState(): WSClientState {
    return this.state;
  }

  /**
   * 재연결 시도 (내부 메서드)
   */
  private _attemptReconnect(): void {
    if (this.reconnectAttempts >= (this.config.maxReconnectAttempts || 5)) {
      console.error('[ChatWSClient] Max reconnect attempts reached');
      if (this.config.onError) {
        this.config.onError(new Error('Max reconnect attempts reached'));
      }
      return;
    }

    this.reconnectAttempts++;
    this.state = 'reconnecting';

    const delay = this.config.reconnectInterval! * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
    console.log(`[ChatWSClient] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})...`);

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * 큐잉된 메시지 전송 (내부 메서드)
   */
  private _flushMessageQueue(): void {
    if (this.messageQueue.length === 0) return;

    console.log(`[ChatWSClient] 📨 Flushing ${this.messageQueue.length} queued messages`);

    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message) {
        this.send(message);
      }
    }
  }
}

/**
 * Singleton WebSocket Client Instance (Optional)
 */
let wsClientInstance: ChatWSClient | null = null;

export function createWSClient(config: WSClientConfig): ChatWSClient {
  if (wsClientInstance) {
    wsClientInstance.disconnect();
  }
  wsClientInstance = new ChatWSClient(config);
  return wsClientInstance;
}

export function getWSClient(): ChatWSClient | null {
  return wsClientInstance;
}
