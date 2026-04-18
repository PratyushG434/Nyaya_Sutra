import { useEffect, useRef, useState } from 'react';
import { Send, Trash2, Scale, BookOpen, Shield, MessageSquare, ChevronDown, ChevronUp, CheckCircle2 } from 'lucide-react';
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

// ── Markdown renderer (no external deps) ─────────────────────────────────────
function renderInline(text: string): React.ReactNode[] {
  // bold **text**, italic *text*, inline code `code`
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  let last = 0;
  let match;
  let key = 0;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    if (match[2]) parts.push(<strong key={key++} className="font-semibold text-paper-900">{match[2]}</strong>);
    else if (match[3]) parts.push(<em key={key++} className="italic text-paper-700">{match[3]}</em>);
    else if (match[4]) parts.push(<code key={key++} className="font-mono text-xs bg-paper-100 text-paper-800 px-1.5 py-0.5 rounded">{match[4]}</code>);
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

// ── Procedure Step Card ───────────────────────────────────────────────────────
function ProcedureSteps({ content }: { content: string }) {
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [expandedStep, setExpandedStep] = useState<number | null>(0);

  // Parse numbered steps from markdown: lines starting with "1.", "2.", etc.
  const lines = content.split('\n');
  const steps: { title: string; details: string[] }[] = [];
  let currentStep: { title: string; details: string[] } | null = null;

  for (const line of lines) {
    const stepMatch = line.match(/^(\d+)\.\s+(.+)/);
    if (stepMatch) {
      if (currentStep) steps.push(currentStep);
      currentStep = { title: stepMatch[2], details: [] };
    } else if (currentStep && line.trim()) {
      currentStep.details.push(line.trim().replace(/^[-•*]\s*/, ''));
    }
  }
  if (currentStep) steps.push(currentStep);

  // If no numbered steps found, fall back to plain markdown
  if (steps.length === 0) {
    return <MarkdownBlock content={content} />;
  }

  const toggleComplete = (i: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setCompletedSteps(prev => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  };

  const completedCount = completedSteps.size;
  const progress = Math.round((completedCount / steps.length) * 100);

  return (
    <div className="mt-3 space-y-3">
      {/* Progress bar */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 h-1.5 bg-paper-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-paper-700 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="text-[11px] font-bold uppercase tracking-widest text-paper-400 whitespace-nowrap">
          {completedCount}/{steps.length} done
        </span>
      </div>

      {steps.map((step, i) => {
        const isCompleted = completedSteps.has(i);
        const isExpanded = expandedStep === i;

        return (
          <div
            key={i}
            className={`
              rounded-xl border transition-all duration-300 overflow-hidden
              ${isCompleted
                ? 'border-paper-200 bg-paper-50 opacity-60'
                : isExpanded
                  ? 'border-paper-300 bg-white shadow-md'
                  : 'border-paper-200 bg-white hover:border-paper-300 hover:shadow-sm'
              }
            `}
          >
            {/* Step header */}
            <button
              onClick={() => setExpandedStep(isExpanded ? null : i)}
              className="w-full flex items-center gap-3 px-4 py-3 text-left"
            >
              {/* Step number / check */}
              <button
                onClick={(e) => toggleComplete(i, e)}
                className={`
                  flex-shrink-0 w-7 h-7 rounded-full border-2 flex items-center justify-center transition-all duration-200
                  ${isCompleted
                    ? 'border-paper-600 bg-paper-700 text-white'
                    : 'border-paper-300 hover:border-paper-600'
                  }
                `}
                title={isCompleted ? 'Mark incomplete' : 'Mark complete'}
              >
                {isCompleted
                  ? <CheckCircle2 size={14} />
                  : <span className="text-[11px] font-bold text-paper-500">{i + 1}</span>
                }
              </button>

              <span className={`flex-1 text-sm font-semibold leading-snug ${isCompleted ? 'line-through text-paper-400' : 'text-paper-800'}`}>
                {renderInline(step.title)}
              </span>

              {step.details.length > 0 && (
                <span className="text-paper-400 flex-shrink-0">
                  {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </span>
              )}
            </button>

            {/* Step details */}
            {isExpanded && step.details.length > 0 && (
              <div className="px-4 pb-4 pt-1 border-t border-paper-100">
                <ul className="space-y-2 mt-2">
                  {step.details.map((detail, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm text-paper-600 leading-relaxed">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-paper-300 flex-shrink-0" />
                      {renderInline(detail)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Generic Markdown Block ────────────────────────────────────────────────────
function MarkdownBlock({ content }: { content: string }) {
  const lines = content.split('\n');
  const nodes: React.ReactNode[] = [];
  let key = 0;
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // H2 heading
    if (line.startsWith('## ')) {
      nodes.push(
        <h2 key={key++} className="font-serif text-lg text-paper-900 mt-5 mb-2 leading-snug">
          {renderInline(line.slice(3))}
        </h2>
      );
    }
    // H3 heading
    else if (line.startsWith('### ')) {
      nodes.push(
        <h3 key={key++} className="font-semibold text-sm text-paper-800 mt-4 mb-1 uppercase tracking-wider">
          {renderInline(line.slice(4))}
        </h3>
      );
    }
    // Horizontal rule
    else if (line.trim() === '---') {
      nodes.push(<hr key={key++} className="border-paper-200 my-5" />);
    }
    // Bullet list item
    else if (/^[-•*]\s+/.test(line)) {
      const items: React.ReactNode[] = [];
      while (i < lines.length && /^[-•*]\s+/.test(lines[i])) {
        items.push(
          <li key={i} className="flex items-start gap-2 text-sm text-paper-700 leading-relaxed">
            <span className="mt-2 w-1.5 h-1.5 rounded-full bg-paper-400 flex-shrink-0" />
            <span>{renderInline(lines[i].replace(/^[-•*]\s+/, ''))}</span>
          </li>
        );
        i++;
      }
      nodes.push(<ul key={key++} className="space-y-1.5 my-2">{items}</ul>);
      continue;
    }
    // Numbered list item (but NOT procedure — handled separately)
    else if (/^\d+\.\s+/.test(line)) {
      const items: React.ReactNode[] = [];
      let num = 1;
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        items.push(
          <li key={i} className="flex items-start gap-3 text-sm text-paper-700 leading-relaxed">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-paper-100 text-paper-500 text-[10px] font-bold flex items-center justify-center mt-0.5">{num}</span>
            <span>{renderInline(lines[i].replace(/^\d+\.\s+/, ''))}</span>
          </li>
        );
        num++;
        i++;
      }
      nodes.push(<ol key={key++} className="space-y-2 my-2">{items}</ol>);
      continue;
    }
    // Blockquote
    else if (line.startsWith('> ')) {
      nodes.push(
        <blockquote key={key++} className="border-l-2 border-paper-300 pl-4 py-1 my-2 text-sm italic text-paper-600">
          {renderInline(line.slice(2))}
        </blockquote>
      );
    }
    // Non-empty paragraph
    else if (line.trim()) {
      nodes.push(
        <p key={key++} className="text-sm text-paper-700 leading-relaxed my-1">
          {renderInline(line)}
        </p>
      );
    }

    i++;
  }

  return <div className="space-y-1">{nodes}</div>;
}

// ── Section badge ─────────────────────────────────────────────────────────────
const SECTION_META: Record<string, { icon: string; label: string; accent: string }> = {
  legal_advice: { icon: '⚖️', label: 'Legal Advice',     accent: 'border-amber-200 bg-amber-50' },
  procedure:    { icon: '📋', label: 'Step-by-Step Procedure', accent: 'border-blue-100 bg-blue-50' },
  query:        { icon: '💬', label: 'Legal Information', accent: 'border-green-100 bg-green-50' },
};

// ── Parse multi-section response ──────────────────────────────────────────────
function parseResponse(reply: string, agents: string[]) {
  if (!agents || agents.length <= 1) {
    return [{ key: agents?.[0] ?? 'general', content: reply }];
  }

  // Split on markdown H2 section dividers
  const sections: { key: string; content: string }[] = [];
  const parts = reply.split(/\n---\n/);

  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;

    // Detect which agent this section belongs to
    let key = 'general';
    if (/##.*legal advice/i.test(trimmed))     key = 'legal_advice';
    else if (/##.*procedure/i.test(trimmed))   key = 'procedure';
    else if (/##.*legal information/i.test(trimmed)) key = 'query';
    else if (agents.length === 1)              key = agents[0];

    // Strip the H2 header line from content (we render it as a badge)
    const content = trimmed.replace(/^##\s+[^\n]+\n/, '').trim();
    sections.push({ key, content });
  }

  return sections.length > 0 ? sections : [{ key: 'general', content: reply }];
}

// ── Formatted bot response ────────────────────────────────────────────────────
export function FormattedResponse({
  reply,
  type,
  agents,
}: {
  reply: string;
  type: string;
  agents?: string[];
}) {
  const sections = parseResponse(reply, agents ?? []);
  const isMulti = sections.length > 1;

  // Fallback — plain styled text
  if (type === 'fallback') {
    return (
      <div className="text-sm text-paper-700 leading-relaxed whitespace-pre-line">
        {reply}
      </div>
    );
  }

  return (
    <div className={`space-y-5 ${isMulti ? 'mt-1' : ''}`}>
      {sections.map((section, idx) => {
        const meta = SECTION_META[section.key];
        const isProcedure = section.key === 'procedure';

        return (
          <div key={idx}>
            {/* Section badge (only for multi-agent responses) */}
            {isMulti && meta && (
              <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[11px] font-bold uppercase tracking-widest mb-3 ${meta.accent}`}>
                <span>{meta.icon}</span>
                <span className="text-paper-600">{meta.label}</span>
              </div>
            )}

            {/* Content */}
            {isProcedure
              ? <ProcedureSteps content={section.content} />
              : <MarkdownBlock content={section.content} />
            }
          </div>
        );
      })}
    </div>
  );
}

// ── Agent chips shown under message ──────────────────────────────────────────
function AgentChips({ agents }: { agents: string[] }) {
  if (!agents || agents.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-3">
      {agents.map(a => {
        const meta = SECTION_META[a];
        if (!meta) return null;
        return (
          <span key={a} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-semibold uppercase tracking-wider ${meta.accent} text-paper-500`}>
            {meta.icon} {meta.label}
          </span>
        );
      })}
    </div>
  );
}

// ── Main ChatInterface ────────────────────────────────────────────────────────
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
            {messages.map((message) => {
              // For bot messages with structured data, use FormattedResponse
              // AFTER — use top-level fields directly
              if (message.role === 'assistant' && message.type) {
                return (
                  <div key={message.id} className="flex flex-col max-w-3xl">
                    <div className="rounded-2xl bg-white border border-paper-200 shadow-sm px-6 py-5">
                      <FormattedResponse
                        reply={message.content}
                        type={message.type}
                        agents={message.agents}
                      />
                    </div>
                    {message.agents && message.agents.length > 1 && (
                      <AgentChips agents={message.agents} />
                    )}
                  </div>
                );
              }
              // User messages and plain bot messages
              return <MessageBubble key={message.id} message={message} mode={mode} />;
            })}
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