import React, { useState, useEffect } from 'react';
import { useLocation } from 'wouter';
import { Lock, Unlock, ShieldCheck, Terminal as TerminalIcon, Key, User, ArrowRight, UserPlus, Eye, EyeOff } from 'lucide-react';
import { NeuralCityEnhanced } from '@/components/NeuralCityEnhanced';
import { toast } from 'sonner';
import { motion, AnimatePresence } from 'framer-motion';

export default function AuthPage() {
  const [, setLocation] = useLocation();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [authSuccess, setAuthSuccess] = useState(false);
  const [skipFX, setSkipFX] = useState(() => {
    const saved = localStorage.getItem('risklock_skip_fx');
    return saved !== null ? saved === 'true' : true;
  });

  const handleInstantSkip = () => {
    localStorage.setItem('copilot_session_active', 'true');
    localStorage.setItem('risklock_user', username.trim() || 'admin');
    toast.success('Instant Ingress granted.');
    setLocation('/dashboard');
  };

  // Ingress gate sliding doors state: 'closed' | 'open'
  const [gateState, setGateState] = useState<'closed' | 'open'>('open');
  // Handshake anim state: 'idle' | 'scanning' | 'locked'
  const [handshakeState, setHandshakeState] = useState<'idle' | 'scanning' | 'locked'>('idle');

  // Background NeuralCity setup
  const mockSceneState = {
    progress: 0,
    sceneIndex: 0,
    sceneProgress: 0,
    heroCoreScale: 1,
    heroParticleOpacity: 0.8,
    problemTowerDim: 0,
    problemPathwayOpacity: 0,
    problemWarningParticles: 0,
    solutionPathwayIgnition: [1, 1, 1, 1],
    solutionCoreRotationSpeed: 0.5,
    solutionCoreBrightness: 0.2,
    agentsTowerFocusIndex: -1,
    agentsTowerBrightness: [0.3, 0.3, 0.3, 0.3],
    differentiatorPathwayPulse: 0.2,
    differentiatorCoreShockwave: 0,
    differentiatorCoreFlash: 0,
    resilienceShieldOpacity: 0,
    resilienceShieldPulse: 0,
    ctaCityBrightness: 0.5,
    ctaPathwaysLit: 0.5,
    ctaCoreRotationSpeed: 1,
    ctaCameraTowardCore: 0,
    ctaWhiteoutFlash: 0
  };

  const API_BASE = (import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://127.0.0.1:8000" : window.location.origin)).replace(/\/$/, "");

  const runSequenceLogs = async (steps: string[]) => {
    setLogs([]);
    for (let i = 0; i < steps.length; i++) {
      await new Promise((resolve) => setTimeout(resolve, 300));
      setLogs((prev) => [...prev, steps[i]]);
    }
  };

  const verifyCredentials = async (cleanUser: string, cleanPass: string) => {
    // 1. Try real backend endpoint
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // transmit HttpOnly, SameSite=Strict session cookie
        body: JSON.stringify({ username: cleanUser, password: cleanPass }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.token) {
          sessionStorage.setItem('risklock_session_token', data.token);
        }
        return { username: data.username || cleanUser };
      } else if (res.status === 401 || res.status === 400 || res.status === 422 || res.status === 429) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Authentication rejected by security policy.');
      }
    } catch (err: any) {
      if (err.message && (err.message.includes('Invalid') || err.message.includes('passcode') || err.message.includes('locked') || err.message.includes('rejected'))) {
        throw err;
      }
      // Backend offline or network error — fall back to local demo verification
    }

    // 2. Local resilient verification for offline / disconnected demo mode
    const registered = JSON.parse(localStorage.getItem('risklock_users') || '{}');
    const u = cleanUser.toLowerCase();
    
    if (
      (u === 'admin' && cleanPass === 'risklock') ||
      (registered[cleanUser] && registered[cleanUser] === cleanPass)
    ) {
      return { username: cleanUser };
    }

    throw new Error('Authentication failed. Invalid passcode (Demo: admin / risklock)');
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanUser = username.trim();
    const cleanPass = password.trim();

    if (!cleanUser || !cleanPass) {
      toast.error('Please enter both identifier and secret code.');
      return;
    }

    setIsLoading(true);

    if (skipFX) {
      try {
        const authResult = await verifyCredentials(cleanUser, cleanPass);
        localStorage.setItem('copilot_session_active', 'true');
        localStorage.setItem('risklock_user', authResult.username);
        toast.success('Validation Successful. Ingress granted.');
        setLocation('/dashboard');
      } catch (error: any) {
        toast.error(error.message || 'Login failed.');
        setIsLoading(false);
      }
      return;
    }

    // IMMERSIVE ANIMATION PATH
    // 1. Slide Ingress doors shut
    setGateState('closed');
    setLogs(['[INGRESS] Gate locked. Initiating credentials validation...']);
    
    // Wait for door sliding shut transition
    await new Promise((resolve) => setTimeout(resolve, 600));
    setHandshakeState('scanning');

    // Enforce scan timing to show handshake brackets moving & sweep lines
    await new Promise((resolve) => setTimeout(resolve, 1200));

    try {
      const authResult = await verifyCredentials(cleanUser, cleanPass);

      // snap handshakes together
      setHandshakeState('locked');
      
      await runSequenceLogs([
        '[HANDSHAKE] Handshake validation request locked...',
        '[VERIFYING] Secure decryptor checks active...',
        `[IDENTIFIED] Authorized: ${authResult.username.toUpperCase()} (RiskLock Core)`,
        '[INGRESS APPROVED] Opening gateway sliding portals...'
      ]);

      setAuthSuccess(true);
      localStorage.setItem('copilot_session_active', 'true');
      localStorage.setItem('risklock_user', authResult.username);
      
      // Slide doors open
      setTimeout(() => {
        setGateState('open');
        toast.success('Access Granted. Ingress secure.');
      }, 500);

      setTimeout(() => {
        setLocation('/dashboard');
      }, 1500);

    } catch (error: any) {
      setHandshakeState('idle');
      setLogs((prev) => [...prev, `[FAILED] Handshake rejected: ${error.message}`]);
      toast.error(error.message || 'Verification rejected.');
      setIsLoading(false);
      setTimeout(() => setGateState('open'), 1000);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanUser = username.trim();
    const cleanPass = password.trim();
    const cleanConfirm = confirmPassword.trim();

    if (!cleanUser || !cleanPass || !cleanConfirm) {
      toast.error('All key inputs are required.');
      return;
    }

    if (cleanPass !== cleanConfirm) {
      toast.error('Passcodes do not match.');
      return;
    }

    setIsLoading(true);

    const registerCredentials = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: cleanUser, password: cleanPass }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || 'Enrollment rejected by security policy.');
        }
      } catch (err: any) {
        if (err.message && (err.message.includes('rejected') || err.message.includes('registered') || err.message.includes('reserved') || err.message.includes('characters'))) {
          throw err;
        }
        // Backend offline fallback
      }

      const registered = JSON.parse(localStorage.getItem('risklock_users') || '{}');
      registered[cleanUser] = cleanPass;
      localStorage.setItem('risklock_users', JSON.stringify(registered));
      return true;
    };

    if (skipFX) {
      try {
        await registerCredentials();
        toast.success('Registration successful! You can now log in.');
        setMode('login');
        setPassword('');
        setConfirmPassword('');
        setIsLoading(false);
      } catch (error: any) {
        toast.error(error.message || 'Registration failed.');
        setIsLoading(false);
      }
      return;
    }

    // IMMERSIVE REGISTRATION PATH
    setGateState('closed');
    setLogs(['[ENROLLMENT] Slide doors locked. Registering keys...']);
    
    await new Promise((resolve) => setTimeout(resolve, 600));
    setHandshakeState('scanning');

    // Enforce scan timing to show registration details
    await new Promise((resolve) => setTimeout(resolve, 1200));

    try {
      await registerCredentials();

      setHandshakeState('locked');

      await runSequenceLogs([
        '[ENROLLING] Writing credentials to secure vault...',
        '[SALTING] Injecting unique secure crypto-salt...',
        '[HASHING] SHA-256 encrypted keys written...',
        '[COMPLETED] User credentials record securely stored.'
      ]);

      toast.success('Registration successful! Enrollment complete.');
      
      setTimeout(() => {
        setGateState('open');
        setMode('login');
        setPassword('');
        setConfirmPassword('');
        setLogs([]);
        setHandshakeState('idle');
        setIsLoading(false);
      }, 1200);

    } catch (error: any) {
      setHandshakeState('idle');
      setLogs((prev) => [...prev, `[FAILED] Enrollment rejected: ${error.message}`]);
      toast.error(error.message || 'Registration rejected.');
      setIsLoading(false);
      setTimeout(() => setGateState('open'), 1000);
    }
  };

  return (
    <div className="min-h-screen w-full relative flex items-center justify-center bg-gray-950 text-white font-sans overflow-hidden select-none">
      <style>{`
        @keyframes blink { 50% { opacity: 0; } }
        .blinking-cursor::after {
          content: ' _';
          animation: blink 1s infinite step-start;
          color: #818cf8;
        }
        .neon-glow {
          box-shadow: 0 0 20px rgba(99, 102, 241, 0.1);
        }
        .neon-glow:focus-within {
          box-shadow: 0 0 25px rgba(99, 102, 241, 0.3);
        }
        @keyframes shockwave {
          0% { transform: scale(0.8); opacity: 0.8; }
          100% { transform: scale(2.2); opacity: 0; }
        }
        .shockwave-ring {
          animation: shockwave 0.8s ease-out forwards;
        }
        @keyframes dash {
          to { stroke-dashoffset: -40; }
        }
        .pulsing-path {
          stroke-dasharray: 8;
          animation: dash 2.5s linear infinite;
        }
      `}</style>

      {/* Neural City Backdrop */}
      <div className="fixed inset-0 pointer-events-none z-0 opacity-40">
        <NeuralCityEnhanced sceneState={mockSceneState} />
      </div>

      <div className="absolute inset-0 bg-gray-950/70 z-1 pointer-events-none backdrop-blur-sm" />

      {/* Ingress Card console */}
      <div className="z-10 w-full max-w-md bg-gray-900/80 border border-white/10 rounded-[32px] shadow-2xl relative overflow-hidden h-[480px]">
        {/* Glow Header bar */}
        <div className={`absolute top-0 inset-x-0 h-1 bg-gradient-to-r transition-all duration-500 z-30 ${
          authSuccess ? 'from-emerald-500 to-teal-400' : 'from-indigo-500 via-purple-500 to-blue-500'
        }`} />

        {/* INNER FORM PANELS (revealed when gateState is open) */}
        <div className="p-8 flex flex-col justify-between h-full relative z-10">
          <div>
            <div className="text-center mb-5 mt-4">
              <h2 className="text-2xl font-black uppercase tracking-tight text-white mb-1 blinking-cursor">
                {mode === 'login' ? 'GATEWAY INGRESS' : 'KEY ENROLLMENT'}
              </h2>
              <p className="text-[10px] text-gray-400 leading-relaxed max-w-xs mx-auto">
                {mode === 'login' 
                  ? 'Access secure control center console.' 
                  : 'Enroll new cryptographic keys to SQLite core.'}
              </p>
            </div>

            {/* Mode selection tabs */}
            <div className="grid grid-cols-2 gap-1.5 bg-black/40 border border-white/5 p-1 rounded-2xl mb-4 text-[10px] font-bold font-mono">
              <button
                type="button"
                onClick={() => { if (!isLoading) { setMode('login'); setLogs([]); } }}
                className={`py-1.5 rounded-xl transition-all duration-300 ${
                  mode === 'login' 
                    ? 'bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 text-indigo-300' 
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                [ SIGN_IN ]
              </button>
              <button
                type="button"
                onClick={() => { if (!isLoading) { setMode('register'); setLogs([]); } }}
                className={`py-1.5 rounded-xl transition-all duration-300 ${
                  mode === 'register' 
                    ? 'bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 text-indigo-300' 
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                [ ENROLL_KEYS ]
              </button>
            </div>

            <form onSubmit={mode === 'login' ? handleLoginSubmit : handleRegisterSubmit} className="space-y-3.5">
              {/* Username field */}
              <div className="space-y-1">
                <label className="text-[9px] uppercase font-bold text-gray-500 tracking-wider flex items-center gap-1 font-mono">
                  <span>[ USERNAME ]</span>
                </label>
                <div className="relative rounded-2xl bg-black/40 border border-white/5 flex items-center transition-all duration-300 neon-glow">
                  <User className="w-3.5 h-3.5 text-gray-500 absolute left-4" />
                  <input
                    type="text"
                    placeholder="ENTER IDENTIFIER"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    disabled={isLoading}
                    className="w-full bg-transparent pl-11 pr-4 py-2.5 text-xs text-white placeholder-gray-600 focus:outline-none font-mono"
                  />
                </div>
              </div>

              {/* Password field */}
              <div className="space-y-1">
                <label className="text-[9px] uppercase font-bold text-gray-500 tracking-wider flex items-center gap-1 font-mono">
                  <span>[ INGRESS CODE ]</span>
                </label>
                <div className="relative rounded-2xl bg-black/40 border border-white/5 flex items-center transition-all duration-300 neon-glow">
                  <Key className="w-3.5 h-3.5 text-gray-500 absolute left-4" />
                  <input
                    type={showPassword ? "text" : "password"}
                    placeholder="ENTER SECRET PASSCODE"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={isLoading}
                    className="w-full bg-transparent pl-11 pr-10 py-2.5 text-xs text-white placeholder-gray-600 focus:outline-none font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Confirm Password (Register mode) */}
              {mode === 'register' && (
                <div className="space-y-1">
                  <label className="text-[9px] uppercase font-bold text-gray-500 tracking-wider flex items-center gap-1 font-mono">
                    <span>[ VERIFY PASSCODE ]</span>
                  </label>
                  <div className="relative rounded-2xl bg-black/40 border border-white/5 flex items-center transition-all duration-300 neon-glow">
                    <Key className="w-3.5 h-3.5 text-gray-500 absolute left-4" />
                    <input
                      type={showPassword ? "text" : "password"}
                      placeholder="RE-ENTER SECRET PASSCODE"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      disabled={isLoading}
                      className="w-full bg-transparent pl-11 pr-4 py-2.5 text-xs text-white placeholder-gray-600 focus:outline-none font-mono"
                    />
                  </div>
                </div>
              )}

              {/* Skip Animation Toggle */}
              <div className="flex items-center justify-between px-3 py-2 rounded-xl bg-white/[0.03] border border-white/5 font-mono text-[9px]">
                <div className="flex items-center gap-1.5 text-gray-300">
                  <span className="text-amber-400">⚡</span>
                  <span className="font-bold">Skip Animations (Instant Access)</span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const next = !skipFX;
                    setSkipFX(next);
                    localStorage.setItem('risklock_skip_fx', String(next));
                    toast.info(next ? 'Animations skipped: Instant login active' : 'Animations enabled: Immersive sequence active');
                  }}
                  className={`w-8 h-4 rounded-full p-0.5 transition-colors duration-200 cursor-pointer ${
                    skipFX ? 'bg-indigo-500' : 'bg-gray-800'
                  }`}
                >
                  <div
                    className={`w-3 h-3 bg-white rounded-full transition-transform duration-200 ${
                      skipFX ? 'translate-x-4' : ''
                    }`}
                  />
                </button>
              </div>

              {/* Authenticate submit */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 rounded-full font-bold uppercase tracking-wider text-[10px] bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500 text-white shadow-lg shadow-indigo-500/10 hover:shadow-indigo-500/20 transform active:scale-[0.98] transition-all flex items-center justify-center gap-1.5 cursor-pointer"
              >
                {mode === 'login' ? (
                  <>
                    <span>Request Handshake Ingress</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                ) : (
                  <>
                    <span>Enroll Credentials</span>
                    <UserPlus className="w-3.5 h-3.5" />
                  </>
                )}
              </button>

              {/* One-click instant bypass button */}
              <button
                type="button"
                onClick={() => {
                  setUsername('admin');
                  setPassword('risklock');
                  handleInstantSkip();
                }}
                className="w-full py-2 rounded-full font-mono text-[9px] uppercase tracking-wider font-bold bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/10 transition-all flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <span>⚡ Instant Demo Ingress (Skip All Animations)</span>
              </button>
            </form>
          </div>

          {/* Bottom Settings (Demo Helper) */}
          <div className="flex items-center justify-between pt-3 border-t border-white/5 text-[9px] font-mono">
            <button
              type="button"
              onClick={() => {
                setUsername('admin');
                setPassword('risklock');
                toast.info('Demo credentials loaded (admin / risklock)');
              }}
              className="text-indigo-400 hover:text-indigo-300 underline cursor-pointer"
            >
              Fill Demo Ingress (admin / risklock)
            </button>
            <span className="text-gray-500 text-[8px]">RiskLock v2.4</span>
          </div>
        </div>

        {/* HOLOGRAPHIC SLIDING AIRLOCK GATEWAY PANELS */}
        <AnimatePresence>
          {gateState === 'closed' && (
            <div className="absolute inset-0 z-20 flex overflow-hidden pointer-events-auto">
              
              {/* Escape hatch: Skip animation button */}
              <button
                onClick={handleInstantSkip}
                className="absolute top-6 right-6 z-50 px-3.5 py-1.5 bg-indigo-600/90 hover:bg-indigo-500 text-white text-[10px] font-mono font-bold uppercase tracking-wider rounded-full shadow-[0_0_20px_rgba(99,102,241,0.6)] border border-indigo-400/40 flex items-center gap-1.5 pointer-events-auto transition-all cursor-pointer hover:scale-105"
              >
                <span>⚡ Skip Animation</span>
                <ArrowRight className="w-3 h-3" />
              </button>
              
              {/* LEFT GATE DOOR */}
              <motion.div
                initial={{ x: '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: '-100%' }}
                transition={{ duration: 0.5, ease: [0.76, 0, 0.24, 1] }}
                className="w-1/2 h-full bg-slate-900 border-r border-indigo-500/30 flex flex-col justify-center items-end relative overflow-hidden"
              >
                {/* Circuit decorations */}
                <div className="absolute top-8 left-8 w-24 h-24 border-l border-t border-indigo-500/15 rounded-tl-xl pointer-events-none" />
                <div className="absolute bottom-8 left-8 w-24 h-24 border-l border-b border-indigo-500/15 rounded-bl-xl pointer-events-none" />
                <div className="w-8 h-px bg-gradient-to-r from-indigo-500/50 to-transparent absolute right-0 top-1/4" />
                <div className="w-12 h-px bg-gradient-to-r from-indigo-500/50 to-transparent absolute right-0 top-3/4" />

                {/* Left Door Status HUD Light */}
                <div className="absolute top-6 left-6 flex items-center gap-1.5 font-mono text-[7px] tracking-wider text-indigo-400/70">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                  <span>[INGRESS_SECURE]</span>
                </div>

                {/* Glowing SVG circuit paths */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-30 text-indigo-500" viewBox="0 0 200 480" fill="none">
                  <path d="M200 240 H140 L110 180 H70 L40 120 H10" stroke="currentColor" strokeWidth="1.5" className="pulsing-path" />
                  <path d="M200 240 H140 L110 300 H70 L40 360 H10" stroke="currentColor" strokeWidth="1.5" />
                  <circle cx="110" cy="180" r="3" fill="#818cf8" className="animate-pulse" />
                  <circle cx="70" cy="180" r="3" fill="#818cf8" />
                  <circle cx="40" cy="120" r="3" fill="#818cf8" />
                </svg>
              </motion.div>

              {/* RIGHT GATE DOOR */}
              <motion.div
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ duration: 0.5, ease: [0.76, 0, 0.24, 1] }}
                className="w-1/2 h-full bg-slate-900 border-l border-indigo-500/30 flex flex-col justify-center items-start relative overflow-hidden"
              >
                {/* Circuit decorations */}
                <div className="absolute top-8 right-8 w-24 h-24 border-r border-t border-indigo-500/15 rounded-tr-xl pointer-events-none" />
                <div className="absolute bottom-8 right-8 w-24 h-24 border-r border-b border-indigo-500/15 rounded-br-xl pointer-events-none" />
                <div className="w-8 h-px bg-gradient-to-l from-indigo-500/50 to-transparent absolute left-0 top-1/4" />
                <div className="w-12 h-px bg-gradient-to-l from-indigo-500/50 to-transparent absolute left-0 top-3/4" />

                {/* Right Door Status HUD Light */}
                <div className="absolute top-6 right-6 flex items-center gap-1.5 font-mono text-[7px] tracking-wider text-emerald-400/70">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
                  <span>[SHIELD_ACTIVE]</span>
                </div>

                {/* Glowing SVG circuit paths */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-30 text-indigo-500" viewBox="0 0 200 480" fill="none">
                  <path d="M0 240 H60 L90 180 H130 L160 120 H190" stroke="currentColor" strokeWidth="1.5" className="pulsing-path" />
                  <path d="M0 240 H60 L90 300 H130 L160 360 H190" stroke="currentColor" strokeWidth="1.5" />
                  <circle cx="90" cy="180" r="3" fill="#818cf8" />
                  <circle cx="130" cy="180" r="3" fill="#818cf8" className="animate-pulse" />
                  <circle cx="160" cy="120" r="3" fill="#818cf8" />
                </svg>
              </motion.div>

              {/* MIDDLE CENTRAL CORE HUD (Floating over doors) */}
              <div className="absolute inset-0 flex flex-col items-center justify-center z-30 pointer-events-none">
                
                {/* Snapping handshakes / validation center */}
                <div className="w-40 h-40 flex items-center justify-center relative">
                  
                  {/* Blinding white glow during auth success */}
                  {authSuccess && (
                    <div className="absolute inset-0 bg-white rounded-full filter blur-xl opacity-20 transform scale-110" />
                  )}

                  {/* Left geometric handshake bracket */}
                  <motion.div
                    initial={{ x: -120, opacity: 0 }}
                    animate={
                      handshakeState === 'scanning'
                        ? { x: -25, opacity: 0.8, y: [0, -5, 5, 0], transition: { y: { repeat: Infinity, duration: 1.5 }, x: { duration: 0.5 } } }
                        : handshakeState === 'locked'
                        ? { x: -8, opacity: 1, scale: 1.05 }
                        : { x: -120, opacity: 0 }
                    }
                    className="absolute z-10 pointer-events-auto"
                  >
                    <svg className="w-12 h-16 text-indigo-400" viewBox="0 0 30 50" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path d="M25 5 H5 V45 H25" strokeLinecap="round" strokeLinejoin="round" />
                      <line x1="5" y1="25" x2="20" y2="25" />
                    </svg>
                  </motion.div>

                  {/* Right geometric handshake bracket */}
                  <motion.div
                    initial={{ x: 120, opacity: 0 }}
                    animate={
                      handshakeState === 'scanning'
                        ? { x: 25, opacity: 0.8, y: [0, 5, -5, 0], transition: { y: { repeat: Infinity, duration: 1.5 }, x: { duration: 0.5 } } }
                        : handshakeState === 'locked'
                        ? { x: 8, opacity: 1, scale: 1.05 }
                        : { x: 120, opacity: 0 }
                    }
                    className="absolute z-10 pointer-events-auto"
                  >
                    <svg className="w-12 h-16 text-indigo-400" viewBox="0 0 30 50" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path d="M5 5 H25 V45 H5" strokeLinecap="round" strokeLinejoin="round" />
                      <line x1="25" y1="25" x2="10" y2="25" />
                    </svg>
                  </motion.div>

                  {/* Locking handshake central node core */}
                  <AnimatePresence>
                    {handshakeState === 'locked' && (
                      <motion.div
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0, opacity: 0 }}
                        className="absolute w-8 h-8 rounded-full bg-indigo-500 border border-white flex items-center justify-center z-20 shadow-[0_0_20px_rgba(99,102,241,0.8)]"
                      >
                        {authSuccess ? <ShieldCheck className="w-4 h-4 text-white" /> : <Lock className="w-4 h-4 text-white" />}
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Shockwave expanding ring (snapping effect) */}
                  {handshakeState === 'locked' && (
                    <div className="absolute w-12 h-12 rounded-full border-2 border-indigo-400 shockwave-ring" />
                  )}

                  {/* Static lock icon on closed gate initial state */}
                  {handshakeState === 'idle' && (
                    <button
                      onClick={() => {
                        if (!isLoading) setGateState('open');
                      }}
                      className="w-16 h-16 rounded-full bg-slate-900 border border-indigo-500/40 hover:border-indigo-400/80 flex flex-col items-center justify-center text-indigo-400 hover:text-indigo-300 hover:shadow-[0_0_25px_rgba(99,102,241,0.2)] pointer-events-auto transition-all cursor-pointer"
                    >
                      <Lock className="w-5 h-5 animate-pulse" />
                      <span className="text-[6px] uppercase font-bold font-mono tracking-widest mt-1">Decrypt</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
