import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Icosahedron, Line, Html } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import * as THREE from 'three';
import { EnhancedSceneState } from '@/hooks/useScrollytellingStateEnhanced';
import { DOMAIN_COLORS } from '@/const';

type SceneState = EnhancedSceneState;

const CONFIG = {
  domains: {
    customer: { color: DOMAIN_COLORS.customer.hex, name: 'Detection' },
    social: { color: DOMAIN_COLORS.social.hex, name: 'Explainability' },
    finance: { color: DOMAIN_COLORS.finance.hex, name: 'Fairness' },
    management: { color: DOMAIN_COLORS.management.hex, name: 'Drift' }
  },
  towerDistance: 120,
  coreScale: 1
};

// 3D holographic glyph neuron structures around active towers (Scene 4)
function CCNeuronGlyphs({ active }: { active: boolean }) {
  const groupRef = useRef<THREE.Group>(null);
  
  useFrame((state) => {
    if (groupRef.current) {
      const targetScale = active ? 1 : 0.01;
      groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
      groupRef.current.rotation.y = state.clock.getElapsedTime() * 0.5;
    }
  });

  return (
    <group ref={groupRef} position={[0, 45, 0]}>
      {Array.from({ length: 4 }).map((_, i) => (
        <mesh key={i} position={[Math.sin(i * 1.5) * 6, Math.cos(i * 1.5) * 6, Math.sin(i * 2) * 4]}>
          <sphereGeometry args={[1.5, 8, 8]} />
          <meshBasicMaterial color={0xfbbf24} wireframe />
        </mesh>
      ))}
    </group>
  );
}

function SMWaveGlyphs({ active }: { active: boolean }) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (groupRef.current) {
      const targetScale = active ? 1 : 0.01;
      groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
      groupRef.current.rotation.x = state.clock.getElapsedTime() * 0.4;
    }
  });

  const wavePoints = useMemo(() => {
    const pts = [];
    for (let x = -8; x <= 8; x += 0.5) {
      pts.push(new THREE.Vector3(x, Math.sin(x * 0.8) * 3, 0));
    }
    return pts;
  }, []);

  return (
    <group ref={groupRef} position={[0, 45, 0]}>
      <Line points={wavePoints} color={0xc026d3} lineWidth={3.0} />
    </group>
  );
}

function FISpikeGlyphs({ active }: { active: boolean }) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (groupRef.current) {
      const targetScale = active ? 1 : 0.01;
      groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
      groupRef.current.rotation.z = state.clock.getElapsedTime() * 0.6;
    }
  });

  return (
    <group ref={groupRef} position={[0, 45, 0]}>
      {Array.from({ length: 3 }).map((_, i) => (
        <Line key={i} points={[new THREE.Vector3(0, 0, 0), new THREE.Vector3((i - 1) * 4, 8, 0)]} color={0x2dd4bf} lineWidth={3.5} />
      ))}
    </group>
  );
}

function MGRingGlyphs({ active }: { active: boolean }) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (groupRef.current) {
      const targetScale = active ? 1 : 0.01;
      groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
      groupRef.current.rotation.y = state.clock.getElapsedTime() * 0.5;
    }
  });

  return (
    <group ref={groupRef} position={[0, 45, 0]}>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[4, 4.4, 32]} />
        <meshBasicMaterial color={0x60a5fa} side={THREE.DoubleSide} wireframe />
      </mesh>
      <mesh rotation={[0, Math.PI / 2, 0]}>
        <ringGeometry args={[6, 6.4, 32]} />
        <meshBasicMaterial color={0x60a5fa} side={THREE.DoubleSide} wireframe />
      </mesh>
    </group>
  );
}

function TowerEnhanced({ position, color, sceneState, towerIndex }: { position: THREE.Vector3; color: number; sceneState: SceneState; towerIndex: number }) {
  const groupRef = useRef<THREE.Group>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const sphereRef = useRef<THREE.Mesh>(null);
  const lineMatRef = useRef<THREE.LineBasicMaterial>(null);
  const wireGeometry = useMemo(() => new THREE.WireframeGeometry(new THREE.BoxGeometry(30, 60, 30)), []);

  useFrame(() => {
    if (groupRef.current && glowRef.current) {
      let targetScale = 1;
      let opacity = 0.25;

      if (sceneState.sceneIndex === 1) {
        // Scene 2: Problem
        targetScale = 1 - sceneState.problemTowerDim * 0.18;
        opacity = 0.25 * (1 - sceneState.problemTowerDim);
      } else if (sceneState.sceneIndex === 3) {
        // Scene 4: Nodes active zooming
        targetScale = sceneState.agentsTowerBrightness[towerIndex] > 0.5 ? 1.25 : 0.8;
        opacity = sceneState.agentsTowerBrightness[towerIndex] * 0.45;
      }

      const finalScale = targetScale;
      groupRef.current.scale.lerp(new THREE.Vector3(finalScale, finalScale, finalScale), 0.1);
      (glowRef.current.material as THREE.MeshBasicMaterial).opacity = opacity;

      if (sphereRef.current && sphereRef.current.material) {
        (sphereRef.current.material as THREE.MeshBasicMaterial).opacity = 0.4;
      }
      if (lineMatRef.current) {
        lineMatRef.current.opacity = 0.6;
      }
    }
  });

  return (
    <group ref={groupRef} position={position}>
      {/* 3D HTML Tower labels for naming reference */}
      <Html distanceFactor={80} position={[0, 35, 0]} center>
        <div style={{
          fontFamily: 'JetBrains Mono, monospace',
          textTransform: 'uppercase',
          fontSize: '11px',
          fontWeight: 'bold',
          color: '#' + color.toString(16).padStart(6, '0'),
          whiteSpace: 'nowrap',
          background: 'rgba(3, 7, 18, 0.85)',
          padding: '4px 10px',
          borderRadius: '6px',
          border: `1px solid rgba(255, 255, 255, 0.1)`,
          pointerEvents: 'none',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          opacity: 1,
          transition: 'opacity 0.3s ease'
        }}>
          {towerIndex === 0 && 'DETECTION'}
          {towerIndex === 1 && 'EXPLAINABILITY'}
          {towerIndex === 2 && 'FAIRNESS'}
          {towerIndex === 3 && 'DRIFT'}
        </div>
      </Html>

      <lineSegments geometry={wireGeometry}>
        <lineBasicMaterial ref={lineMatRef} color={color} linewidth={2} transparent opacity={0.6} />
      </lineSegments>
      <mesh ref={glowRef}>
        <boxGeometry args={[32, 62, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.15} blending={THREE.AdditiveBlending} />
      </mesh>
      <mesh ref={sphereRef} position={[0, 35, 0]}>
        <sphereGeometry args={[8, 16, 16]} />
        <meshBasicMaterial color={color} transparent opacity={0.4} blending={THREE.AdditiveBlending} />
      </mesh>

      {/* Synergize Scene 4 Node glyph shapes */}
      {towerIndex === 0 && <CCNeuronGlyphs active={sceneState.sceneIndex === 3 && sceneState.agentsTowerFocusIndex === 0} />}
      {towerIndex === 1 && <SMWaveGlyphs active={sceneState.sceneIndex === 3 && sceneState.agentsTowerFocusIndex === 1} />}
      {towerIndex === 2 && <FISpikeGlyphs active={sceneState.sceneIndex === 3 && sceneState.agentsTowerFocusIndex === 2} />}
      {towerIndex === 3 && <MGRingGlyphs active={sceneState.sceneIndex === 3 && sceneState.agentsTowerFocusIndex === 3} />}
    </group>
  );
}

function CoreEnhanced({ sceneState }: { sceneState: SceneState }) {
  const coreRef = useRef<THREE.Group>(null);
  const coreMeshRef = useRef<THREE.Mesh>(null);
  const lineMatRef = useRef<THREE.LineBasicMaterial>(null);
  const coreGeometry = useMemo(() => new THREE.IcosahedronGeometry(25, 3), []);
  const wireGeometry = useMemo(() => new THREE.WireframeGeometry(coreGeometry), [coreGeometry]);

  useFrame(() => {
    if (coreRef.current && coreMeshRef.current) {
      let rotationSpeed = 0.0008;
      let brightness = 0.3;

      if (sceneState.sceneIndex === 2) {
        rotationSpeed = 0.0008 + sceneState.solutionCoreRotationSpeed * 0.0005;
        brightness = sceneState.solutionCoreBrightness;
      } else if (sceneState.sceneIndex === 3 || sceneState.sceneIndex === 4) {
        brightness = 0.3 + sceneState.differentiatorCoreFlash * 0.55;
      } else if (sceneState.sceneIndex === 5) {
        rotationSpeed = 0.0008 * sceneState.ctaCoreRotationSpeed;
        brightness = 0.3 + sceneState.ctaPathwaysLit * 0.4;
      }

      // Safe zone opacity in Hero scene
      let safeZoneOpacity = 1.0;
      if (sceneState.sceneIndex === 0) {
        safeZoneOpacity = Math.min(1.0, Math.max(0.0, (sceneState.sceneProgress - 0.2) / 0.8));
      }

      const coreScale = CONFIG.coreScale * (0.01 + 0.99 * safeZoneOpacity);
      coreRef.current.scale.set(coreScale, coreScale, coreScale);

      coreRef.current.rotation.x += 0.0005;
      coreRef.current.rotation.y += rotationSpeed;
      (coreMeshRef.current.material as THREE.MeshBasicMaterial).opacity = brightness * safeZoneOpacity;
      if (lineMatRef.current) {
        lineMatRef.current.opacity = 0.6 * safeZoneOpacity;
      }
    }
  });

  return (
    <group ref={coreRef}>
      <lineSegments geometry={wireGeometry}>
        <lineBasicMaterial ref={lineMatRef} color={0x60a5fa} linewidth={2} transparent opacity={0.6} />
      </lineSegments>
      <mesh ref={coreMeshRef} geometry={coreGeometry}>
        <meshBasicMaterial color={0x60a5fa} transparent opacity={0.15} blending={THREE.AdditiveBlending} />
      </mesh>
    </group>
  );
}

function PathwayEnhanced({ from, to, color, sceneState, towerIndex }: { from: THREE.Vector3; to: THREE.Vector3; color: number; sceneState: SceneState; towerIndex: number }) {
  const points = useMemo(() => [from, to], [from, to]);
  let opacity = 0.3;

  if (sceneState.sceneIndex === 1) {
    opacity = 0.3 * (1 - sceneState.problemTowerDim);
  } else if (sceneState.sceneIndex === 2) {
    opacity = sceneState.solutionPathwayIgnition[towerIndex] || 0.1;
  } else if (sceneState.sceneIndex === 3 || sceneState.sceneIndex === 4) {
    opacity = 0.35 + sceneState.differentiatorPathwayPulse * 0.3;
  } else if (sceneState.sceneIndex === 5) {
    opacity = sceneState.ctaPathwaysLit * 0.65;
  }

  // Safe zone opacity in Hero scene
  if (sceneState.sceneIndex === 0) {
    const safeZoneOpacity = Math.min(1.0, Math.max(0.0, (sceneState.sceneProgress - 0.2) / 0.8));
    opacity = opacity * safeZoneOpacity;
  }

  return <Line points={points} color={color} lineWidth={1.5} transparent opacity={opacity} />;
}

function ParticleSystemEnhanced({ sceneState }: { sceneState: SceneState }) {
  const pointsRef = useRef<THREE.Points>(null);
  const particleCountRef = useRef(200);
  const particleDataRef = useRef<Array<{ x: number; y: number; z: number; vx: number; vy: number; vz: number }>>([]);
  const { camera } = useThree();
  const tempV = useMemo(() => new THREE.Vector3(), []);

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCountRef.current * 3);
    const colors = new Float32Array(particleCountRef.current * 3);

    particleDataRef.current = [];

    for (let i = 0; i < particleCountRef.current; i++) {
      const x = (Math.random() - 0.5) * 300;
      const y = (Math.random() - 0.5) * 300;
      const z = (Math.random() - 0.5) * 300;

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      const colorChoice = Math.random();
      if (colorChoice < 0.25) {
        // Teal: original
        colors[i * 3] = 0.18;
        colors[i * 3 + 1] = 0.83;
        colors[i * 3 + 2] = 0.75;
      } else if (colorChoice < 0.5) {
        // Pink: original
        colors[i * 3] = 0.75;
        colors[i * 3 + 1] = 0.15;
        colors[i * 3 + 2] = 0.82;
      } else if (colorChoice < 0.75) {
        // Yellow/Amber: slightly desaturated warm gold to protect readability
        colors[i * 3] = 0.65;
        colors[i * 3 + 1] = 0.52;
        colors[i * 3 + 2] = 0.12;
      } else {
        // Blue: original
        colors[i * 3] = 0.38;
        colors[i * 3 + 1] = 0.65;
        colors[i * 3 + 2] = 0.98;
      }

      particleDataRef.current.push({
        x,
        y,
        z,
        vx: (Math.random() - 0.5) * 0.02,
        vy: (Math.random() - 0.5) * 0.02,
        vz: (Math.random() - 0.5) * 0.02
      });
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    return geo;
  }, []);

  useFrame(() => {
    if (pointsRef.current && pointsRef.current.geometry) {
      const positions = pointsRef.current.geometry.attributes.position.array as Float32Array;
      let speed = 0.5;
      if (sceneState.sceneIndex === 1) {
        speed = 0.05;
      } else if (sceneState.sceneIndex === 2) {
        speed = 1.2;
      }

      particleDataRef.current.forEach((p, i) => {
        p.x += p.vx * speed;
        p.y += p.vy * speed;
        p.z += p.vz * speed;

        if (Math.abs(p.x) > 200) p.vx *= -1;
        if (Math.abs(p.y) > 150) p.vy *= -1;
        if (Math.abs(p.z) > 200) p.vz *= -1;

        let finalX = p.x;
        let finalY = p.y;
        let finalZ = p.z;

        // Apply narrow safe zone exclusion to background particles in the Hero scene
        if (sceneState.sceneIndex === 0) {
          tempV.set(p.x, p.y, p.z).project(camera);
          
          const inFront = tempV.z > -1 && tempV.z < 1;
          const inSafeZone = inFront && Math.abs(tempV.x) < 0.35 && Math.abs(tempV.y) < 0.22;
          
          if (inSafeZone) {
            // Push particle far back behind the fog to exclude it visually
            finalZ = -2000;
          }
        }

        positions[i * 3] = finalX;
        positions[i * 3 + 1] = finalY;
        positions[i * 3 + 2] = finalZ;
      });

      pointsRef.current.geometry.attributes.position.needsUpdate = true;
      (pointsRef.current.material as THREE.PointsMaterial).opacity = 0.85;
    }
  });

  return (
    <points ref={pointsRef} geometry={geometry}>
      <pointsMaterial size={2.5} vertexColors transparent opacity={0.85} sizeAttenuation blending={THREE.AdditiveBlending} />
    </points>
  );
}

function SceneEnhanced({ sceneState }: { sceneState: SceneState }) {
  const { camera } = useThree();
  const autoOrbitRef = useRef(0);

  const towerPositions = useMemo(
    () => ({
      customer: new THREE.Vector3(-CONFIG.towerDistance, 0, -CONFIG.towerDistance),
      social: new THREE.Vector3(-CONFIG.towerDistance, 0, CONFIG.towerDistance),
      finance: new THREE.Vector3(CONFIG.towerDistance, 0, CONFIG.towerDistance),
      management: new THREE.Vector3(CONFIG.towerDistance, 0, -CONFIG.towerDistance)
    }),
    []
  );

  useFrame(() => {
    autoOrbitRef.current += 0.0003;
    const baseDistance = 200;
    const orbitX = Math.cos(autoOrbitRef.current) * baseDistance;
    const orbitZ = Math.sin(autoOrbitRef.current) * baseDistance;

    let targetX = orbitX;
    let targetY = 80;
    let targetZ = orbitZ;

    if (sceneState.sceneIndex === 1) {
      targetY = 40;
    } else if (sceneState.sceneIndex === 3) {
      const focusedTower = Object.values(towerPositions)[sceneState.agentsTowerFocusIndex] || towerPositions.customer;
      targetX = focusedTower.x * 0.8;
      targetY = 100;
      targetZ = focusedTower.z * 0.8;
    } else if (sceneState.sceneIndex === 5) {
      targetX = orbitX * (1 - sceneState.ctaCameraTowardCore);
      targetY = 80 - sceneState.ctaCameraTowardCore * 75;
      targetZ = orbitZ * (1 - sceneState.ctaCameraTowardCore);
    }

    camera.position.lerp(new THREE.Vector3(targetX, targetY, targetZ), 0.04);
    camera.lookAt(0, 0, 0);
  });

  return (
    <>
      <fog attach="fog" args={[0x030712, 400, 1200]} />

      <ambientLight intensity={0.6} />
      <pointLight position={[100, 100, 100]} intensity={1.2} />
      <pointLight position={[-100, 50, -100]} intensity={0.6} color={0x60a5fa} />

      <CoreEnhanced sceneState={sceneState} />

      {Object.entries(towerPositions).map(([key, pos], idx) => (
        <TowerEnhanced key={key} position={pos} color={CONFIG.domains[key as keyof typeof CONFIG.domains].color} sceneState={sceneState} towerIndex={idx} />
      ))}

      {Object.entries(towerPositions).map(([key, pos], idx) => (
        <PathwayEnhanced key={`pathway-${key}`} from={pos} to={new THREE.Vector3(0, 0, 0)} color={CONFIG.domains[key as keyof typeof CONFIG.domains].color} sceneState={sceneState} towerIndex={idx} />
      ))}

      <ParticleSystemEnhanced sceneState={sceneState} />
    </>
  );
}

export function NeuralCityEnhanced({ sceneState }: { sceneState: SceneState }) {
  return (
    <Canvas camera={{ position: [200, 80, 200], fov: 75 }} style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100vh', zIndex: 0 }} gl={{ antialias: true, alpha: true }}>
      <SceneEnhanced sceneState={sceneState} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.2} luminanceSmoothing={0.9} height={300} />
      </EffectComposer>
    </Canvas>
  );
}
export default NeuralCityEnhanced;
