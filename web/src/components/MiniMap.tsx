"use client";

import { useState, useEffect, useCallback } from "react";
import Map, { Marker, NavigationControl, Popup } from "react-map-gl/maplibre";
import { MapPin, Maximize2, X, TrendingUp, Navigation } from "lucide-react";
import { cn } from "@/lib/utils";
import "maplibre-gl/dist/maplibre-gl.css";

interface MapMarker {
  lat: number;
  lng: number;
  label: string;
  type?: "recommended" | "competitor" | "selected";
  rank?: number;
  successProbability?: number;
}

interface MiniMapProps {
  markers: MapMarker[];
  center?: { lat: number; lng: number };
  zoom?: number;
  height?: number;
  className?: string;
}

// OpenStreetMap 스타일 (MapView.tsx와 동일)
const MAP_STYLE = {
  version: 8 as const,
  sources: {
    osm: {
      type: "raster" as const,
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    },
  },
  layers: [
    {
      id: "osm",
      type: "raster" as const,
      source: "osm",
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

const MARKER_CONFIG = {
  recommended: {
    bg: "from-primary-500 to-primary-600",
    ring: "ring-primary-500/30",
    pulse: "bg-primary-400",
    label: "추천",
    dot: "bg-primary-500",
  },
  competitor: {
    bg: "from-danger-500 to-danger-600",
    ring: "ring-danger-500/30",
    pulse: "bg-danger-400",
    label: "경쟁",
    dot: "bg-danger-500",
  },
  selected: {
    bg: "from-success-500 to-success-600",
    ring: "ring-success-500/30",
    pulse: "bg-success-400",
    label: "선택",
    dot: "bg-success-500",
  },
};

// 마커 컴포넌트
function MarkerPin({
  marker,
  index,
  onClick,
  isSelected,
}: {
  marker: MapMarker;
  index: number;
  onClick: () => void;
  isSelected: boolean;
}) {
  const config = MARKER_CONFIG[marker.type || "recommended"];

  return (
    <button
      onClick={onClick}
      className={cn(
        "relative group cursor-pointer transition-all duration-300",
        "animate-bounce-in",
        isSelected && "z-10 scale-110"
      )}
      style={{ animationDelay: `${index * 80}ms` }}
    >
      {/* 펄스 효과 */}
      <span
        className={cn(
          "absolute inset-0 rounded-full animate-ping opacity-40",
          config.pulse
        )}
        style={{ animationDuration: "2s" }}
      />

      {/* 메인 마커 */}
      <span
        className={cn(
          "relative flex items-center justify-center",
          "w-9 h-9 rounded-full",
          "bg-gradient-to-br shadow-lg",
          "ring-4 ring-offset-1 ring-offset-white",
          "transform group-hover:scale-110 transition-transform duration-200",
          config.bg,
          config.ring
        )}
      >
        {marker.rank ? (
          <span className="text-white text-sm font-bold tracking-tight">
            {marker.rank}
          </span>
        ) : (
          <MapPin className="text-white drop-shadow-sm" size={18} />
        )}
      </span>

      {/* 포인터 */}
      <span
        className={cn(
          "absolute -bottom-1.5 left-1/2 -translate-x-1/2",
          "w-0 h-0 border-l-[6px] border-r-[6px] border-t-[8px]",
          "border-l-transparent border-r-transparent",
          marker.type === "competitor"
            ? "border-t-danger-600"
            : marker.type === "selected"
              ? "border-t-success-600"
              : "border-t-primary-600"
        )}
      />
    </button>
  );
}

// 팝업 컴포넌트
function MarkerPopup({
  marker,
  onClose,
}: {
  marker: MapMarker;
  onClose: () => void;
}) {
  const config = MARKER_CONFIG[marker.type || "recommended"];

  return (
    <Popup
      longitude={marker.lng}
      latitude={marker.lat}
      anchor="bottom"
      onClose={onClose}
      closeButton={false}
      closeOnClick={false}
      offset={[0, -12] as [number, number]}
      className="animate-scale-in"
    >
      <div className="relative min-w-[160px] -m-2.5">
        {/* 헤더 */}
        <div className="flex items-center justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            {marker.rank && (
              <span
                className={cn(
                  "w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold bg-gradient-to-br",
                  config.bg
                )}
              >
                {marker.rank}
              </span>
            )}
            <span className="font-semibold text-gray-900 text-sm leading-tight">
              {marker.label}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-0.5 hover:bg-gray-100 rounded transition-colors"
          >
            <X size={14} className="text-gray-400" />
          </button>
        </div>

        {/* 성공확률 바 */}
        {marker.successProbability !== undefined && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500 flex items-center gap-1">
                <TrendingUp size={12} />
                성공확률
              </span>
              <span className="font-semibold text-gray-900">
                {Math.round(marker.successProbability * 100)}%
              </span>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full bg-gradient-to-r transition-all duration-500",
                  marker.successProbability >= 0.7
                    ? "from-success-500 to-success-400"
                    : marker.successProbability >= 0.4
                      ? "from-warning-500 to-warning-400"
                      : "from-danger-500 to-danger-400"
                )}
                style={{ width: `${marker.successProbability * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* 좌표 */}
        <div className="mt-2 pt-2 border-t border-gray-100 flex items-center gap-1 text-[10px] text-gray-400">
          <Navigation size={10} />
          {marker.lat.toFixed(4)}, {marker.lng.toFixed(4)}
        </div>
      </div>
    </Popup>
  );
}

// 범례 컴포넌트
function MapLegend({ markers }: { markers: MapMarker[] }) {
  const types = Array.from(
    new Set(markers.map((m) => m.type || "recommended"))
  ) as Array<keyof typeof MARKER_CONFIG>;

  return (
    <div
      className={cn(
        "absolute bottom-3 left-3 z-10",
        "bg-white/95 backdrop-blur-sm rounded-lg",
        "px-3 py-2 shadow-lg border border-gray-100",
        "flex items-center gap-4"
      )}
    >
      {types.map((type) => {
        const config = MARKER_CONFIG[type];
        return (
          <span key={type} className="flex items-center gap-1.5 text-xs">
            <span className={cn("w-2.5 h-2.5 rounded-full", config.dot)} />
            <span className="text-gray-600 font-medium">{config.label}</span>
          </span>
        );
      })}
    </div>
  );
}

// 확장 모달
function ExpandedMapModal({
  markers,
  center,
  zoom,
  selectedMarker,
  onMarkerSelect,
  onClose,
}: {
  markers: MapMarker[];
  center: { lat: number; lng: number };
  zoom: number;
  selectedMarker: MapMarker | null;
  onMarkerSelect: (marker: MapMarker | null) => void;
  onClose: () => void;
}) {
  // ESC 키로 닫기
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-8">
      {/* 오버레이 */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />

      {/* 모달 */}
      <div
        className={cn(
          "relative w-full max-w-4xl h-[80vh] max-h-[600px]",
          "bg-white rounded-2xl shadow-2xl overflow-hidden",
          "animate-scale-in"
        )}
      >
        {/* 헤더 */}
        <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-4 py-3 bg-gradient-to-b from-white via-white/95 to-transparent">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary-500 flex items-center justify-center">
              <MapPin size={16} className="text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 text-sm">
                추천 위치 지도
              </h3>
              <p className="text-xs text-gray-500">
                {markers.length}개 위치 표시 중
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className={cn(
              "w-8 h-8 rounded-lg flex items-center justify-center",
              "bg-gray-100 hover:bg-gray-200 transition-colors"
            )}
          >
            <X size={18} className="text-gray-600" />
          </button>
        </div>

        {/* 지도 */}
        <Map
          initialViewState={{
            longitude: center.lng,
            latitude: center.lat,
            zoom: zoom + 1,
          }}
          style={{ width: "100%", height: "100%" }}
          mapStyle={MAP_STYLE}
        >
          <NavigationControl position="top-right" showCompass={true} />

          {markers.map((marker, index) => (
            <Marker
              key={`expanded-${index}`}
              longitude={marker.lng}
              latitude={marker.lat}
              anchor="bottom"
            >
              <MarkerPin
                marker={marker}
                index={index}
                onClick={() =>
                  onMarkerSelect(
                    selectedMarker?.lat === marker.lat &&
                      selectedMarker?.lng === marker.lng
                      ? null
                      : marker
                  )
                }
                isSelected={
                  selectedMarker?.lat === marker.lat &&
                  selectedMarker?.lng === marker.lng
                }
              />
            </Marker>
          ))}

          {selectedMarker && (
            <MarkerPopup
              marker={selectedMarker}
              onClose={() => onMarkerSelect(null)}
            />
          )}
        </Map>

        {/* 범례 */}
        <MapLegend markers={markers} />

        {/* 마커 리스트 (사이드바) */}
        <div
          className={cn(
            "absolute bottom-3 right-3 z-10",
            "w-48 max-h-40 overflow-y-auto scrollbar-thin",
            "bg-white/95 backdrop-blur-sm rounded-lg",
            "shadow-lg border border-gray-100"
          )}
        >
          <div className="p-2 border-b border-gray-100">
            <span className="text-xs font-medium text-gray-500">
              위치 목록
            </span>
          </div>
          <div className="p-1">
            {markers.map((marker, index) => {
              const config = MARKER_CONFIG[marker.type || "recommended"];
              const isSelected =
                selectedMarker?.lat === marker.lat &&
                selectedMarker?.lng === marker.lng;

              return (
                <button
                  key={index}
                  onClick={() => onMarkerSelect(isSelected ? null : marker)}
                  className={cn(
                    "w-full flex items-center gap-2 px-2 py-1.5 rounded-md",
                    "text-left text-xs transition-colors",
                    isSelected
                      ? "bg-primary-50 text-primary-700"
                      : "hover:bg-gray-50 text-gray-700"
                  )}
                >
                  <span
                    className={cn("w-2 h-2 rounded-full flex-shrink-0", config.dot)}
                  />
                  <span className="truncate flex-1">{marker.label}</span>
                  {marker.rank && (
                    <span className="text-gray-400 font-medium">
                      #{marker.rank}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// 메인 MiniMap 컴포넌트
export function MiniMap({
  markers,
  center,
  zoom = 13,
  height = 200,
  className,
}: MiniMapProps) {
  const [selectedMarker, setSelectedMarker] = useState<MapMarker | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMapReady, setIsMapReady] = useState(false);

  // 마커들의 중심점 계산
  const defaultCenter = center ||
    (markers.length > 0
      ? {
          lat: markers.reduce((sum, m) => sum + m.lat, 0) / markers.length,
          lng: markers.reduce((sum, m) => sum + m.lng, 0) / markers.length,
        }
      : { lat: 37.5665, lng: 126.978 }); // 서울 기본값

  const handleMarkerClick = useCallback((marker: MapMarker) => {
    setSelectedMarker((prev) =>
      prev?.lat === marker.lat && prev?.lng === marker.lng ? null : marker
    );
  }, []);

  return (
    <>
      <div
        className={cn(
          "relative overflow-hidden",
          "rounded-xl border border-gray-200/80",
          "shadow-sm hover:shadow-md transition-shadow duration-300",
          "bg-gray-50",
          className
        )}
      >
        {/* 로딩 스켈레톤 */}
        {!isMapReady && (
          <div
            className="absolute inset-0 bg-gray-100 animate-pulse flex items-center justify-center"
            style={{ height }}
          >
            <div className="flex items-center gap-2 text-gray-400">
              <MapPin size={20} className="animate-bounce" />
              <span className="text-sm">지도 로딩중...</span>
            </div>
          </div>
        )}

        {/* 확장 버튼 */}
        <button
          onClick={() => setIsExpanded(true)}
          className={cn(
            "absolute top-2.5 right-2.5 z-10",
            "w-8 h-8 rounded-lg",
            "bg-white/95 backdrop-blur-sm shadow-md border border-gray-100",
            "flex items-center justify-center",
            "hover:bg-gray-50 hover:scale-105 active:scale-95",
            "transition-all duration-200"
          )}
          title="전체화면으로 보기"
        >
          <Maximize2 size={14} className="text-gray-600" />
        </button>

        {/* 지도 */}
        <Map
          initialViewState={{
            longitude: defaultCenter.lng,
            latitude: defaultCenter.lat,
            zoom,
          }}
          style={{ width: "100%", height }}
          mapStyle={MAP_STYLE}
          onLoad={() => setIsMapReady(true)}
          attributionControl={false}
        >
          <NavigationControl
            position="top-right"
            showCompass={false}
            style={{ marginTop: "40px" }}
          />

          {markers.map((marker, index) => (
            <Marker
              key={`mini-${index}`}
              longitude={marker.lng}
              latitude={marker.lat}
              anchor="bottom"
            >
              <MarkerPin
                marker={marker}
                index={index}
                onClick={() => handleMarkerClick(marker)}
                isSelected={
                  selectedMarker?.lat === marker.lat &&
                  selectedMarker?.lng === marker.lng
                }
              />
            </Marker>
          ))}

          {selectedMarker && (
            <MarkerPopup
              marker={selectedMarker}
              onClose={() => setSelectedMarker(null)}
            />
          )}
        </Map>

        {/* 범례 */}
        {markers.length > 0 && <MapLegend markers={markers} />}

        {/* 하단 그라데이션 */}
        <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white/40 to-transparent pointer-events-none" />
      </div>

      {/* 확장 모달 */}
      {isExpanded && (
        <ExpandedMapModal
          markers={markers}
          center={defaultCenter}
          zoom={zoom}
          selectedMarker={selectedMarker}
          onMarkerSelect={setSelectedMarker}
          onClose={() => setIsExpanded(false)}
        />
      )}
    </>
  );
}

export type { MapMarker, MiniMapProps };
