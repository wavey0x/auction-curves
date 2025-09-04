import React, { useEffect, useRef } from "react";
import { X, Settings, Tags, Volume2 } from "lucide-react";
import { useUserSettings } from "../context/UserSettingsContext";
import AddressTagManager from "./AddressTagManager";

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ open, onClose }) => {
  const { 
    defaultValueDisplay, setDefaultValueDisplay,
    customRpcEnabled, setCustomRpcEnabled,
    customRpcUrl, setCustomRpcUrl
  } = useUserSettings();
  const overlayRef = useRef<HTMLDivElement>(null);
  const [rpcInput, setRpcInput] = React.useState<string>(customRpcUrl || '');
  const [rpcError, setRpcError] = React.useState<string | null>(null);
  const [notificationSoundEnabled, setNotificationSoundEnabled] = React.useState(() => {
    try {
      return localStorage.getItem('notificationSoundEnabled') !== 'false'
    } catch { return true }
  });
  const [activeTab, setActiveTab] = React.useState<'general' | 'tags'>(() => {
    try {
      const v = localStorage.getItem('settings_active_tab')
      return (v === 'tags' || v === 'general') ? (v as 'general'|'tags') : 'general'
    } catch { return 'general' }
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  // sync input when opening
  useEffect(() => {
    if (open) {
      setRpcInput(customRpcUrl || '')
      setRpcError(null)
    }
  }, [open, customRpcUrl])

  // persist active tab selection
  useEffect(() => {
    try { localStorage.setItem('settings_active_tab', activeTab) } catch {}
  }, [activeTab])

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
      <div className="relative w-full max-w-[700px] rounded-xl border border-gray-800 bg-gray-900 shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <div className="flex items-center space-x-2 text-gray-200">
            <Settings className="h-4 w-4 text-primary-400" />
            <h3 className="font-semibold">Settings</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-gray-800 text-gray-400 hover:text-gray-200">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-800">
          <button
            onClick={() => setActiveTab('general')}
            className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'general'
                ? 'text-primary-400 border-b-2 border-primary-400 bg-primary-500/5'
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            <Settings className="h-4 w-4" />
            <span>General</span>
          </button>
          <button
            onClick={() => setActiveTab('tags')}
            className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'tags'
                ? 'text-primary-400 border-b-2 border-primary-400 bg-primary-500/5'
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            <Tags className="h-4 w-4" />
            <span>Address Tags</span>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-6 max-h-[70vh] overflow-y-auto">
          {activeTab === 'general' && (
            <>
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

          {/* Notification Sound Toggle */}
          <div className="space-y-3">
            <div className="flex items-start justify-between">
              <div className="pr-4">
                <div className="text-sm text-gray-200 flex items-center space-x-2">
                  <Volume2 className="h-4 w-4 text-primary-400" />
                  <span>Notification sounds</span>
                </div>
                <div className="text-xs text-gray-500 mt-1">Play kick drum sound on event notifications</div>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={notificationSoundEnabled}
                aria-label="Enable notification sounds"
                onClick={() => {
                  const newValue = !notificationSoundEnabled
                  setNotificationSoundEnabled(newValue)
                  localStorage.setItem('notificationSoundEnabled', String(newValue))
                }}
                className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors duration-200 shrink-0 ${
                  notificationSoundEnabled ? 'bg-primary-600' : 'bg-gray-700'
                }`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white shadow transition-transform duration-200 ${
                    notificationSoundEnabled ? 'translate-x-7' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            
            {/* Test Sound Button */}
            {notificationSoundEnabled && (
              <div>
                <button
                  onClick={() => {
                    // Test kick drum sound (same as NotificationBubble)
                    try {
                      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
                      const now = audioContext.currentTime
                      
                      // Create oscillator for the bass thump
                      const osc = audioContext.createOscillator()
                      const oscGain = audioContext.createGain()
                      
                      // Create noise for the attack/click
                      const noiseBufferSize = audioContext.sampleRate * 0.02
                      const noiseBuffer = audioContext.createBuffer(1, noiseBufferSize, audioContext.sampleRate)
                      const noiseData = noiseBuffer.getChannelData(0)
                      
                      // Generate brown noise
                      let lastOut = 0
                      for (let i = 0; i < noiseBufferSize; i++) {
                        const white = Math.random() * 2 - 1
                        noiseData[i] = (lastOut + (0.02 * white)) / 1.02
                        lastOut = noiseData[i]
                        noiseData[i] *= 3.5
                      }
                      
                      const noiseSource = audioContext.createBufferSource()
                      const noiseGain = audioContext.createGain()
                      const noiseFilter = audioContext.createBiquadFilter()
                      
                      noiseSource.buffer = noiseBuffer
                      noiseFilter.type = 'lowpass'
                      noiseFilter.frequency.value = 1000
                      noiseFilter.Q.value = 1
                      
                      // Kick drum frequency sweep
                      osc.type = 'sine'
                      osc.frequency.setValueAtTime(150, now)
                      osc.frequency.exponentialRampToValueAtTime(40, now + 0.1)
                      
                      // Envelopes
                      oscGain.gain.setValueAtTime(0, now)
                      oscGain.gain.linearRampToValueAtTime(0.8, now + 0.005)
                      oscGain.gain.exponentialRampToValueAtTime(0.001, now + 0.2)
                      
                      noiseGain.gain.setValueAtTime(0, now)
                      noiseGain.gain.linearRampToValueAtTime(0.4, now + 0.002)
                      noiseGain.gain.exponentialRampToValueAtTime(0.001, now + 0.05)
                      
                      // Connect and play
                      osc.connect(oscGain)
                      oscGain.connect(audioContext.destination)
                      noiseSource.connect(noiseFilter)
                      noiseFilter.connect(noiseGain)
                      noiseGain.connect(audioContext.destination)
                      
                      osc.start(now)
                      osc.stop(now + 0.2)
                      noiseSource.start(now)
                      noiseSource.stop(now + 0.05)
                    } catch (error) {
                      alert('Audio test failed: ' + error.message)
                    }
                  }}
                  className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-md transition-colors"
                >
                  Test Sound 🥁
                </button>
              </div>
            )}
          </div>

          {/* Custom RPC Toggle and Input */}
          <div className="space-y-3">
            <div className="flex items-start justify-between">
              <div className="pr-4">
                <div className="text-sm text-gray-200">Use custom RPC</div>
                <div className="text-xs text-gray-500 mt-1">Override default RPC with your own endpoint</div>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={customRpcEnabled}
                aria-label="Use custom RPC"
                onClick={() => setCustomRpcEnabled(!customRpcEnabled)}
                className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors duration-200 shrink-0 ${
                  customRpcEnabled ? 'bg-primary-600' : 'bg-gray-700'
                }`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white shadow transition-transform duration-200 ${
                    customRpcEnabled ? 'translate-x-7' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {customRpcEnabled && (
              <div>
                <label className="block text-xs text-gray-400 mb-1">RPC URL</label>
                <input
                  type="text"
                  value={rpcInput}
                  onChange={(e) => {
                    const v = e.target.value
                    setRpcInput(v)
                    const isValid = validateRpcUrl(v)
                    if (isValid) {
                      setRpcError(null)
                      setCustomRpcUrl(v.trim())
                    } else {
                      setRpcError('Enter a valid http(s) URL')
                    }
                  }}
                  placeholder="https://your-node.example.com"
                  className={`w-full rounded-lg bg-gray-800 border ${rpcError ? 'border-red-500' : 'border-gray-700'} px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 ${rpcError ? 'focus:ring-red-500' : 'focus:ring-primary-500'}`}
                />
                <div className="mt-1 text-xs">
                  {rpcError ? (
                    <span className="text-red-400">{rpcError}</span>
                  ) : (
                    <div className="space-y-1">
                      <span className="text-gray-500">Example: https://eth.merkle.io</span>
                      <div className="text-yellow-400">
                        ⚠️ CORS: Use http://localhost:3001 if you get CORS errors
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
            </>
          )}

          {activeTab === 'tags' && (
            <AddressTagManager />
          )}
        </div>

        {/* Bottom actions removed per request */}
      </div>
    </div>
  );
};

export default SettingsModal;

// extremely basic URL validation
function validateRpcUrl(v: string): boolean {
  const s = v.trim()
  if (!s) return false
  if (!/^https?:\/\//i.test(s)) return false
  try {
    const u = new URL(s)
    return !!u.hostname
  } catch {
    return false
  }
}
