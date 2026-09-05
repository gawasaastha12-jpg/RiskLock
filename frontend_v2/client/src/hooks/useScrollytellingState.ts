import { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import ScrollTrigger from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export interface SceneState {
  progress: number;
  activeSection: number;
  cameraPosition: [number, number, number];
  pathwayIntensity: number;
  particleSpeed: number;
}

export function useScrollytellingState() {
  const [sceneState, setSceneState] = useState<SceneState>({
    progress: 0,
    activeSection: 0,
    cameraPosition: [200, 80, 200],
    pathwayIntensity: 0,
    particleSpeed: 0.3
  });

  useEffect(() => {
    // Define scroll sections
    const sections = [
      { name: 'hero', start: '0%', end: '12%' },
      { name: 'problem', start: '12%', end: '28%' },
      { name: 'solution', start: '28%', end: '40%' },
      { name: 'architecture', start: '40%', end: '60%' },
      { name: 'agents', start: '60%', end: '75%' },
      { name: 'differentiator', start: '75%', end: '85%' },
      { name: 'resilience', start: '85%', end: '92%' },
      { name: 'tech', start: '92%', end: '97%' },
      { name: 'cta', start: '97%', end: '100%' }
    ];

    sections.forEach((section, idx) => {
      ScrollTrigger.create({
        trigger: `[data-section="${section.name}"]`,
        start: 'top center',
        end: 'bottom center',
        onEnter: () => {
          setSceneState(prev => ({ ...prev, activeSection: idx }));
        },
        onEnterBack: () => {
          setSceneState(prev => ({ ...prev, activeSection: idx }));
        }
      });
    });

    // Main scroll animation
    gsap.to(window, {
      scrollTrigger: {
        trigger: 'body',
        start: 'top top',
        end: 'bottom bottom',
        scrub: 1,
        onUpdate: (self) => {
          const progress = self.progress;
          let pathwayIntensity = 0;
          let particleSpeed = 0.3;
          let cameraY = 80;

          // Scene 1: Hero (0-12%)
          if (progress < 0.12) {
            pathwayIntensity = 0;
            particleSpeed = 0.2;
            cameraY = 80;
          }
          // Scene 2: Problem (12-28%)
          else if (progress < 0.28) {
            pathwayIntensity = 0;
            particleSpeed = 0.1;
            cameraY = 60 + (progress - 0.12) / 0.16 * 20;
          }
          // Scene 3: Solution (28-40%)
          else if (progress < 0.40) {
            pathwayIntensity = (progress - 0.28) / 0.12;
            particleSpeed = 0.2 + (progress - 0.28) / 0.12 * 0.3;
            cameraY = 80 + (progress - 0.28) / 0.12 * 40;
          }
          // Scene 4: Architecture (40-60%)
          else if (progress < 0.60) {
            pathwayIntensity = 1;
            particleSpeed = 0.5;
            cameraY = 120;
          }
          // Scene 5: Agents (60-75%)
          else if (progress < 0.75) {
            pathwayIntensity = 1;
            particleSpeed = 0.5;
            cameraY = 120 - (progress - 0.60) / 0.15 * 20;
          }
          // Scene 6: Differentiator (75-85%)
          else if (progress < 0.85) {
            pathwayIntensity = 0.8 + (progress - 0.75) / 0.10 * 0.2;
            particleSpeed = 0.8;
            cameraY = 100;
          }
          // Scene 7: Resilience (85-92%)
          else if (progress < 0.92) {
            pathwayIntensity = 0.6;
            particleSpeed = 0.4;
            cameraY = 100;
          }
          // Scene 8: Tech (92-97%)
          else if (progress < 0.97) {
            pathwayIntensity = 0.3;
            particleSpeed = 0.3;
            cameraY = 100;
          }
          // Scene 9: CTA (97-100%)
          else {
            pathwayIntensity = 1;
            particleSpeed = 0.8;
            cameraY = 80 + (progress - 0.97) / 0.03 * 50;
          }

          setSceneState(prev => ({
            ...prev,
            progress,
            pathwayIntensity,
            particleSpeed,
            cameraPosition: [200, cameraY, 200]
          }));
        }
      }
    });

    return () => {
      ScrollTrigger.getAll().forEach(trigger => trigger.kill());
    };
  }, []);

  return sceneState;
}
