import React, { useEffect, useRef } from "react";
import { X, Settings } from "lucide-react";
import { useUserSettings } from "../context/UserSettingsContext";

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ open, onClose }) => {
  const { defaultValueDisplay, setDefaultValueDisplay } = useUserSettings();
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!open) return null;

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === overlayRef.current) onClose();
  };

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div className="relative w-full max-w-md rounded-xl border border-gray-800 bg-gray-900 shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <div className="flex items-center space-x-2 text-gray-200">
            <Settings className="h-4 w-4 text-primary-400" />
            <h3 className="font-semibold">Settings</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-gray-800 text-gray-400 hover:text-gray-200">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-4 space-y-6">
          {/* Default Value Display Toggle */}
          <div className="flex items-start justify-between">
            <div className="pr-4">
              <div className="text-sm text-gray-200">Display values as USD</div>
              <div className="text-xs text-gray-500 mt-1">Currently displaying as <span className="text-gray-300 font-medium">{defaultValueDisplay === 'usd' ? 'USD' : 'token'}</span></div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={defaultValueDisplay === 'usd'}
              aria-label="Display values as USD"
              onClick={() => setDefaultValueDisplay(defaultValueDisplay === 'usd' ? 'token' : 'usd')}
              className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors duration-200 shrink-0 ${
                defaultValueDisplay === 'usd' ? 'bg-primary-600' : 'bg-gray-700'
              }`}
            >
              <span
                className={`inline-block h-6 w-6 transform rounded-full bg-white shadow transition-transform duration-200 ${
                  defaultValueDisplay === 'usd' ? 'translate-x-7' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Future settings can be added here */}
        </div>

        <div className="px-4 py-3 border-t border-gray-800 flex justify-end">
          <button onClick={onClose} className="px-3 py-1.5 bg-primary-500/20 text-primary-300 rounded hover:bg-primary-500/30 text-sm">Close</button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
