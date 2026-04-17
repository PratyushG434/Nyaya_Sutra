import { Mode } from '../types';
import { User, Gavel } from 'lucide-react';

interface ModeSelectorProps {
  mode: Mode;
  onChange: (mode: Mode) => void;
}

export function ModeSelector({ mode, onChange }: ModeSelectorProps) {
  return (
    <div className="flex bg-paper-100 p-1 rounded-full border border-paper-200">
      <button
        onClick={() => onChange('citizen')}
        className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest transition-all duration-300 ${
          mode === 'citizen'
            ? 'bg-paper-800 text-white shadow-md'
            : 'text-paper-700 hover:text-paper-900'
        }`}
      >
        <User size={14} />
        <span>Citizen</span>
      </button>
      <button
        onClick={() => onChange('lawyer')}
        className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest transition-all duration-300 ${
          mode === 'lawyer'
            ? 'bg-paper-800 text-white shadow-md'
            : 'text-paper-700 hover:text-paper-900'
        }`}
      >
        <Gavel size={14} />
        <span>Advocate</span>
      </button>
    </div>
  );
}
