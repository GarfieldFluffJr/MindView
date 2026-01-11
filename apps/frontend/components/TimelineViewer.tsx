"use client";

import { Suspense, useEffect, useState, useRef, useMemo, useCallback } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { TrackballControls, useGLTF, Center, Environment } from "@react-three/drei";
import * as THREE from "three";
import { TimelineScanInfo, getTimelineMorphDataUrl } from "@/lib/api";

interface MorphData {
  frame_count: number;
  vertex_count: number;
  timestamps: string[];
  deltas: number[][];
}

interface TimelineBrainModelProps {
  meshUrl: string;
  morphData: MorphData | null;
  timelinePosition: number;
}

function TimelineBrainModel({
  meshUrl,
  morphData,
  timelinePosition,
}: TimelineBrainModelProps) {
  const { scene } = useGLTF(meshUrl);
  const meshRef = useRef<THREE.Mesh | null>(null);
  const basePositions = useRef<Float32Array | null>(null);
  const geometryRef = useRef<THREE.BufferGeometry | null>(null);

  // Initialize mesh reference and store base positions
  useEffect(() => {
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh && child.geometry) {
        meshRef.current = child;
        geometryRef.current = child.geometry;

        // Store original vertex positions
        const positions = child.geometry.attributes.position;
        basePositions.current = new Float32Array(positions.array);

        // Compute normals for proper lighting
        child.geometry.computeVertexNormals();

        // Set up material
        const material = new THREE.MeshPhongMaterial({
          color: 0xcccccc,
          specular: 0x444444,
          shininess: 20,
          flatShading: false,
          side: THREE.DoubleSide,
          depthWrite: true,
        });

        child.material = material;
      }
    });
  }, [scene]);

  // Animate morph based on timeline position
  useFrame(() => {
    if (!meshRef.current || !basePositions.current || !morphData || !geometryRef.current) {
      return;
    }

    const geometry = geometryRef.current;
    const positions = geometry.attributes.position;
    const frameCount = morphData.frame_count;

    // Calculate which frames we're between
    const exactFrame = timelinePosition * (frameCount - 1);
    const frameA = Math.floor(exactFrame);
    const frameB = Math.min(frameA + 1, frameCount - 1);
    const t = exactFrame - frameA; // Interpolation factor (0-1)

    // Get deltas for both frames
    // Frame 0 is the base mesh (no delta), subsequent frames have deltas
    const deltaA = frameA === 0 ? null : morphData.deltas[frameA - 1];
    const deltaB = frameB === 0 ? null : morphData.deltas[frameB - 1];

    // Interpolate vertex positions
    const posArray = positions.array as Float32Array;
    for (let i = 0; i < positions.count; i++) {
      const baseX = basePositions.current[i * 3];
      const baseY = basePositions.current[i * 3 + 1];
      const baseZ = basePositions.current[i * 3 + 2];

      const deltaAX = deltaA ? deltaA[i * 3] : 0;
      const deltaAY = deltaA ? deltaA[i * 3 + 1] : 0;
      const deltaAZ = deltaA ? deltaA[i * 3 + 2] : 0;

      const deltaBX = deltaB ? deltaB[i * 3] : 0;
      const deltaBY = deltaB ? deltaB[i * 3 + 1] : 0;
      const deltaBZ = deltaB ? deltaB[i * 3 + 2] : 0;

      // Linear interpolation between delta A and delta B
      const dx = deltaAX + t * (deltaBX - deltaAX);
      const dy = deltaAY + t * (deltaBY - deltaAY);
      const dz = deltaAZ + t * (deltaBZ - deltaAZ);

      posArray[i * 3] = baseX + dx;
      posArray[i * 3 + 1] = baseY + dy;
      posArray[i * 3 + 2] = baseZ + dz;
    }

    positions.needsUpdate = true;
    geometry.computeVertexNormals();
  });

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
      <meshStandardMaterial color="#8b5cf6" wireframe />
    </mesh>
  );
}

interface TimelineSliderProps {
  scans: TimelineScanInfo[];
  position: number;
  onPositionChange: (pos: number) => void;
  isPlaying: boolean;
  onPlayPause: () => void;
}

function TimelineSlider({
  scans,
  position,
  onPositionChange,
  isPlaying,
  onPlayPause,
}: TimelineSliderProps) {
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const currentScanIndex = Math.round(position * (scans.length - 1));

  return (
    <div className="absolute bottom-0 left-0 right-0 bg-black/80 backdrop-blur-sm p-6">
      <div className="max-w-4xl mx-auto">
        {/* Play/Pause and info */}
        <div className="flex items-center gap-4 mb-4">
          <button
            onClick={onPlayPause}
            className="w-12 h-12 rounded-full bg-purple-500 hover:bg-purple-600 flex items-center justify-center transition-colors"
          >
            {isPlaying ? (
              <svg
                className="w-6 h-6 text-white"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <rect x="6" y="4" width="4" height="16" />
                <rect x="14" y="4" width="4" height="16" />
              </svg>
            ) : (
              <svg
                className="w-6 h-6 text-white ml-1"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <polygon points="5,3 19,12 5,21" />
              </svg>
            )}
          </button>

          <div className="text-white text-sm">
            <span className="font-medium">
              Scan {currentScanIndex + 1} of {scans.length}
            </span>
            <span className="text-gray-400 ml-2">
              {scans[currentScanIndex]?.original_filename}
            </span>
          </div>
        </div>

        {/* Slider track */}
        <div className="relative pt-2 pb-10">
          <input
            type="range"
            min={0}
            max={1}
            step={0.001}
            value={position}
            onChange={(e) => onPositionChange(parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer accent-purple-500"
          />

          {/* Scan markers */}
          <div className="absolute top-8 left-0 right-0">
            {scans.map((scan, i) => {
              const markerPosition = scans.length > 1 ? i / (scans.length - 1) : 0;
              return (
                <div
                  key={scan.job_id}
                  className="absolute flex flex-col items-center"
                  style={{
                    left: `${markerPosition * 100}%`,
                    transform: "translateX(-50%)",
                  }}
                >
                  <div
                    className={`w-3 h-3 rounded-full border-2 transition-colors ${
                      i === currentScanIndex
                        ? "bg-purple-500 border-purple-300"
                        : "bg-white border-gray-400"
                    }`}
                  />
                  <span className="text-xs text-gray-400 mt-1 whitespace-nowrap">
                    {formatDate(scan.scan_timestamp)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

interface TimelineViewerProps {
  patientId: number;
  caseId: number;
  scans: TimelineScanInfo[];
  meshUrl: string;
  timelineJobId: string;
  onClose: () => void;
}

export default function TimelineViewer({
  patientId,
  caseId,
  scans,
  meshUrl,
  timelineJobId,
  onClose,
}: TimelineViewerProps) {
  const [morphData, setMorphData] = useState<MorphData | null>(null);
  const [position, setPosition] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load morph data
  useEffect(() => {
    const loadMorphData = async () => {
      try {
        setLoading(true);
        const morphUrl = getTimelineMorphDataUrl(timelineJobId);
        const response = await fetch(morphUrl);

        if (!response.ok) {
          throw new Error("Failed to load morph data");
        }

        const data = await response.json();
        setMorphData(data);
        setLoading(false);
      } catch (err) {
        console.error("Failed to load morph data:", err);
        setError("Failed to load timeline animation data. Please try regenerating the timeline.");
        setLoading(false);
      }
    };
    loadMorphData();
  }, [timelineJobId]);

  // Animate playback
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setPosition((prev) => {
        const next = prev + 0.002; // Speed control
        if (next >= 1) {
          setIsPlaying(false);
          return 1;
        }
        return next;
      });
    }, 16); // ~60fps

    return () => clearInterval(interval);
  }, [isPlaying]);

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === " " || e.key === "Spacebar") {
        e.preventDefault();
        setIsPlaying((prev) => !prev);
      } else if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowLeft") {
        setPosition((prev) => Math.max(0, prev - 0.05));
      } else if (e.key === "ArrowRight") {
        setPosition((prev) => Math.min(1, prev + 0.05));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 bg-gray-900">
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-4 left-4 z-10 bg-white/90 hover:bg-white text-gray-800 px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 19l-7-7m0 0l7-7m-7 7h18"
          />
        </svg>
        Back
      </button>

      {/* Header info */}
      <div className="absolute top-4 right-4 z-10 bg-black/70 backdrop-blur-sm rounded-lg px-4 py-2">
        <h2 className="text-white font-semibold">Timeline View</h2>
        <p className="text-gray-400 text-sm">
          Patient {patientId} | Case {caseId}
        </p>
      </div>

      {/* Keyboard shortcuts hint */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 bg-black/50 backdrop-blur-sm rounded-lg px-3 py-1">
        <p className="text-gray-400 text-xs">
          Space: Play/Pause | Arrows: Scrub | Esc: Close
        </p>
      </div>

      {/* 3D Canvas */}
      <Canvas
        camera={{ position: [0, 0, 200], fov: 50 }}
        style={{ width: "100%", height: "calc(100% - 140px)" }}
        gl={{ alpha: false }}
      >
        <color attach="background" args={["#0d1117"]} />
        <ambientLight intensity={0.3} />
        <directionalLight position={[50, 80, 50]} intensity={1.5} />
        <directionalLight position={[-50, 20, 50]} intensity={0.6} />
        <directionalLight position={[0, 30, -80]} intensity={0.8} />
        <directionalLight position={[0, -50, 30]} intensity={0.4} />

        <Suspense fallback={<LoadingSpinner />}>
          {!loading && !error && morphData && (
            <TimelineBrainModel
              meshUrl={meshUrl}
              morphData={morphData}
              timelinePosition={position}
            />
          )}
          <Environment preset="studio" />
        </Suspense>

        <TrackballControls
          rotateSpeed={2}
          zoomSpeed={1.2}
          panSpeed={0.8}
          minDistance={50}
          maxDistance={500}
        />
      </Canvas>

      {/* Timeline controls */}
      {!loading && !error && (
        <TimelineSlider
          scans={scans}
          position={position}
          onPositionChange={setPosition}
          isPlaying={isPlaying}
          onPlayPause={() => setIsPlaying(!isPlaying)}
        />
      )}

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-white mt-4">Loading timeline...</p>
          </div>
        </div>
      )}

      {/* Error overlay */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
          <div className="bg-red-900/50 rounded-lg p-6 max-w-md text-center">
            <svg
              className="w-12 h-12 text-red-400 mx-auto mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <p className="text-white mb-4">{error}</p>
            <button
              onClick={onClose}
              className="bg-white text-gray-900 px-4 py-2 rounded hover:bg-gray-100 transition-colors"
            >
              Go Back
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
