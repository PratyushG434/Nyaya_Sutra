import { Mode } from '../types';
import { User, Scale, FileText } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  files?: { name: string; type: string; size: number }[];
}

interface MessageBubbleProps {
  message: Message;
  mode: Mode;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isAssistant = message.role === 'assistant';

  return (
    <div className={`flex w-full ${isAssistant ? 'justify-start' : 'justify-end'}`}>
      <div className={`flex gap-4 max-w-[85%] ${isAssistant ? 'flex-row' : 'flex-row-reverse'}`}>
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border shadow-sm ${
          isAssistant 
            ? 'bg-paper-100 border-paper-200 text-paper-800' 
            : 'bg-paper-800 border-paper-900 text-white'
        }`}>
          {isAssistant ? <Scale size={16} /> : <User size={16} />}
        </div>
        
        <div className="flex flex-col gap-2">
          <div className={`px-6 py-4 rounded-2xl shadow-sm border ${
            isAssistant 
              ? 'bg-white border-paper-200 text-paper-900 font-serif-clean leading-relaxed' 
              : 'bg-paper-100 border-paper-200 text-paper-800 font-sans'
          }`}>
            <p className="whitespace-pre-wrap text-[15px]">{message.content}</p>
            
            {message.files && message.files.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2 pt-4 border-t border-paper-100">
                {message.files.map((file, i) => (
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

export function TypingIndicator({ mode }: { mode: Mode }) {
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
