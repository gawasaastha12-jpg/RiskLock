import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Icosahedron, Line } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import * as THREE from 'three';
import gsap from 'gsap';

import { EnhancedSceneState } from '@/hooks/useScrollytellingStateEnhanced';

type SceneState = EnhancedSceneState;

const CONFIG = {
  domains: {
    finance: { color: 0x2dd4bf, name: 'Finance' },
    social: { color: 0xc026d3, name: 'Social Media' },
    customer: { color: 0xfbbf24, name: 'Customer Care' },
    management: { color: 0x60a5fa, name: 'Management' }
  },
  towerDistance: 120,
  coreScale: 1
};

// Tower component
function Tower({ position, color, active }: { position: THREE.Vector3; color: number; active: boolean }) {
  const groupRef = useRef<THREE.Group>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const wireGeometry = useMemo(() => new THREE.WireframeGeometry(new THREE.BoxGeometry(30, 60, 30)), []);

  useFrame(() => {
    if (groupRef.current) {
      const targetScale = active ? 1.15 : 1;
      groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
    }
  });

  return (
    <group ref={groupRef} position={position}>
      {/* Wireframe box */}
      <lineSegments geometry={wireGeometry}>
        <lineBasicMaterial color={color} linewidth={2} />
      </lineSegments>

      {/* Glow halo */}
      <mesh ref={glowRef}>
        <boxGeometry args={[32, 62, 32]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={active ? 0.25 : 0.1}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Glow sprite at top */}
      <mesh position={[0, 35, 0]}>
        <sphereGeometry args={[8, 16, 16]} />
        <meshBasicMaterial color={color} transparent opacity={0.4} blending={THREE.AdditiveBlending} />
      </mesh>
    </group>
  );
}

// Core component (rotating icosahedron)
function Core({ sceneState }: { sceneState: SceneState }) {
  const coreRef = useRef<THREE.Group>(null);
  const coreGeometry = useMemo(() => new THREE.IcosahedronGeometry(25, 3), []);
  const wireGeometry = useMemo(() => new THREE.WireframeGeometry(coreGeometry), [coreGeometry]);

  useFrame(() => {
    if (coreRef.current) {
      coreRef.current.rotation.x += 0.0005;
      coreRef.current.rotation.y += 0.0008;

      // Pulse scale based on scene progress
      const pulseScale = 1 + Math.sin(Date.now() * 0.001 + sceneState.progress * Math.PI) * 0.1;
      coreRef.current.scale.set(pulseScale, pulseScale, pulseScale);
    }
  });

  return (
    <group ref={coreRef}>
      <lineSegments geometry={wireGeometry}>
        <lineBasicMaterial color={0x60a5fa} linewidth={2} />
      </lineSegments>

      <mesh geometry={coreGeometry}>
        <meshBasicMaterial color={0x60a5fa} transparent opacity={0.1} blending={THREE.AdditiveBlending} />
      </mesh>
    </group>
  );
}

// Pathway component
function Pathway({ from, to, color, intensity }: { from: THREE.Vector3; to: THREE.Vector3; color: number; intensity: number }) {
  const points = useMemo(() => [from, to], [from, to]);

  return (
    <Line
      points={points}
      color={color}
      lineWidth={1}
      transparent
      opacity={0.3 + intensity * 0.5}
    />
  );
}

// Particle system
function ParticleSystem({ sceneState }: { sceneState: SceneState }) {
  const pointsRef = useRef<THREE.Points>(null);
  const particleCountRef = useRef(200);

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCountRef.current * 3);
    const colors = new Float32Array(particleCountRef.current * 3);

    for (let i = 0; i < particleCountRef.current; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 300;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 300;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 300;

      colors[i * 3] = Math.random();
      colors[i * 3 + 1] = Math.random();
      colors[i * 3 + 2] = Math.random();
    }

    const posAttr = new THREE.BufferAttribute(positions, 3);
    const colorAttr = new THREE.BufferAttribute(colors, 3);
    geo.setAttribute('position', posAttr);
    geo.setAttribute('color', colorAttr);

    return geo;
  }, []);

  useFrame(() => {
    if (pointsRef.current && pointsRef.current.geometry) {
      const positions = pointsRef.current.geometry.attributes.position.array as Float32Array;

      for (let i = 0; i < particleCountRef.current; i++) {
        positions[i * 3] += (Math.random() - 0.5) * 0.5;
        positions[i * 3 + 1] += (Math.random() - 0.5) * 0.5;
        positions[i * 3 + 2] += (Math.random() - 0.5) * 0.5;
      }

      pointsRef.current.geometry.attributes.position.needsUpdate = true;
    }
  });

  return (
    <points ref={pointsRef} geometry={geometry}>
      <pointsMaterial size={3} vertexColors transparent sizeAttenuation blending={THREE.AdditiveBlending} />
    </points>
  );
}

// Main scene component
function Scene({ sceneState }: { sceneState: SceneState }) {
  const { camera } = useThree();
  const autoOrbitRef = useRef(0);

  const towerPositions = useMemo(
    () => ({
      finance: new THREE.Vector3(CONFIG.towerDistance, 0, CONFIG.towerDistance),
      social: new THREE.Vector3(-CONFIG.towerDistance, 0, CONFIG.towerDistance),
      customer: new THREE.Vector3(-CONFIG.towerDistance, 0, -CONFIG.towerDistance),
      management: new THREE.Vector3(CONFIG.towerDistance, 0, -CONFIG.towerDistance)
    }),
    []
  );

  useFrame(() => {
    // Auto-orbit camera
    autoOrbitRef.current += 0.0003;
    const baseDistance = 200;
    const orbitX = Math.cos(autoOrbitRef.current) * baseDistance;
    const orbitZ = Math.sin(autoOrbitRef.current) * baseDistance;

    // Interpolate camera based on scroll progress
    const targetY = 80 + sceneState.progress * 40;
    camera.position.lerp(new THREE.Vector3(orbitX, targetY, orbitZ), 0.05);
    camera.lookAt(0, 0, 0);
  });

  return (
    <>
      <color attach="background" args={[0x05070f]} />
      <fog attach="fog" args={[0x05070f, 300, 1000]} />

      {/* Lights */}
      <ambientLight intensity={0.5} />
      <pointLight position={[100, 100, 100]} intensity={1} />

      {/* Core */}
      <Core sceneState={sceneState} />

      {/* Towers */}
      {Object.entries(towerPositions).map(([key, pos]) => (
        <Tower
          key={key}
          position={pos}
          color={CONFIG.domains[key as keyof typeof CONFIG.domains].color}
          active={sceneState.sceneIndex === Object.keys(towerPositions).indexOf(key)}
        />
      ))}

      {/* Pathways */}
      {Object.entries(towerPositions).map(([key, pos], idx) => (
        <Pathway
          key={`pathway-${key}`}
          from={pos}
          to={new THREE.Vector3(0, 0, 0)}
          color={CONFIG.domains[key as keyof typeof CONFIG.domains].color}
          intensity={sceneState.progress}
        />
      ))}

      {/* Particles */}
      <ParticleSystem sceneState={sceneState} />
    </>
  );
}

// Main NeuralCity component
export function NeuralCity({ sceneState }: { sceneState: SceneState }) {
  return (
    <Canvas
      camera={{ position: [200, 80, 200], fov: 75 }}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100vh',
        zIndex: 0
      }}
      gl={{ antialias: true, alpha: true }}
    >
      <Scene sceneState={sceneState} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.2} luminanceSmoothing={0.9} height={300} />
      </EffectComposer>
    </Canvas>
  );
}
