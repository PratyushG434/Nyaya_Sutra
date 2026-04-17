export type Mode = 'citizen' | 'lawyer';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  attachments?: UploadedFile[];
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
  sources?: string[];
}
