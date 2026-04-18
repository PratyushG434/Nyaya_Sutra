import { CheckCircle2, Circle, ArrowRight } from 'lucide-react';
import { TimelineStep } from '../types';

interface TimelineProps {
  steps: TimelineStep[];
  caseType?: string;
}

export function Timeline({ steps, caseType }: TimelineProps) {
  return (
    <div className="my-6 p-6 rounded-2xl bg-white border border-paper-200 shadow-sm overflow-hidden">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-paper-100 flex items-center justify-center text-paper-700">
            <ArrowRight size={20} />
          </div>
          <div>
            <h3 className="text-sm font-serif text-paper-900 font-bold uppercase tracking-wider">
              Legal Roadmap
            </h3>
            {caseType && (
              <p className="text-[10px] text-paper-400 font-bold uppercase tracking-widest mt-0.5">
                Target: {caseType}
              </p>
            )}
          </div>
        </div>
        <div className="px-3 py-1 rounded-full bg-paper-50 border border-paper-100 text-[10px] font-bold text-paper-500 uppercase tracking-tight">
          Actionable Journey
        </div>
      </div>

      <div className="relative space-y-0">
        {/* Connection Line */}
        <div className="absolute left-[19px] top-2 bottom-2 w-0.5 bg-paper-100" />

        {steps.map((step, index) => {
          const isDone = step.status === 'done';
          const isCurrent = step.status === 'current';
          const isUpcoming = step.status === 'upcoming';

          return (
            <div
              key={index}
              className={`relative pl-12 pb-8 last:pb-0 group transition-all duration-500 ${
                isUpcoming ? 'opacity-40 grayscale-[0.5]' : 'opacity-100'
              }`}
            >
              {/* Dot / Icon */}
              <div className="absolute left-0 top-0 z-10">
                {isDone ? (
                  <div className="w-10 h-10 rounded-full bg-green-50 flex items-center justify-center text-green-600 border border-green-100 shadow-sm transition-transform group-hover:scale-110">
                    <CheckCircle2 size={20} />
                  </div>
                ) : isCurrent ? (
                  <div className="w-10 h-10 rounded-full bg-paper-800 flex items-center justify-center text-white border-4 border-paper-100 shadow-lg animate-pulse-subtle transition-transform group-hover:scale-110">
                    <Circle size={14} fill="white" />
                  </div>
                ) : (
                  <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-paper-200 border border-paper-100 shadow-sm transition-transform group-hover:scale-110">
                    <Circle size={14} />
                  </div>
                )}
              </div>

              <div className="pt-2">
                <h4
                  className={`text-sm font-bold tracking-tight mb-1 transition-colors ${
                    isDone
                      ? 'text-paper-400 line-through decoration-paper-200'
                      : isCurrent
                      ? 'text-paper-900'
                      : 'text-paper-400'
                  }`}
                >
                  {step.title}
                </h4>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[9px] font-bold uppercase tracking-[0.15em] px-2 py-0.5 rounded ${
                      isDone
                        ? 'bg-green-50 text-green-600'
                        : isCurrent
                        ? 'bg-paper-100 text-paper-800'
                        : 'bg-paper-50 text-paper-300'
                    }`}
                  >
                    {step.status}
                  </span>
                  {isCurrent && (
                    <span className="flex h-1.5 w-1.5 rounded-full bg-paper-800 animate-ping" />
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
