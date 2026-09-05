import React from 'react';
import { EnhancedSceneState } from '@/hooks/useScrollytellingStateEnhanced';

export function DebugSceneState({ sceneState }: { sceneState: EnhancedSceneState }) {
  const sceneNames = ['Hero', 'Problem', 'Solution', 'Safeguards', 'CTA'];

  return (
    <div style={{
      position: 'fixed',
      bottom: 20,
      right: 20,
      background: 'rgba(0, 0, 0, 0.8)',
      color: '#0ff',
      padding: '12px 16px',
      borderRadius: '8px',
      fontSize: '12px',
      fontFamily: 'monospace',
      zIndex: 9999,
      maxWidth: '300px',
      border: '1px solid #0ff'
    }}>
      <div style={{ marginBottom: '8px', fontWeight: 'bold' }}>
        Scene: {sceneNames[sceneState.sceneIndex]} ({sceneState.sceneIndex})
      </div>
      <div style={{ fontSize: '11px', lineHeight: '1.4' }}>
        <div>Progress: {(sceneState.progress * 100).toFixed(1)}%</div>
        <div>Scene Progress: {(sceneState.sceneProgress * 100).toFixed(1)}%</div>
        <div>Tower Dim: {sceneState.problemTowerDim.toFixed(2)}</div>
        <div>Pathway Ignition: {sceneState.solutionPathwayIgnition.map(p => p.toFixed(1)).join(', ')}</div>
        <div>Core Brightness: {sceneState.solutionCoreBrightness.toFixed(2)}</div>
        <div>Shockwave: {sceneState.differentiatorCoreShockwave.toFixed(2)}</div>
        <div>Shield Opacity: {sceneState.resilienceShieldOpacity.toFixed(2)}</div>
        <div>Whiteout: {sceneState.ctaWhiteoutFlash.toFixed(2)}</div>
      </div>
    </div>
  );
}
