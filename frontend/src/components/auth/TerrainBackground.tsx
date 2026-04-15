import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

function TerrainMesh() {
  const meshRef = useRef<THREE.Mesh>(null);
  const timeRef = useRef(0);

  // Create a plane geometry with enough vertices for a visible terrain grid
  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(30, 30, 80, 80);
    geo.rotateX(-Math.PI * 0.55); // Tilt to show terrain perspective
    return geo;
  }, []);

  // Animate the terrain vertices to undulate like a living topographic map
  useFrame((_, delta) => {
    if (!meshRef.current) return;
    timeRef.current += delta * 0.4;
    const t = timeRef.current;
    const pos = meshRef.current.geometry.attributes.position!;
    const arr = pos.array as Float32Array;

    for (let i = 0; i < pos.count; i++) {
      const x = arr[i * 3]!;
      const y = arr[i * 3 + 1]!;
      // Layer multiple sine waves for organic-feeling terrain
      arr[i * 3 + 2] =
        Math.sin(x * 0.4 + t) * 0.6 +
        Math.sin(y * 0.3 + t * 0.7) * 0.4 +
        Math.sin((x + y) * 0.2 + t * 0.5) * 0.3;
    }
    pos.needsUpdate = true;
  });

  return (
    <mesh ref={meshRef} geometry={geometry} position={[0, -2, 0]}>
      <meshBasicMaterial
        wireframe
        color="#0AEFFF"
        transparent
        opacity={0.12}
      />
    </mesh>
  );
}

function GlowOrb() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = clock.getElapsedTime();
    meshRef.current.position.y = Math.sin(t * 0.5) * 0.5 + 1;
    meshRef.current.position.x = Math.sin(t * 0.3) * 2;
  });

  return (
    <mesh ref={meshRef} position={[0, 1, -5]}>
      <sphereGeometry args={[0.3, 16, 16]} />
      <meshBasicMaterial color="#0AEFFF" transparent opacity={0.25} />
    </mesh>
  );
}

function SecondaryOrb() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = clock.getElapsedTime();
    meshRef.current.position.y = Math.cos(t * 0.4) * 0.8 + 0.5;
    meshRef.current.position.x = Math.cos(t * 0.25) * 3;
    meshRef.current.position.z = Math.sin(t * 0.15) * 2 - 4;
  });

  return (
    <mesh ref={meshRef} position={[2, 0.5, -4]}>
      <sphereGeometry args={[0.2, 12, 12]} />
      <meshBasicMaterial color="#3B82F6" transparent opacity={0.2} />
    </mesh>
  );
}

export default function TerrainBackground() {
  return (
    <div className="fixed inset-0 z-0">
      {/* Gradient overlay for depth — fades terrain into darkness at edges */}
      <div
        className="absolute inset-0 z-10 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 70% 60% at 50% 55%, transparent 30%, #060B14 80%)",
        }}
      />
      <Canvas
        camera={{ position: [0, 5, 12], fov: 45 }}
        style={{ background: "#060B14" }}
        gl={{ antialias: true, alpha: false }}
      >
        <TerrainMesh />
        <GlowOrb />
        <SecondaryOrb />
        {/* Subtle ambient light — keeps the wireframe visible */}
        <ambientLight intensity={0.5} />
      </Canvas>
    </div>
  );
}
