import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Save, Edit3 } from "lucide-react";

interface EditResponseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (newResponse: string) => Promise<void>;
  initialResponse: string;
}

export default function EditResponseModal({
  isOpen,
  onClose,
  onSave,
  initialResponse,
}: EditResponseModalProps) {
  const [response, setResponse] = useState(initialResponse);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setResponse(initialResponse);
    }
  }, [isOpen, initialResponse]);

  const handleSave = async () => {
    try {
      setSaving(true);
      await onSave(response);
      onClose();
    } catch (e) {
      console.error("Error saving response edit:", e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-md"
          />

          {/* Modal Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.5 }}
            className="w-full max-w-2xl bg-gray-900/90 border border-white/10 rounded-3xl p-6 shadow-2xl relative z-10 backdrop-blur-xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-4">
              <div className="flex items-center gap-2">
                <Edit3 className="w-5 h-5 text-indigo-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Edit AI Response
                </h3>
              </div>
              <button
                onClick={onClose}
                className="text-gray-500 hover:text-white p-1 hover:bg-white/5 rounded-xl transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Form */}
            <div className="space-y-4">
              <label className="text-[10px] uppercase tracking-wider text-gray-500 font-bold block">
                Drafted Response (Human-in-the-Loop Override)
              </label>
              <textarea
                value={response}
                onChange={(e) => setResponse(e.target.value)}
                rows={10}
                className="w-full bg-black/40 border border-white/10 rounded-2xl p-4 font-sans text-xs text-gray-200 focus:outline-none focus:border-indigo-500/50 leading-relaxed resize-none"
                placeholder="Write response text..."
              />
            </div>

            {/* Footer Actions */}
            <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-white/5">
              <button
                onClick={onClose}
                disabled={saving}
                className="px-4 py-2 border border-white/10 text-gray-400 hover:text-white hover:bg-white/5 rounded-2xl text-xs font-semibold transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white rounded-full text-xs font-bold shadow-[0_8px_32px_rgba(99,102,241,0.3)] transition disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" />
                {saving ? "Saving Changes..." : "Save & Update Draft"}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
