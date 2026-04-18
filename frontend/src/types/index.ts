export type Mode = 'citizen' | 'lawyer';

export interface TimelineStep {
  step: number;
  title: string;
  status: 'done' | 'current' | 'upcoming';
}

export interface AuditResults {
  statutes: string[];
  precedents: string[];
  warnings: string[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  attachments?: UploadedFile[];
  // Backend response fields
  type?: string;
  agents?: string[];
  route?: string;
  used_file?: boolean;
  // Legacy fields (for future use)
  timeline?: TimelineStep[];
  audit_results?: AuditResults;
}

export interface UploadedFile {
  name: string;
  size: number;
  type: string;
  url?: string;
}

export interface ChatRequest {
  message: string;
  mode: Mode;
  history: { role: string; content: string }[];
  files?: string[];
}

// Citizen mode response
export interface CitizenChatResponse {
  reply: string;
  type: string;
  agents: string[];
}

// Lawyer mode response
export interface LawyerChatResponse {
  reply: string;
  type: string;
  route: string;
  used_file?: boolean;
}

export type ChatResponse = CitizenChatResponse | LawyerChatResponse;
