/**
 * Type Definitions
 * Backend State와 동기화된 타입 정의
 */

// ExecutionStep types re-exported from types/execution
export type { ExecutionStep, StepStatus, StepType } from '@/types/execution'

// Alias for consistency with backend naming
export type ExecutionStepState = import('@/types/execution').ExecutionStep

// Session
export interface Session {
  session_id: string;
  created_at: string;
  expires_at: string;
}

// Chat Message (Frontend only)
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

// ExecutionPlan re-exported from types/execution
export type { ExecutionPlan } from '@/types/execution'

// Final Response
export interface FinalResponse {
  type: 'answer' | 'error' | 'clarification';
  content: string;
  data?: Record<string, any>;
}
