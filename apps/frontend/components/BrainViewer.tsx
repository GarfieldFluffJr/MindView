"use client";

import { Suspense, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF, Center, Environment } from "@react-three/drei";
import * as THREE from "three";

interface BrainModelProps {
  url: string;
}

function BrainModel({ url }: BrainModelProps) {
  const { scene } = useGLTF(url);

  useEffect(() => {
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const hasVertexColors = child.geometry.attributes.color !== undefined;

        child.material = new THREE.MeshPhysicalMaterial({
          vertexColors: hasVertexColors,
          color: hasVertexColors ? 0xffffff : 0x88ccff,
          transparent: true,
          opacity: 0.7,
          side: THREE.DoubleSide,
          depthWrite: false,
          roughness: 0.4,
          metalness: 0.1,
          clearcoat: 0.3,
        });
      }
    });
  }, [scene]);

  return (
    <Center>
      <primitive object={scene} />
    </Center>
  );
}

function LoadingSpinner() {
  return (
    <mesh>
      <sphereGeometry args={[0.5, 16, 16]} />
      <meshStandardMaterial color="#4299e1" wireframe />
    </mesh>
  );
}

interface BrainViewerProps {
  meshUrl: string;
  onReset?: () => void;
}

export default function BrainViewer({ meshUrl, onReset }: BrainViewerProps) {
  return (
    <div className="relative w-full bg-gray-900 rounded-xl overflow-hidden" style={{ height: "70vh" }}>
      <Canvas
        camera={{ position: [0, 0, 200], fov: 50 }}
        style={{ width: "100%", height: "100%" }}
        gl={{ alpha: false }}
      >
        <color attach="background" args={["#111827"]} />
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        <directionalLight position={[-10, -10, -5]} intensity={0.5} />
        <directionalLight position={[0, 10, -10]} intensity={0.3} />
        <Suspense fallback={<LoadingSpinner />}>
          <BrainModel url={meshUrl} />
          <Environment preset="studio" />
        </Suspense>
        <OrbitControls
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
          minDistance={50}
          maxDistance={500}
        />
      </Canvas>
      <div className="absolute bottom-4 left-4 text-white text-sm bg-black/50 px-3 py-2 rounded-lg">
        <p>Drag to rotate | Scroll to zoom | Shift+drag to pan</p>
      </div>
      {onReset && (
        <button
          onClick={onReset}
          className="absolute top-4 right-4 bg-white/90 hover:bg-white text-gray-800 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          Upload New Scan
        </button>
      )}
    </div>
  );
}
