import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Line } from '@react-three/drei';
import * as THREE from 'three';
import { EnhancedSceneState } from '@/hooks/useScrollytellingStateEnhanced';

// Shield ring for resilience scene
export function ShieldRing({ sceneState }: { sceneState: EnhancedSceneState }) {
  const ringRef = useRef<any>(null);

  const geometry = useMemo(() => {
    const points: THREE.Vector3[] = [];
    const segments = 64;
    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2;
      points.push(new THREE.Vector3(Math.cos(angle) * 150, 0, Math.sin(angle) * 150));
    }
    return points;
  }, []);

  useFrame(() => {
    if (ringRef.current && ringRef.current.material) {
      (ringRef.current.material as THREE.LineBasicMaterial).opacity = sceneState.resilienceShieldOpacity * 0.6;
    }
  });

  return (
    <Line
      ref={ringRef}
      points={geometry}
      color={0x60a5fa}
      lineWidth={2}
      transparent
      opacity={sceneState.resilienceShieldOpacity * 0.6}
    />
  );
}

// Shockwave effect for differentiator scene
export function Shockwave({ sceneState }: { sceneState: EnhancedSceneState }) {
  const shockwaveRef = useRef<THREE.Mesh>(null);

  useFrame(() => {
    if (shockwaveRef.current && shockwaveRef.current.material) {
      const scale = 1 + sceneState.differentiatorCoreShockwave * 3;
      shockwaveRef.current.scale.set(scale, 1, scale);
      (shockwaveRef.current.material as THREE.MeshBasicMaterial).opacity = Math.max(0, 0.6 - sceneState.differentiatorCoreShockwave * 0.8);
    }
  });

  return (
    <mesh ref={shockwaveRef} position={[0, 0, 0]}>
      <ringGeometry args={[40, 60, 32]} />
      <meshBasicMaterial
        color={0xfbbf24}
        transparent
        opacity={0.4}
        blending={THREE.AdditiveBlending}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

// Whiteout flash for CTA scene
export function WhiteoutFlash({ sceneState }: { sceneState: EnhancedSceneState }) {
  const flashRef = useRef<THREE.Mesh>(null);

  useFrame(() => {
    if (flashRef.current && flashRef.current.material) {
      (flashRef.current.material as THREE.MeshBasicMaterial).opacity = sceneState.ctaWhiteoutFlash * 0.8;
    }
  });

  return (
    <mesh ref={flashRef} position={[0, 0, 50]}>
      <planeGeometry args={[1000, 1000]} />
      <meshBasicMaterial color={0xffffff} transparent opacity={sceneState.ctaWhiteoutFlash * 0.8} />
    </mesh>
  );
}
