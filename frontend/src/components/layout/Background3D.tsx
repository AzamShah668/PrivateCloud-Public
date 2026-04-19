import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

function RotatingGlobe() {
  const groupRef = useRef<THREE.Group>(null);
  const ring1Ref = useRef<THREE.Mesh>(null);
  const ring2Ref = useRef<THREE.Mesh>(null);
  const ring3Ref = useRef<THREE.Mesh>(null);

  // Very high detail geodesic dome for a perfectly round, techy triangulation
  const geo = useMemo(() => new THREE.IcosahedronGeometry(4.2, 12), []);
  // Lower detail for the visible wireframe so the lines aren't too dense
  const wireframeGeo = useMemo(() => new THREE.IcosahedronGeometry(4.22, 6), []);

  useFrame((_state, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.04;
      groupRef.current.rotation.x += delta * 0.015;
    }
    if (ring1Ref.current) ring1Ref.current.rotation.x -= delta * 0.05;
    if (ring2Ref.current) ring2Ref.current.rotation.y += delta * 0.03;
    if (ring3Ref.current) ring3Ref.current.rotation.z -= delta * 0.08;
  });

  return (
    // Move the globe further to the right and push it back slightly so it doesn't overlap the form UI
    <group position={[8, -1, -8]}>
      <group ref={groupRef}>
        {/* Solid Inner Sphere - blocks background elements */}
        <mesh geometry={geo}>
          <meshBasicMaterial 
            color="#020617" 
            transparent={false}
            depthWrite={true}
          />
        </mesh>
        
        {/* Outer Triangulated Wireframe */}
        <mesh geometry={wireframeGeo}>
          <meshBasicMaterial 
            color="#0AEFFF" 
            wireframe 
            transparent 
            opacity={0.15} 
            blending={THREE.AdditiveBlending} 
            depthWrite={false}
          />
        </mesh>

        {/* Glowing Nodes at vertices of the triangulated wireframe */}
        <points geometry={wireframeGeo}>
          <pointsMaterial
            color="#3B82F6"
            size={0.08}
            transparent
            opacity={0.8}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </points>

        {/* Subtle Inner Glow */}
        <mesh geometry={geo}>
          <meshBasicMaterial 
            color="#0AEFFF" 
            transparent 
            opacity={0.04} 
            blending={THREE.AdditiveBlending} 
            depthWrite={false}
          />
        </mesh>
      </group>

      {/* Orbiting Orbital Ring 1 */}
      <mesh ref={ring1Ref} rotation={[Math.PI / 3, 0, 0]}>
        <torusGeometry args={[5.8, 0.015, 16, 100]} />
        <meshBasicMaterial 
          color="#3B82F6" 
          transparent 
          opacity={0.6} 
          blending={THREE.AdditiveBlending} 
        />
      </mesh>
      
      {/* Orbiting Orbital Ring 2 */}
      <mesh ref={ring2Ref} rotation={[-Math.PI / 4, Math.PI / 6, 0]}>
        <torusGeometry args={[6.5, 0.015, 16, 100]} />
        <meshBasicMaterial 
          color="#D946EF" 
          transparent 
          opacity={0.4} 
          blending={THREE.AdditiveBlending} 
        />
      </mesh>
      
      {/* Orbiting Orbital Ring 3 (Inner, fast) */}
      <mesh ref={ring3Ref} rotation={[0, Math.PI / 4, 0]}>
        <torusGeometry args={[4.8, 0.01, 16, 100]} />
        <meshBasicMaterial 
          color="#0AEFFF" 
          transparent 
          opacity={0.8} 
          blending={THREE.AdditiveBlending} 
        />
      </mesh>
    </group>
  );
}

function ParticleField() {
  const pointsRef = useRef<THREE.Points>(null);
  
  const count = 300;
  const [positions, sizes] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const sz = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      // distribute randomly in a wide area, pushing them back
      pos[i * 3] = (Math.random() - 0.5) * 30;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 20;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 15 - 8;
      sz[i] = Math.random() * 1.5;
    }
    return [pos, sz];
  }, []);

  useFrame((state, delta) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y -= delta * 0.01;
      pointsRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.15) * 0.3;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
        <bufferAttribute
          attach="attributes-size"
          args={[sizes, 1]}
        />
      </bufferGeometry>
      <pointsMaterial 
        size={0.05} 
        color="#D946EF" 
        transparent 
        opacity={0.2} 
        sizeAttenuation 
        blending={THREE.AdditiveBlending} 
        depthWrite={false}
      />
    </points>
  );
}

export default function Background3D() {
  return (
    <div className="fixed inset-0 pointer-events-none z-0">
      <Canvas camera={{ position: [0, 0, 5], fov: 60 }} gl={{ alpha: true, antialias: true }}>
        {/* Add fog so the back of the globe fades smoothly into the background color */}
        <fog attach="fog" args={['#060B14', 5, 20]} />
        <RotatingGlobe />
        <ParticleField />
      </Canvas>
    </div>
  );
}
