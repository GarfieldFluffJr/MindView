"use client";

import { Suspense, useEffect, useState, useMemo, useRef } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { TrackballControls, useGLTF, Center, Environment } from "@react-three/drei";
import * as THREE from "three";

interface RegionState {
  visible: boolean;
  opacity: number;
}

interface BrainModelProps {
  url: string;
  clippingEnabled: boolean;
  clippingPosition: number;
  regionStates: Record<string, RegionState>;
}

function ClippingSetup({ enabled }: { enabled: boolean }) {
  const { gl } = useThree();

  useEffect(() => {
    gl.localClippingEnabled = enabled;
  }, [gl, enabled]);

  return null;
}

function BrainModel({ url, clippingEnabled, clippingPosition, regionStates }: BrainModelProps) {
  const { scene } = useGLTF(url);
  const materialsRef = useRef<Map<string, THREE.MeshPhongMaterial>>(new Map());

  // Clone the scene to avoid issues with cached/shared scene objects
  const clonedScene = useMemo(() => {
    return scene.clone(true);
  }, [scene]);

  const clippingPlane = useMemo(() => {
    return new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  }, []);

  useEffect(() => {
    clippingPlane.constant = clippingPosition;
  }, [clippingPlane, clippingPosition]);

  // Initial setup - create materials and extract vertex colors
  useEffect(() => {
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const meshName = child.name || "unknown";

        // Check for vertex colors
        const hasVertexColors = child.geometry.attributes.color !== undefined;

        // Compute normals for proper lighting
        if (child.geometry) {
          child.geometry.computeVertexNormals();
        }

        // Create material with vertex colors if available
        const material = new THREE.MeshPhongMaterial({
          vertexColors: hasVertexColors,
          color: hasVertexColors ? 0xffffff : 0xcccccc,
          specular: 0x444444,
          shininess: 20,
          flatShading: false,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 1.0,
          depthWrite: true,
          clippingPlanes: clippingEnabled ? [clippingPlane] : [],
          clipShadows: true,
        });

        // Fix backface lighting by flipping normals when viewing from behind
        material.onBeforeCompile = (shader) => {
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <normal_fragment_maps>',
            `#include <normal_fragment_maps>
             if (!gl_FrontFacing) normal = -normal;`
          );
        };

        child.material = material;
        materialsRef.current.set(meshName, material);
      }
    });

    // Cleanup
    return () => {
      materialsRef.current.forEach((material) => {
        material.dispose();
      });
      materialsRef.current.clear();
    };
  }, [scene, clippingPlane]); // Only run once on mount

  // Update clipping planes when clipping state changes
  useEffect(() => {
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshPhongMaterial) {
        child.material.clippingPlanes = clippingEnabled ? [clippingPlane] : [];
        child.material.needsUpdate = true;
      }
    });
  }, [clonedScene, clippingEnabled, clippingPlane]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clonedScene.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry?.dispose();
          if (child.material instanceof THREE.Material) {
            child.material.dispose();
          }
        }
      });
    };
  }, [clonedScene]);

  // Update visibility and opacity based on regionStates
  useEffect(() => {
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const meshName = child.name || "unknown";
        const state = regionStates[meshName];

        if (state) {
          child.visible = state.visible;
          if (child.material instanceof THREE.MeshPhongMaterial) {
            child.material.opacity = state.opacity;
            child.material.transparent = state.opacity < 1.0;
            child.material.depthWrite = true;
            child.material.needsUpdate = true;
          }
        }
      }
    });
  }, [scene, regionStates]);

  return (
    <>
      <Center>
        <primitive object={clonedScene} />
      </Center>
      {clippingEnabled && (
        <mesh
          position={[0, -clippingPosition, 0]}
          rotation={[-Math.PI / 2, 0, 0]}
          renderOrder={-1}
        >
          <planeGeometry args={[300, 300]} />
          <meshBasicMaterial
            color="#aaaaaa"
            transparent
            opacity={0.1}
            side={THREE.DoubleSide}
            depthWrite={false}
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
  regionStates: Record<string, RegionState>;
  onReset?: () => void;
}

export default function BrainViewer({ meshUrl, regionStates, onReset }: BrainViewerProps) {
  const [clippingEnabled, setClippingEnabled] = useState(false);
  const [clippingPosition, setClippingPosition] = useState(100);

  // Clear GLTF cache when URL changes
  useEffect(() => {
    return () => {
      useGLTF.clear();
    };
  }, [meshUrl]);

  return (
    <div className="relative w-full bg-gray-900 rounded-xl overflow-hidden" style={{ height: "70vh" }}>
      <Canvas
        key={meshUrl}
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
            key={meshUrl}
            url={meshUrl}
            clippingEnabled={clippingEnabled}
            clippingPosition={clippingPosition}
            regionStates={regionStates}
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
