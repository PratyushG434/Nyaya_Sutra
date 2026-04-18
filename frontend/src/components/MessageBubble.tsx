import { Message, Mode } from '../types';
import { User, Scale, FileText, ShieldAlert, BookOpenCheck, Gavel } from 'lucide-react';
import { Timeline } from './Timeline';

interface MessageBubbleProps {
  message: Message;
  mode: Mode;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isAssistant = message.role === 'assistant';

  return (
    <div className={`flex w-full ${isAssistant ? 'justify-start' : 'justify-end'}`}>
      <div className={`flex gap-4 max-w-[90%] md:max-w-[80%] ${isAssistant ? 'flex-row' : 'flex-row-reverse'}`}>
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border shadow-sm mt-1 ${
          isAssistant 
            ? 'bg-paper-100 border-paper-200 text-paper-800' 
            : 'bg-paper-800 border-paper-900 text-white'
        }`}>
          {isAssistant ? <Scale size={16} /> : <User size={16} />}
        </div>
        
        <div className="flex flex-col gap-2 flex-1 min-w-0">
          <div className={`px-6 py-4 rounded-2xl shadow-sm border overflow-hidden ${
            isAssistant 
              ? 'bg-white border-paper-200 text-paper-900 font-serif-clean leading-relaxed' 
              : 'bg-paper-100 border-paper-200 text-paper-800 font-sans'
          }`}>
            <p className="whitespace-pre-wrap text-[15px]">{message.content}</p>
            
            {/* Timeline / Flowchart */}
            {message.timeline && (
              <Timeline steps={message.timeline} />
            )}

            {/* Audit Results (Lawyer Mode) */}
            {message.audit_results && (
              <div className="mt-6 space-y-4 border-t border-paper-100 pt-6">
                <div className="flex items-center gap-2 mb-2">
                  <Gavel size={14} className="text-paper-400" />
                  <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-paper-400">Legal Audit Summary</span>
                </div>
                
                {message.audit_results.statutes.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {message.audit_results.statutes.map((s, i) => (
                      <span key={i} className="flex items-center gap-1.5 px-3 py-1 bg-paper-50 border border-paper-200 rounded-full text-[11px] font-medium text-paper-700">
                        <BookOpenCheck size={10} className="text-paper-400" />
                        {s}
                      </span>
                    ))}
                  </div>
                )}

                {message.audit_results.warnings.length > 0 && (
                  <div className="space-y-2">
                    {message.audit_results.warnings.map((w, i) => (
                      <div key={i} className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-100 rounded-xl text-xs text-amber-800">
                        <ShieldAlert size={14} className="flex-shrink-0 mt-0.5 text-amber-500" />
                        <p className="font-medium">{w}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {message.attachments && message.attachments.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2 pt-4 border-t border-paper-100">
                {message.attachments.map((file, i) => (
                  <div 
                    key={i}
                    className="flex items-center gap-2 px-3 py-1.5 bg-paper-50 border border-paper-200 rounded-lg text-xs text-paper-700"
                  >
                    <FileText size={12} className="text-paper-400" />
                    <span className="font-medium">{file.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <span className={`text-[10px] font-bold uppercase tracking-widest text-paper-300 px-2 ${isAssistant ? 'text-left' : 'text-right'}`}>
            {isAssistant ? 'Nyaya-Saathi' : 'You'}
          </span>
        </div>
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex gap-4 max-w-[85%] items-start">
        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border border-paper-200 bg-paper-100 text-paper-800 shadow-sm">
          <Scale size={16} />
        </div>
        <div className="px-6 py-4 rounded-2xl bg-white border border-paper-200 shadow-sm">
          <div className="flex gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-paper-200 animate-bounce [animation-delay:-0.3s]" />
            <div className="w-1.5 h-1.5 rounded-full bg-paper-200 animate-bounce [animation-delay:-0.15s]" />
            <div className="w-1.5 h-1.5 rounded-full bg-paper-200 animate-bounce" />
          </div>
        </div>
      </div>
    </div>
  );
}
