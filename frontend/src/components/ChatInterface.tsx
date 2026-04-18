import { useEffect, useRef, useState } from 'react';
import { Send, Trash2, Scale, BookOpen, Shield, MessageSquare } from 'lucide-react';
import { Mode, UploadedFile } from '../types';
import { useChat } from '../hooks/useChat';
import { ModeSelector } from './ModeSelector';
import { MessageBubble, TypingIndicator } from './MessageBubble';
import { FileUpload } from './FileUpload';
import { VoiceInput } from './VoiceInput';

const CITIZEN_SUGGESTIONS = [
  'What are my rights if I am arrested?',
  'How do I file a consumer complaint?',
  'What is the process for getting bail?',
  'How can I apply for legal aid?',
];

const LAWYER_SUGGESTIONS = [
  'Summarize the latest Supreme Court judgements on Article 21',
  'Draft a notice under Section 138 NI Act',
  'What are the grounds for anticipatory bail?',
  'Explain the Vishakha Guidelines',
];

export function ChatInterface() {
  const [mode, setMode] = useState<Mode>('citizen');
  const [input, setInput] = useState('');
  const [pendingFiles, setPendingFiles] = useState<UploadedFile[]>([]);
  const { messages, isLoading, error, sendMessage, uploadFile, clearChat } = useChat(mode);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() && pendingFiles.length === 0) return;
    const files = pendingFiles.length > 0 ? pendingFiles : undefined;
    const text = input.trim();
    setInput('');
    setPendingFiles([]);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    await sendMessage(text, files);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleModeChange = (newMode: Mode) => {
    setMode(newMode);
  };

  const suggestions = mode === 'citizen' ? CITIZEN_SUGGESTIONS : LAWYER_SUGGESTIONS;
  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-screen bg-paper-50 font-sans">
      <header className="flex-shrink-0 flex items-center justify-between px-8 py-6 border-b border-paper-200 bg-paper-50/90 backdrop-blur-md z-10">
        <div className="flex items-center gap-4">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-paper-100 border border-paper-200 shadow-sm">
            <Scale size={24} className="text-paper-800" />
          </div>
          <div>
            <h1 className="text-paper-900 font-serif text-2xl tracking-tight leading-none">
              Nyaya-Saathi
            </h1>
            <p className="text-paper-700 text-xs mt-1 font-medium uppercase tracking-wider">
              {mode === 'citizen' ? 'Legal Companion' : 'Research Assistant'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <ModeSelector mode={mode} onChange={handleModeChange} />
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="flex items-center justify-center w-10 h-10 rounded-full text-paper-700 hover:text-red-600 hover:bg-red-50 transition-all duration-300"
              title="Clear conversation"
            >
              <Trash2 size={18} />
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-10 space-y-8 scrollbar-thin max-w-4xl mx-auto w-full">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4 gap-12 pb-20">
            <div className="space-y-6">
              <h2 className="text-4xl font-serif text-paper-900 leading-tight">
                How can I assist your <br /> <span className="italic text-paper-700">legal journey</span> today?
              </h2>
              <p className="text-paper-700 max-w-lg mx-auto text-lg font-light leading-relaxed">
                {mode === 'citizen'
                  ? 'Seek clarity on your rights and legal procedures in plain, accessible language.'
                  : 'Delve into statutory interpretations, case law summaries, and drafting support.'}
              </p>
            </div>

            <div className="w-full max-w-2xl">
              <div className="flex items-center gap-2 mb-6 justify-center">
                <div className="h-px bg-paper-200 flex-1"></div>
                <p className="text-[10px] uppercase tracking-[0.2em] text-paper-300 font-bold">
                  Suggested Inquiries
                </p>
                <div className="h-px bg-paper-200 flex-1"></div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(s)}
                    className="text-left px-6 py-4 rounded-xl border border-paper-200 bg-white hover:bg-paper-100 hover:border-paper-300 transition-all duration-300 group shadow-sm hover:shadow-md"
                  >
                    <div className="flex items-start gap-3">
                      <MessageSquare
                        size={16}
                        className="flex-shrink-0 mt-1 text-paper-300 group-hover:text-paper-700 transition-colors"
                      />
                      <span className="text-sm text-paper-800 font-medium">{s}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap justify-center items-center gap-8 text-[11px] font-bold uppercase tracking-widest text-paper-300">
              <div className="flex items-center gap-2">
                <Shield size={14} className="text-paper-300" />
                <span>Private & Confidential</span>
              </div>
              <div className="flex items-center gap-2">
                <BookOpen size={14} className="text-paper-300" />
                <span>Bharatiya Nyaya Sanhita</span>
              </div>
              <div className="flex items-center gap-2 underline underline-offset-4 decoration-paper-200">
                <Scale size={14} className="text-paper-300" />
                <span>Non-Advisory</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} mode={mode} />
            ))}
            {isLoading && <TypingIndicator />}
            {error && (
              <div className="flex justify-center py-4">
                <div className="flex items-center gap-3 px-5 py-3 bg-red-50 border border-red-100 rounded-2xl text-sm text-red-600 shadow-sm">
                  <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  {error}
                </div>
              </div>
            )}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="flex-shrink-0 px-6 pb-8 max-w-4xl mx-auto w-full">
        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-b from-paper-200 to-paper-100 rounded-3xl blur opacity-20 group-hover:opacity-40 transition duration-1000 group-hover:duration-200"></div>
          <div className="relative flex flex-col p-2 rounded-2xl border border-paper-200 bg-white shadow-xl transition-all duration-300">
            <div className="flex items-end gap-2 px-2 py-2">
              <div className="flex items-center gap-1">
                <FileUpload
                  files={pendingFiles}
                  onFilesChange={setPendingFiles}
                  onUpload={uploadFile}
                />
                <VoiceInput onTranscript={(text) => setInput(prev => prev + (prev ? ' ' : '') + text)} />
              </div>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  mode === 'citizen'
                    ? 'Inquire about your legal rights...'
                    : 'Draft legal documents or research statutes...'
                }
                rows={1}
                className="flex-1 bg-transparent text-paper-900 placeholder-paper-300 resize-none outline-none leading-relaxed py-2 max-h-[120px] overflow-y-auto scrollbar-thin text-[15px]"
              />
              <button
                onClick={handleSend}
                disabled={isLoading || (!input.trim() && pendingFiles.length === 0)}
                className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-300 disabled:opacity-20 disabled:grayscale bg-paper-800 hover:bg-paper-900 shadow-lg shadow-paper-200 text-white"
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
        <p className="text-center text-[10px] text-paper-300 mt-4 uppercase tracking-[0.2em] font-bold">
          Nyaya-Saathi: A legal information system. Not a substitute for legal counsel.
        </p>
      </div>
    </div>
  );
}
