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

export interface ChatResponse {
  reply: string;
  timeline?: TimelineStep[];
  audit_results?: AuditResults;
  sources?: string[];
}
