import React, { useState, useEffect } from 'react';
import { Link } from 'wouter';
import { NeuralCityEnhanced } from '@/components/NeuralCityEnhanced';
import { useScrollytellingStateEnhanced } from '@/hooks/useScrollytellingStateEnhanced';
import '../styles/scrollytelling.css';

export default function ScrollytellingHome() {
  const sceneState = useScrollytellingStateEnhanced();
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mediaQuery.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return (
    <div className="scrollytelling-container relative">
      {/* Fixed 3D Canvas Viewport - Mounted behind text with pointer-events-none */}
      <div className="canvas-container" style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: 1, pointerEvents: 'none' }}>
        <NeuralCityEnhanced sceneState={sceneState} />
      </div>

      {/* Cinematic Transition Overlays controlled by GSAP callbacks */}
      <div id="glitch-overlay" className="fixed inset-0 pointer-events-none mix-blend-mode-difference z-40 bg-white opacity-0 transition-opacity duration-75"></div>
      <div id="flash-overlay" className="fixed inset-0 pointer-events-none z-40 bg-white opacity-0 transition-opacity duration-150"></div>
      <div id="wipe-overlay" className="fixed inset-0 pointer-events-none z-40 bg-slate-950 transition-all duration-300" style={{ clipPath: 'polygon(0 0, 0 0, 0 100%, 0 100%)' }}></div>

      {/* Scrollable Content Layers - Positioned on top with z-20 */}
      <div className="content-wrapper relative z-20">

        {/* SCENE 1: THE NEURAL METROPOLIS (HERO) */}
        <section className="scene hero-scene min-h-screen flex flex-col justify-between items-center text-center py-20 pointer-events-none" data-section="hero">
          <div className="mt-8 pointer-events-auto">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-blue-400/30 bg-blue-400/10 text-xs font-semibold text-blue-400 tracking-wider uppercase font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
              RAZORPAY AI BUILDATHON — TRACK 02 · AI RISK MANAGER
            </span>
          </div>

          <div className="scene-content max-w-4xl pointer-events-auto my-auto relative">
            <div className="radial-vignette"></div>
            <h1 className="hero-title text-5xl md:text-7xl font-bold leading-tight text-white mb-6">
              RiskLock <br/>
              <span className="bg-gradient-to-r from-blue-400 via-teal-400 to-fuchsia-500 bg-clip-text text-transparent">
                Fraud-Spike Detector
              </span>
            </h1>
            <p className="hero-subhead text-lg md:text-xl text-gray-400 max-w-2xl mx-auto font-light leading-relaxed">
              One engine. Four safeguards, working every transaction.
            </p>
          </div>

          <div className="scroll-cue flex flex-col items-center gap-2 text-gray-500 font-mono text-xs uppercase tracking-widest mt-12 pointer-events-auto">
            <span>Scroll down to explore</span>
            <svg className="w-5 h-5 animate-bounce-slow text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </section>

        {/* SCENE 2: THE PROBLEM (DISCONNECTION) */}
        <section className="scene problem-scene min-h-[250vh] relative px-6 py-20 flex flex-col justify-start" data-section="problem">
          <div className="sticky top-20 max-w-xl self-start pointer-events-auto z-30 text-glass-panel border border-rose-500/30">
            <h2 className="text-[10px] uppercase font-mono tracking-widest text-rose-500 font-bold mb-2">Scene 02 / The Crisis</h2>
            <h3 className="text-3xl md:text-4xl font-bold text-white mb-6">The Trust Gap</h3>
            <p className="text-gray-400 text-sm leading-relaxed">
              Every flagged transaction raises the same three questions — and most systems can't answer any of them.
            </p>
          </div>

          <div className="relative w-full max-w-xl self-end space-y-40 mt-[30vh] pointer-events-auto">
            {/* Problem Card 1 */}
            <div id="react-problem-card-1" className="glass-card p-8 rounded-3xl relative overflow-hidden transition-all duration-300">
              <div className="absolute top-0 left-0 w-2.5 h-full bg-rose-500"></div>
              <h4 className="text-lg font-bold text-white mb-2">Black-Box Scoring</h4>
              <p className="text-sm text-gray-400 leading-relaxed">
                A probability with no explanation is not a decision anyone can defend.
              </p>
            </div>

            {/* Problem Card 2 */}
            <div id="react-problem-card-2" className="glass-card p-8 rounded-3xl relative overflow-hidden transition-all duration-300">
              <div className="absolute top-0 left-0 w-2.5 h-full bg-rose-500"></div>
              <h4 className="text-lg font-bold text-white mb-2">Invisible Bias</h4>
              <p className="text-sm text-gray-400 leading-relaxed">
                A model can discriminate quietly for months before anyone notices the pattern.
              </p>
            </div>

            {/* Problem Card 3 */}
            <div id="react-problem-card-3" className="glass-card p-8 rounded-3xl relative overflow-hidden transition-all duration-300">
              <div className="absolute top-0 left-0 w-2.5 h-full bg-rose-500"></div>
              <h4 className="text-lg font-bold text-white mb-2">Silent Drift</h4>
              <p className="text-sm text-gray-400 leading-relaxed">
                Fraud patterns change. Most systems don't know when they've stopped working.
              </p>
            </div>
          </div>
        </section>

        {/* SCENE 3: THE SOLUTION (COPILOT CONNECTS) */}
        <section className="scene solution-scene min-h-screen flex items-center justify-center px-6 py-20 relative" data-section="solution">
          <div className="scene-content max-w-3xl text-center glass-card p-10 md:p-14 rounded-[36px] border border-white/10 shadow-2xl relative overflow-hidden pointer-events-auto">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-400 via-teal-400 to-fuchsia-500"></div>
            <h2 className="text-[10px] uppercase font-mono tracking-widest text-teal-400 font-bold mb-3">Scene 03 / Convergence</h2>
            <h3 className="text-3xl md:text-5xl font-bold text-white mb-6">One Engine, Four Safeguards.</h3>
            <p className="text-gray-300 text-base md:text-lg leading-relaxed max-w-xl mx-auto font-light">
              RiskLock scores every transaction, explains the decision, checks itself for bias, and watches its own reliability — before a human ever sees it.
            </p>
          </div>
        </section>

        {/* SCENE 4: WHY UNIQUE (DOMAIN AGENTS + RAG) */}
        <section className="scene agents-scene min-h-[400vh] relative px-6 py-20 flex flex-col justify-start" data-section="agents">
          <div className="sticky top-20 max-w-xl self-start z-30 pointer-events-auto text-glass-panel border border-fuchsia-500/30">
            <h2 className="text-[10px] uppercase font-mono tracking-widest text-fuchsia-500 font-bold mb-2">Scene 04 / Nodes</h2>
            <h3 className="text-3xl md:text-4xl font-bold text-white mb-6">Specialized Safeguards</h3>
            <p className="text-gray-400 text-sm leading-relaxed">
              Four distinct intelligence safeguards working autonomously every transaction, with built-in guardrails and human escalation routes.
            </p>
          </div>

          <div className="relative w-full max-w-xl self-end space-y-96 mt-[30vh] pointer-events-auto">
            {/* Agent 1 Panel */}
            <div id="react-agent-panel-1" className="glass-card p-8 rounded-3xl relative overflow-hidden transition-all duration-300">
              <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/10 rounded-bl-full pointer-events-none"></div>
              <span className="hud-label text-[10px] text-amber-500 font-bold block mb-1.5">DETECTION</span>
              <h4 className="text-xl font-bold text-white mb-3">Detection</h4>
              <p className="text-sm text-gray-400 leading-relaxed mb-4">
                Scores every transaction in real time with a calibrated XGBoost model, catching 98.8% of held-out fraud cases.
              </p>
              <div className="text-[10px] font-mono text-amber-500 border border-amber-500/20 bg-amber-500/5 px-3 py-1.5 rounded-lg inline-block">
                Calibrated XGBoost (98.8% Recall)
              </div>
            </div>

            {/* Agent 2 Panel */}
            <div id="react-agent-panel-2" className="glass-card p-8 rounded-3xl relative overflow-hidden transition-all duration-300">
              <div className="absolute top-0 right-0 w-24 h-24 bg-fuchsia-500/10 rounded-bl-full pointer-events-none"></div>
              <span className="hud-label text-[10px] text-fuchsia-500 font-bold block mb-1.5">EXPLAINABILITY</span>
              <h4 className="text-xl font-bold text-white mb-3">Explainability</h4>
              <p className="text-sm text-gray-400 leading-relaxed mb-4">
                Generates a plain-English reason for every flagged transaction from live SHAP feature attributions — no black box.
              </p>
              <div className="text-[10px] font-mono text-fuchsia-500 border border-fuchsia-500/20 bg-fuchsia-500/5 px-3 py-1.5 rounded-lg inline-block">
                Live SHAP Attributions
              </div>
            </div>

            {/* Agent 3 Panel */}
            <div id="react-agent-panel-3" className="glass-card p-8 rounded-3xl relative overflow-hidden transition-all duration-300">
              <div className="absolute top-0 right-0 w-24 h-24 bg-teal-400/10 rounded-bl-full pointer-events-none"></div>
              <span className="hud-label text-[10px] text-teal-400 font-bold block mb-1.5">FAIRNESS</span>
              <h4 className="text-xl font-bold text-white mb-3">Fairness</h4>
              <p className="text-sm text-gray-400 leading-relaxed mb-4">
                Audits every decision by customer segment. Found and fixed an 18.25x friction disparity — down to 7.91x — at zero added cost.
              </p>
              <div className="text-[10px] font-mono text-teal-400 border border-teal-400/20 bg-teal-400/5 px-3 py-1.5 rounded-lg inline-block">
                18.25x → 7.91x Disparity Reduced
              </div>
            </div>

            {/* Agent 4 Panel */}
            <div id="react-agent-panel-4" className="glass-card p-8 rounded-3xl relative overflow-hidden transition-all duration-300">
              <div className="absolute top-0 right-0 w-24 h-24 bg-blue-400/10 rounded-bl-full pointer-events-none"></div>
              <span className="hud-label text-[10px] text-blue-400 font-bold block mb-1.5">DRIFT</span>
              <h4 className="text-xl font-bold text-white mb-3">Drift</h4>
              <p className="text-sm text-gray-400 leading-relaxed mb-4">
                Monitors live feature distributions with PSI tracking, stress-tested to confirm the alarm actually fires under real shift.
              </p>
              <div className="text-[10px] font-mono text-blue-400 border border-blue-400/20 bg-blue-400/5 px-3 py-1.5 rounded-lg inline-block">
                PSI Drift Monitoring
              </div>
            </div>
          </div>
        </section>

        {/* SCENE 5: CTA (READY TO GLIMPSE) */}
        <section className="scene cta-scene min-h-screen flex flex-col justify-center items-center py-20 pointer-events-none" data-section="cta">
          <div className="scene-content max-w-2xl text-center space-y-8 pointer-events-auto relative">
            <div className="radial-vignette"></div>
            <h2 className="text-5xl md:text-7xl font-bold tracking-tight text-white leading-none">
              Ready to see it decide?
            </h2>
            <p className="text-gray-400 text-sm md:text-base leading-relaxed max-w-md mx-auto font-light">
              Walk through a real flagged transaction.
            </p>

            <div className="pt-4 flex flex-col items-center gap-4">
              {/* Runway CTA Button */}
              <Link href="/dashboard" className="relative px-12 py-4 bg-gradient-to-r from-violet-600 to-blue-500 text-white font-extrabold uppercase tracking-wider text-xs rounded-full shadow-[0_16px_36px_rgba(139,92,246,0.4)] hover:shadow-[0_20px_52px_rgba(139,92,246,0.6)] hover:scale-[1.02] transition-all overflow-hidden group select-none block w-64 text-center">
                {/* Moving runway yellow line */}
                <div className="absolute inset-0 bg-slate-900 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center overflow-hidden pointer-events-none">
                  <div className="absolute inset-x-0 top-1.5 h-[1px] bg-slate-700/50" />
                  <div className="absolute inset-x-0 bottom-1.5 h-[1px] bg-slate-700/50" />
                  <div className="w-[200%] h-[2px] absolute top-1/2 -translate-y-1/2 runway-animation"></div>
                </div>
                
                <span className="relative z-10 block transition-transform duration-300 group-hover:translate-x-3">
                  ENTER THE CONSOLE
                </span>

                {/* Airplane icon */}
                <div className="absolute z-20 top-1/2 -translate-y-1/2 left-4 pointer-events-none text-white opacity-0 group-hover:opacity-100 group-hover:translate-x-36 transition-all duration-1000 ease-out">
                  <svg className="w-4 h-4 transform rotate-45" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M17.8 19.2 16 11l3.5-3.5a2.1 2.1 0 1 0-3-3L13 8 4.8 6.2c-.5-.1-1 .1-1.3.5l-.3.3c-.4.4-.4 1.1 0 1.5L9 12l-4 4H3l-1 1v2l1 1h2l1-1v-2l4-4 3.7 5.7c.4.4 1.1.4 1.5 0l.3-.3c.4-.3.6-.8.5-1.3Z" />
                  </svg>
                </div>
              </Link>

              {/* GitHub Link */}
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-xs font-mono text-gray-500 hover:text-white uppercase tracking-widest transition-colors pt-2">
                View Source on GitHub
              </a>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
