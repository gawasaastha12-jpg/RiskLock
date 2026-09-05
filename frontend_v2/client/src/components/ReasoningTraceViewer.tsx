import { useState } from "react";
import { Terminal, ChevronDown, ChevronUp } from "lucide-react";

interface ReasoningTraceViewerProps {
  trace?: string | null | any;
}

export default function ReasoningTraceViewer({ trace }: ReasoningTraceViewerProps) {
  const [isOpen, setIsOpen] = useState(false);

  const rawString = typeof trace === "string" 
    ? trace 
    : trace && typeof trace === "object" 
    ? JSON.stringify(trace, null, 2) 
    : "";

  if (!rawString) return null;

  const lines = rawString
    .split("\n")
    .map(line => line.trim())
    .filter(line => line.length > 0);

  const parseLine = (line: string) => {
    let tag = "Decision Engine";
    let tagColor = "bg-gray-800/50 border-gray-700/30 text-gray-400";
    let content = line;

    if (line.startsWith("XGBoost:") || line.startsWith("Calibrated XGBoost:")) {
      tag = "Calibrated XGBoost";
      tagColor = "bg-indigo-500/10 border-indigo-500/20 text-indigo-400";
      content = line.replace(/^(Calibrated )?XGBoost:\s*/, "");
    } else if (line.startsWith("SHAP:") || line.startsWith("Explainability:")) {
      tag = "SHAP Explainer";
      tagColor = "bg-sky-500/10 border-sky-500/20 text-sky-400";
      content = line.replace(/^(SHAP|Explainability):\s*/, "");
    } else if (line.startsWith("Fairness:") || line.startsWith("Pareto:")) {
      tag = "Fairness Audit";
      tagColor = "bg-teal-500/10 border-teal-500/20 text-teal-400";
      content = line.replace(/^(Fairness|Pareto):\s*/, "");
    } else if (line.startsWith("Drift:") || line.startsWith("PSI:")) {
      tag = "Drift Monitor";
      tagColor = "bg-blue-500/10 border-blue-500/20 text-blue-400";
      content = line.replace(/^(Drift|PSI):\s*/, "");
    } else if (line.startsWith("Decision:") || line.startsWith("Tier:")) {
      tag = "Decision Guard";
      tagColor = "bg-amber-500/10 border-amber-500/20 text-amber-400";
      content = line.replace(/^(Decision|Tier):\s*/, "");
    }

    return { tag, tagColor, content };
  };

  return (
    <div className="mt-4 border-t border-white/5 pt-4">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between text-[11px] font-bold text-gray-400 hover:text-white transition-all py-1"
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-indigo-400" />
          <span>RiskLock Engine Observability & SHAP Trace</span>
        </div>
        {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>

      {isOpen && (
        <div className="mt-3 bg-black/40 border border-white/5 rounded-2xl p-4 font-mono text-[10px] space-y-2.5 overflow-x-auto leading-relaxed max-h-64 overflow-y-auto">
          {lines.map((line, idx) => {
            const { tag, tagColor, content } = parseLine(line);
            return (
              <div key={idx} className="flex items-start gap-3">
                <span className={`px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider border shrink-0 ${tagColor}`}>
                  {tag}
                </span>
                <span className="text-gray-300 break-words">{content}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
