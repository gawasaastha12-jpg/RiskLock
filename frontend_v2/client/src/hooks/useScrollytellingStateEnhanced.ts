import { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import ScrollTrigger from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export interface EnhancedSceneState {
  progress: number;
  sceneIndex: number;
  sceneProgress: number;
  heroCoreScale: number;
  heroParticleOpacity: number;
  problemTowerDim: number;
  problemPathwayOpacity: number;
  problemWarningParticles: number;
  solutionPathwayIgnition: number[];
  solutionCoreRotationSpeed: number;
  solutionCoreBrightness: number;
  agentsTowerFocusIndex: number;
  agentsTowerBrightness: number[];
  differentiatorPathwayPulse: number;
  differentiatorCoreShockwave: number;
  differentiatorCoreFlash: number;
  resilienceShieldOpacity: number;
  resilienceShieldPulse: number;
  ctaCityBrightness: number;
  ctaPathwaysLit: number;
  ctaCoreRotationSpeed: number;
  ctaCameraTowardCore: number;
  ctaWhiteoutFlash: number;
}

export function useScrollytellingStateEnhanced(): EnhancedSceneState {
  const [state, setState] = useState<EnhancedSceneState>({
    progress: 0,
    sceneIndex: 0,
    sceneProgress: 0,
    heroCoreScale: 1,
    heroParticleOpacity: 1,
    problemTowerDim: 0,
    problemPathwayOpacity: 0,
    problemWarningParticles: 0,
    solutionPathwayIgnition: [1, 1, 1, 1], // Start active, dim on problem
    solutionCoreRotationSpeed: 1,
    solutionCoreBrightness: 0.3,
    agentsTowerFocusIndex: -1,
    agentsTowerBrightness: [0.3, 0.3, 0.3, 0.3],
    differentiatorPathwayPulse: 0,
    differentiatorCoreShockwave: 0,
    differentiatorCoreFlash: 0,
    resilienceShieldOpacity: 0,
    resilienceShieldPulse: 0,
    ctaCityBrightness: 1,
    ctaPathwaysLit: 1,
    ctaCoreRotationSpeed: 1,
    ctaCameraTowardCore: 0,
    ctaWhiteoutFlash: 0
  });

  useEffect(() => {
    gsap.to(window, {
      scrollTrigger: {
        trigger: 'body',
        start: 'top top',
        end: 'bottom bottom',
        scrub: 1,
        onUpdate: (self) => {
          const progress = self.progress;
          let sceneIndex = 0;
          let sceneStart = 0;
          let sceneEnd = 0.2;

          // 5-Scene linear mapping (Hero -> Problem -> Solution -> 4 Pillars -> CTA)
          if (progress < 0.15) {
            sceneIndex = 0;
            sceneStart = 0;
            sceneEnd = 0.15;
          } else if (progress < 0.35) {
            sceneIndex = 1;
            sceneStart = 0.15;
            sceneEnd = 0.35;
          } else if (progress < 0.50) {
            sceneIndex = 2;
            sceneStart = 0.35;
            sceneEnd = 0.50;
          } else if (progress < 0.85) {
            sceneIndex = 3;
            sceneStart = 0.50;
            sceneEnd = 0.85;
          } else {
            sceneIndex = 4;
            sceneStart = 0.85;
            sceneEnd = 1.0;
          }

          const sceneProgress = (progress - sceneStart) / (sceneEnd - sceneStart);

          const newState: EnhancedSceneState = {
            progress,
            sceneIndex,
            sceneProgress,
            heroCoreScale: 1,
            heroParticleOpacity: 1,
            problemTowerDim: 0,
            problemPathwayOpacity: 0,
            problemWarningParticles: 0,
            solutionPathwayIgnition: [1, 1, 1, 1],
            solutionCoreRotationSpeed: 1,
            solutionCoreBrightness: 0.3,
            agentsTowerFocusIndex: -1,
            agentsTowerBrightness: [0.85, 0.85, 0.85, 0.85],
            differentiatorPathwayPulse: 0,
            differentiatorCoreShockwave: 0,
            differentiatorCoreFlash: 0,
            resilienceShieldOpacity: 0,
            resilienceShieldPulse: 0,
            ctaCityBrightness: 1,
            ctaPathwaysLit: 1,
            ctaCoreRotationSpeed: 1,
            ctaCameraTowardCore: 0,
            ctaWhiteoutFlash: 0
          };

          if (sceneIndex === 0) {
            // Scene 1: Hero
            newState.heroCoreScale = 1 + Math.sin(Date.now() * 0.001) * 0.08;
            newState.solutionPathwayIgnition = [1, 1, 1, 1];
          } else if (sceneIndex === 1) {
            // Scene 2: Problem
            newState.problemTowerDim = Math.min(sceneProgress * 1.5, 1);
            newState.solutionPathwayIgnition = [
              1 - newState.problemTowerDim * 0.9,
              1 - newState.problemTowerDim * 0.9,
              1 - newState.problemTowerDim * 0.9,
              1 - newState.problemTowerDim * 0.9
            ];
            newState.problemWarningParticles = sceneProgress;
            newState.solutionCoreBrightness = 0.3 - newState.problemTowerDim * 0.25;
            newState.solutionCoreRotationSpeed = 0.3;
          } else if (sceneIndex === 2) {
            // Scene 3: Solution Connects
            const ignitionDelay = 0.15;
            newState.solutionPathwayIgnition = [
              Math.max(0.1, Math.min(1, (sceneProgress - 0) / ignitionDelay)),
              Math.max(0.1, Math.min(1, (sceneProgress - ignitionDelay) / ignitionDelay)),
              Math.max(0.1, Math.min(1, (sceneProgress - ignitionDelay * 2) / ignitionDelay)),
              Math.max(0.1, Math.min(1, (sceneProgress - ignitionDelay * 3) / ignitionDelay))
            ];
            newState.solutionCoreRotationSpeed = 1 + sceneProgress * 1.8;
            newState.solutionCoreBrightness = 0.1 + sceneProgress * 0.9;
          } else if (sceneIndex === 3) {
            // Scene 4: Specialized Domain Agents
            newState.agentsTowerFocusIndex = Math.min(Math.floor(sceneProgress * 4), 3);
            const brightness = [0.25, 0.25, 0.25, 0.25];
            if (newState.agentsTowerFocusIndex >= 0) {
              brightness[newState.agentsTowerFocusIndex] = 1.0;
            }
            newState.agentsTowerBrightness = brightness;
            
            // Dynamic glyph animations & shockwave at end
            newState.differentiatorPathwayPulse = Math.sin(sceneProgress * Math.PI * 4) * 0.5 + 0.5;
            if (sceneProgress > 0.8) {
              newState.differentiatorCoreShockwave = (sceneProgress - 0.8) / 0.2;
              newState.differentiatorCoreFlash = Math.max(0, 1 - (sceneProgress - 0.8) / 0.2);
            }
            // Faint Resilience shield
            newState.resilienceShieldOpacity = sceneProgress * 0.65;
            newState.resilienceShieldPulse = Math.sin(sceneProgress * Math.PI * 2) * 0.5 + 0.5;
          } else if (sceneIndex === 4) {
            // Scene 5: CTA (Pushes camera toward core & whiteout)
            newState.ctaCityBrightness = 1;
            newState.ctaPathwaysLit = 1;
            newState.ctaCoreRotationSpeed = 2 + sceneProgress * 2.5;
            newState.ctaCameraTowardCore = sceneProgress;
            if (sceneProgress > 0.75) {
              newState.ctaWhiteoutFlash = (sceneProgress - 0.75) / 0.25;
            }
          }

          setState(newState);
        }
      }
    });

    return () => {
      ScrollTrigger.getAll().forEach(trigger => trigger.kill());
      gsap.killTweensOf(window);
    };
  }, []);

  return state;
}
