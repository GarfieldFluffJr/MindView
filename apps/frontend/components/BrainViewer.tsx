"use client";

import { Suspense, useEffect, useState, useMemo } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { TrackballControls, useGLTF, Center, Environment } from "@react-three/drei";
import * as THREE from "three";

interface BrainModelProps {
  url: string;
  clippingEnabled: boolean;
  clippingPosition: number;
}

function ClippingSetup({ enabled }: { enabled: boolean }) {
  const { gl } = useThree();

  useEffect(() => {
    gl.localClippingEnabled = enabled;
  }, [gl, enabled]);

  return null;
}

function BrainModel({ url, clippingEnabled, clippingPosition }: BrainModelProps) {
  const { scene } = useGLTF(url);

  const clippingPlane = useMemo(() => {
    return new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  }, []);

  useEffect(() => {
    clippingPlane.constant = clippingPosition;
  }, [clippingPlane, clippingPosition]);

  useEffect(() => {
    let meshIndex = 0;
    const opacityLevels = [1.0, 1.0, 1.0, 1.0];

    scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const hasVertexColors = child.geometry.attributes.color !== undefined;
        const layerOpacity = opacityLevels[meshIndex % opacityLevels.length];

        // Compute normals for proper lighting
        if (child.geometry) {
          child.geometry.computeVertexNormals();
        }

        const material = new THREE.MeshPhongMaterial({
          color: 0xcccccc,
          specular: 0x444444,
          shininess: 20,
          flatShading: true,
          side: THREE.DoubleSide,
          depthWrite: true,
          clippingPlanes: clippingEnabled ? [clippingPlane] : [],
          clipShadows: true,
        });

        child.material = material;
        child.renderOrder = meshIndex;
        meshIndex++;
      }
    });
  }, [scene, clippingEnabled, clippingPlane]);

  return (
    <>
      <Center>
        <primitive object={scene} />
      </Center>
      {clippingEnabled && (
        <mesh position={[0, -clippingPosition, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[300, 300]} />
          <meshBasicMaterial
            color="#ff6b6b"
            transparent
            opacity={0.15}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}
    </>
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
  const [clippingEnabled, setClippingEnabled] = useState(false);
  const [clippingPosition, setClippingPosition] = useState(100);

  return (
    <div className="relative w-full bg-gray-900 rounded-xl overflow-hidden" style={{ height: "70vh" }}>
      <Canvas
        camera={{ position: [0, 0, 200], fov: 50 }}
        style={{ width: "100%", height: "100%" }}
        gl={{ alpha: false, sortObjects: true, localClippingEnabled: true }}
      >
        <color attach="background" args={["#0d1117"]} />
        <ambientLight intensity={0.3} />
        {/* Key light - main illumination */}
        <directionalLight position={[50, 80, 50]} intensity={1.5} />
        {/* Fill light - soften shadows */}
        <directionalLight position={[-50, 20, 50]} intensity={0.6} />
        {/* Rim light - highlight edges */}
        <directionalLight position={[0, 30, -80]} intensity={0.8} />
        {/* Bottom fill - show underside detail */}
        <directionalLight position={[0, -50, 30]} intensity={0.4} />
        <ClippingSetup enabled={clippingEnabled} />
        <Suspense fallback={<LoadingSpinner />}>
          <BrainModel
            url={meshUrl}
            clippingEnabled={clippingEnabled}
            clippingPosition={clippingPosition}
          />
          <Environment preset="studio" />
        </Suspense>
        <TrackballControls
          noPan={false}
          noZoom={false}
          noRotate={false}
          minDistance={50}
          maxDistance={500}
          rotateSpeed={2}
          zoomSpeed={1.2}
          panSpeed={0.8}
        />
      </Canvas>

      {/* Clipping Controls Panel */}
      <div className="absolute top-4 right-4 bg-black/70 backdrop-blur-sm rounded-lg p-4 flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <span className="text-white text-sm font-medium">Clip</span>
          <button
            onClick={() => setClippingEnabled(!clippingEnabled)}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              clippingEnabled ? "bg-blue-500" : "bg-gray-600"
            }`}
          >
            <span
              className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform duration-200 ${
                clippingEnabled ? "translate-x-6" : "translate-x-0"
              }`}
            />
          </button>
        </div>

        {onReset && (
          <button
            onClick={onReset}
            className="bg-white/90 hover:bg-white text-gray-800 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Upload New Scan
          </button>
        )}
      </div>

      {/* Vertical Slider */}
      {clippingEnabled && (
        <div className="absolute right-8 top-1/2 -translate-y-1/2 flex flex-col items-center gap-2">
          <span className="text-white text-xs">Top</span>
          <input
            type="range"
            min={-100}
            max={100}
            step={1}
            value={clippingPosition}
            onChange={(e) => setClippingPosition(Number(e.target.value))}
            className="h-48 w-2 bg-gray-600 rounded-lg appearance-none cursor-pointer accent-blue-500"
            style={{
              writingMode: "vertical-lr",
              direction: "rtl",
            }}
          />
          <span className="text-white text-xs">Bottom</span>
          <span className="text-white text-xs mt-1 bg-black/50 px-2 py-1 rounded">{clippingPosition}</span>
        </div>
      )}

      <div className="absolute bottom-4 left-4 text-white text-sm bg-black/50 px-3 py-2 rounded-lg">
        <p>Left-drag to rotate | Scroll to zoom | Right-drag to pan</p>
      </div>
    </div>
  );
}
