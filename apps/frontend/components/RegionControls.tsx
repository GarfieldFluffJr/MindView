"use client";

import { useState, useMemo } from "react";
import { RegionInfo } from "@/lib/api";

interface RegionState {
  visible: boolean;
  opacity: number;
}

interface RegionControlsProps {
  regions: RegionInfo[];
  regionStates: Record<string, RegionState>;
  onRegionChange: (regionName: string, state: Partial<RegionState>) => void;
  onShowAll: () => void;
  onHideAll: () => void;
  hasTumor: boolean;
}

const CATEGORY_ORDER = [
  { key: "tumor", label: "Tumor Regions", priority: 1 },
  { key: "subcortical", label: "Subcortical Structures", priority: 2 },
  { key: "ventricle", label: "Ventricles", priority: 3 },
  { key: "brainstem", label: "Brainstem", priority: 4 },
  { key: "cerebellum", label: "Cerebellum", priority: 5 },
  { key: "cortex", label: "Cerebral Cortex", priority: 6 },
  { key: "white_matter", label: "White Matter", priority: 7 },
  { key: "csf", label: "CSF", priority: 8 },
  { key: "intensity_layer", label: "Intensity Layers", priority: 9 },
  { key: "region", label: "Regions", priority: 10 },
  { key: "unknown", label: "Other", priority: 11 },
];

function rgbToHex(r: number, g: number, b: number): string {
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}

export default function RegionControls({
  regions,
  regionStates,
  onRegionChange,
  onShowAll,
  onHideAll,
  hasTumor,
}: RegionControlsProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(["tumor", "subcortical", "ventricle"])
  );
  const [isolatedRegion, setIsolatedRegion] = useState<string | null>(null);

  // Group regions by category
  const groupedRegions = useMemo(() => {
    const groups: Record<string, RegionInfo[]> = {};

    for (const region of regions) {
      const category = region.category || "unknown";
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(region);
    }

    // Sort categories by priority
    const sortedCategories = CATEGORY_ORDER.filter(
      (cat) => groups[cat.key]?.length > 0
    );

    return sortedCategories.map((cat) => ({
      ...cat,
      regions: groups[cat.key] || [],
    }));
  }, [regions]);

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  const handleIsolate = (regionName: string) => {
    if (isolatedRegion === regionName) {
      // Un-isolate - show all regions that were visible before
      setIsolatedRegion(null);
      onShowAll();
    } else {
      // Isolate - hide all except this region
      setIsolatedRegion(regionName);
      for (const region of regions) {
        onRegionChange(region.name, {
          visible: region.name === regionName,
        });
      }
    }
  };

  const handleCategoryShowAll = (categoryRegions: RegionInfo[]) => {
    for (const region of categoryRegions) {
      onRegionChange(region.name, { visible: true });
    }
  };

  const handleCategoryHideAll = (categoryRegions: RegionInfo[]) => {
    for (const region of categoryRegions) {
      onRegionChange(region.name, { visible: false });
    }
  };

  return (
    <div className="bg-gray-900/95 backdrop-blur-sm rounded-lg overflow-hidden flex flex-col max-h-[70vh]">
      {/* Header */}
      <div className="p-3 border-b border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-white font-semibold text-sm">Brain Regions</h3>
          <span className="text-gray-400 text-xs">{regions.length} regions</span>
        </div>

        {hasTumor && (
          <div className="bg-red-900/50 border border-red-700 rounded px-2 py-1 mb-2">
            <span className="text-red-300 text-xs font-medium">
              Tumor regions detected
            </span>
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={onShowAll}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition-colors"
          >
            Show All
          </button>
          <button
            onClick={onHideAll}
            className="flex-1 bg-gray-700 hover:bg-gray-600 text-white text-xs px-2 py-1 rounded transition-colors"
          >
            Hide All
          </button>
        </div>
      </div>

      {/* Region List */}
      <div className="overflow-y-auto flex-1 p-2">
        {groupedRegions.map((group) => (
          <div key={group.key} className="mb-2">
            {/* Category Header */}
            <div className="flex items-center justify-between px-2 py-1.5 bg-gray-800 rounded hover:bg-gray-750 transition-colors">
              <div
                className="flex items-center gap-2 flex-1 cursor-pointer"
                onClick={() => toggleCategory(group.key)}
              >
                <span
                  className={`transform transition-transform ${
                    expandedCategories.has(group.key) ? "rotate-90" : ""
                  }`}
                >
                  <svg
                    className="w-3 h-3 text-gray-400"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                </span>
                <span
                  className={`text-xs font-medium ${
                    group.key === "tumor" ? "text-red-400" : "text-gray-300"
                  }`}
                >
                  {group.label}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-gray-500 text-xs">
                  {group.regions.length}
                </span>
                <button
                  onClick={() => handleCategoryShowAll(group.regions)}
                  className="text-gray-400 hover:text-white p-0.5"
                  title="Show all in category"
                >
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                    <path
                      fillRule="evenodd"
                      d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
                <button
                  onClick={() => handleCategoryHideAll(group.regions)}
                  className="text-gray-400 hover:text-white p-0.5"
                  title="Hide all in category"
                >
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zm4.261 4.26l1.514 1.515a2.003 2.003 0 012.45 2.45l1.514 1.514a4 4 0 00-5.478-5.478z"
                      clipRule="evenodd"
                    />
                    <path d="M12.454 16.697L9.75 13.992a4 4 0 01-3.742-3.741L2.335 6.578A9.98 9.98 0 00.458 10c1.274 4.057 5.065 7 9.542 7 .847 0 1.669-.105 2.454-.303z" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Category Regions */}
            {expandedCategories.has(group.key) && (
              <div className="mt-1 space-y-1">
                {group.regions.map((region) => {
                  const state = regionStates[region.name] || {
                    visible: region.defaultVisible,
                    opacity: region.opacity,
                  };

                  return (
                    <div
                      key={region.name}
                      className={`px-2 py-1.5 rounded text-xs ${
                        state.visible
                          ? "bg-gray-800/50"
                          : "bg-gray-800/30 opacity-60"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {/* Visibility Toggle */}
                        <button
                          onClick={() =>
                            onRegionChange(region.name, {
                              visible: !state.visible,
                            })
                          }
                          className={`w-4 h-4 rounded border flex-shrink-0 ${
                            state.visible
                              ? "bg-blue-500 border-blue-500"
                              : "border-gray-500"
                          }`}
                        >
                          {state.visible && (
                            <svg
                              className="w-4 h-4 text-white"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M5 13l4 4L19 7"
                              />
                            </svg>
                          )}
                        </button>

                        {/* Color Indicator */}
                        <div
                          className="w-3 h-3 rounded-sm flex-shrink-0"
                          style={{
                            backgroundColor: rgbToHex(
                              region.color[0],
                              region.color[1],
                              region.color[2]
                            ),
                          }}
                        />

                        {/* Region Name */}
                        <span
                          className={`flex-1 truncate ${
                            region.category === "tumor"
                              ? "text-red-300"
                              : "text-gray-300"
                          }`}
                          title={region.label}
                        >
                          {region.label}
                        </span>

                        {/* Isolate Button */}
                        <button
                          onClick={() => handleIsolate(region.name)}
                          className={`p-0.5 rounded ${
                            isolatedRegion === region.name
                              ? "text-blue-400"
                              : "text-gray-500 hover:text-gray-300"
                          }`}
                          title={
                            isolatedRegion === region.name
                              ? "Show all"
                              : "Isolate region"
                          }
                        >
                          <svg
                            className="w-3 h-3"
                            fill="currentColor"
                            viewBox="0 0 20 20"
                          >
                            <path
                              fillRule="evenodd"
                              d="M3 4a1 1 0 011-1h4a1 1 0 010 2H6.414l2.293 2.293a1 1 0 01-1.414 1.414L5 6.414V8a1 1 0 01-2 0V4zm9 1a1 1 0 010-2h4a1 1 0 011 1v4a1 1 0 01-2 0V6.414l-2.293 2.293a1 1 0 11-1.414-1.414L13.586 5H12zm-9 7a1 1 0 012 0v1.586l2.293-2.293a1 1 0 111.414 1.414L6.414 15H8a1 1 0 010 2H4a1 1 0 01-1-1v-4zm13-1a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 010-2h1.586l-2.293-2.293a1 1 0 111.414-1.414L15 13.586V12a1 1 0 011-1z"
                              clipRule="evenodd"
                            />
                          </svg>
                        </button>
                      </div>

                      {/* Opacity Slider */}
                      {state.visible && (
                        <div className="mt-1 flex items-center gap-2 pl-6">
                          <span className="text-gray-500 text-[10px] w-8">
                            {Math.round(state.opacity * 100)}%
                          </span>
                          <input
                            type="range"
                            min={0}
                            max={100}
                            value={state.opacity * 100}
                            onChange={(e) =>
                              onRegionChange(region.name, {
                                opacity: Number(e.target.value) / 100,
                              })
                            }
                            className="flex-1 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
