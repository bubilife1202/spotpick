"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import Map, { Marker, NavigationControl, Popup } from "react-map-gl/maplibre";
import type { MapRef } from "react-map-gl/maplibre";
import {
  MapPin,
  X,
  TrendingUp,
  DollarSign,
  Store,
  Shield,
  Clock,
  FileText,
  ScrollText,
  Eye,
  EyeOff,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";
import "maplibre-gl/dist/maplibre-gl.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface InteractiveMarkerData {
  district_code: string;
  district_name: string;
  district_type: string;
  lat: number;
  lng: number;
  rank: number;
  success_probability: number;
  estimated_rent: number;
  store_count: number;
  survival_rate: number;
  peak_time: string;
  industry_code: string;
  scorecard_total: number;
}

interface InteractiveMapProps {
  markers: InteractiveMarkerData[];
  highlightedCode: string | null;
  onMarkerClick: (districtCode: string) => void;
  onMarkerHover: (districtCode: string | null) => void;
  height?: number;
  className?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreColor(score: number): {
  bg: string;
  border: string;
  text: string;
  dot: string;
  markerBg: string;
} {
  if (score >= 80)
    return {
      bg: "bg-emerald-50",
      border: "border-emerald-400",
      text: "text-emerald-700",
      dot: "bg-emerald-500",
      markerBg: "from-emerald-500 to-emerald-600",
    };
  if (score >= 60)
    return {
      bg: "bg-amber-50",
      border: "border-amber-400",
      text: "text-amber-700",
      dot: "bg-amber-500",
      markerBg: "from-amber-500 to-amber-600",
    };
  return {
    bg: "bg-rose-50",
    border: "border-rose-400",
    text: "text-rose-700",
    dot: "bg-rose-500",
    markerBg: "from-rose-500 to-rose-600",
  };
}

function formatMan(wonValue: number): string {
  return `${Math.round(wonValue / 10000).toLocaleString()}만원`;
}

// ---------------------------------------------------------------------------
// Score Marker Pin
// ---------------------------------------------------------------------------

function ScoreMarkerPin({
  marker,
  isHighlighted,
  isPopupOpen,
  showCompetition,
  onClick,
  onMouseEnter,
  onMouseLeave,
}: {
  marker: InteractiveMarkerData;
  isHighlighted: boolean;
  isPopupOpen: boolean;
  showCompetition: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}) {
  const score = Math.round(marker.success_probability * 100);
  const sc = scoreColor(score);

  return (
    <button
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      className={cn(
        "relative group cursor-pointer transition-all duration-200",
        (isHighlighted || isPopupOpen) && "z-20 scale-125",
        !isHighlighted && !isPopupOpen && "hover:scale-110 hover:z-10"
      )}
    >
      {/* Pulse for highlighted */}
      {isHighlighted && (
        <span
          className={cn(
            "absolute inset-0 rounded-full animate-ping opacity-30",
            sc.dot
          )}
          style={{ animationDuration: "1.5s" }}
        />
      )}

      {/* Main marker circle */}
      <span
        className={cn(
          "relative flex items-center justify-center",
          "w-10 h-10 rounded-full",
          "bg-gradient-to-br shadow-lg",
          "ring-[3px] ring-white",
          "transition-all duration-200",
          sc.markerBg,
          (isHighlighted || isPopupOpen) && "ring-4 ring-blue-400 shadow-xl"
        )}
      >
        <span className="text-white text-sm font-bold">{marker.rank}</span>
      </span>

      {/* Pointer triangle */}
      <span
        className={cn(
          "absolute -bottom-1.5 left-1/2 -translate-x-1/2",
          "w-0 h-0",
          "border-l-[6px] border-r-[6px] border-t-[8px]",
          "border-l-transparent border-r-transparent",
          score >= 80
            ? "border-t-emerald-600"
            : score >= 60
              ? "border-t-amber-600"
              : "border-t-rose-600"
        )}
      />

      {/* Competition badge */}
      {showCompetition && (
        <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-slate-700 text-white text-[9px] font-bold flex items-center justify-center shadow-sm">
          {marker.store_count}
        </span>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Detailed Popup Card
// ---------------------------------------------------------------------------

function DetailPopupCard({
  marker,
  onClose,
}: {
  marker: InteractiveMarkerData;
  onClose: () => void;
}) {
  const score = Math.round(marker.success_probability * 100);
  const sc = scoreColor(score);
  const survivalPct = Math.min(100, Math.round(marker.survival_rate * 100));

  return (
    <Popup
      longitude={marker.lng}
      latitude={marker.lat}
      anchor="bottom"
      onClose={onClose}
      closeButton={false}
      closeOnClick={false}
      offset={[0, -20] as [number, number]}
      maxWidth="280px"
      className="interactive-map-popup"
    >
      <div className="min-w-[240px] -m-2.5">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div>
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  "w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold bg-gradient-to-br",
                  sc.markerBg
                )}
              >
                {marker.rank}
              </span>
              <h4 className="font-bold text-slate-900 text-sm">
                {marker.district_name}
              </h4>
            </div>
            <span className="text-[10px] text-slate-500 mt-0.5 inline-block">
              {marker.district_type}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-100 rounded-md transition-colors flex-shrink-0"
          >
            <X size={14} className="text-slate-400" />
          </button>
        </div>

        {/* Score bar */}
        <div className="mb-2.5">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-slate-500 flex items-center gap-1">
              <TrendingUp size={11} />
              추천점수
            </span>
            <span className={cn("font-bold", sc.text)}>{score}점</span>
          </div>
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full bg-gradient-to-r transition-all duration-500",
                score >= 80
                  ? "from-emerald-500 to-emerald-400"
                  : score >= 60
                    ? "from-amber-500 to-amber-400"
                    : "from-rose-500 to-rose-400"
              )}
              style={{ width: `${score}%` }}
            />
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11px] mb-3">
          <div className="flex items-center gap-1.5">
            <DollarSign size={11} className="text-blue-500 flex-shrink-0" />
            <span className="text-slate-500">월세</span>
            <span className="ml-auto font-semibold text-slate-700">
              {formatMan(marker.estimated_rent)}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Store size={11} className="text-orange-500 flex-shrink-0" />
            <span className="text-slate-500">경쟁</span>
            <span className="ml-auto font-semibold text-slate-700">
              {marker.store_count}개
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Shield size={11} className="text-indigo-500 flex-shrink-0" />
            <span className="text-slate-500">생존율</span>
            <span className="ml-auto font-semibold text-slate-700">
              {survivalPct}%
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Clock size={11} className="text-pink-500 flex-shrink-0" />
            <span className="text-slate-500">피크</span>
            <span className="ml-auto font-semibold text-slate-700 truncate max-w-[60px]">
              {marker.peak_time || "-"}
            </span>
          </div>
        </div>

        {/* Action links */}
        <div className="flex gap-2 pt-2 border-t border-slate-100">
          <Link
            href={`/report?district_code=${marker.district_code}&industry_code=${marker.industry_code}`}
            className="flex-1 flex items-center justify-center gap-1 py-1.5 bg-blue-600 text-white text-[11px] font-semibold rounded-lg hover:bg-blue-700 transition-colors"
          >
            <FileText size={11} />
            상세 보고서
          </Link>
          <Link
            href={`/report?district_code=${marker.district_code}&industry_code=${marker.industry_code}&tab=plan`}
            className="flex-1 flex items-center justify-center gap-1 py-1.5 bg-slate-100 text-slate-700 text-[11px] font-semibold rounded-lg hover:bg-slate-200 transition-colors"
          >
            <ScrollText size={11} />
            사업계획서
          </Link>
        </div>
      </div>
    </Popup>
  );
}

// ---------------------------------------------------------------------------
// Layer Toggle Buttons
// ---------------------------------------------------------------------------

function LayerToggles({
  showScore,
  showCompetition,
  onToggleScore,
  onToggleCompetition,
}: {
  showScore: boolean;
  showCompetition: boolean;
  onToggleScore: () => void;
  onToggleCompetition: () => void;
}) {
  return (
    <div className="absolute top-3 left-3 z-10 flex flex-col gap-1.5">
      <button
        onClick={onToggleScore}
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium",
          "shadow-md border transition-all",
          showScore
            ? "bg-white text-slate-700 border-blue-300"
            : "bg-white/70 text-slate-400 border-slate-200"
        )}
      >
        {showScore ? (
          <Eye size={12} className="text-blue-500" />
        ) : (
          <EyeOff size={12} />
        )}
        추천점수
      </button>
      <button
        onClick={onToggleCompetition}
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium",
          "shadow-md border transition-all",
          showCompetition
            ? "bg-white text-slate-700 border-orange-300"
            : "bg-white/70 text-slate-400 border-slate-200"
        )}
      >
        {showCompetition ? (
          <Eye size={12} className="text-orange-500" />
        ) : (
          <EyeOff size={12} />
        )}
        경쟁점포
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Score Legend
// ---------------------------------------------------------------------------

function ScoreLegend() {
  return (
    <div className="absolute bottom-3 left-3 z-10 bg-white/95 backdrop-blur-sm rounded-lg px-3 py-2 shadow-md border border-slate-100 flex items-center gap-3">
      <span className="flex items-center gap-1.5 text-[10px]">
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
        <span className="text-slate-600 font-medium">80+</span>
      </span>
      <span className="flex items-center gap-1.5 text-[10px]">
        <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
        <span className="text-slate-600 font-medium">60–79</span>
      </span>
      <span className="flex items-center gap-1.5 text-[10px]">
        <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
        <span className="text-slate-600 font-medium">&lt;60</span>
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main InteractiveMap Component
// ---------------------------------------------------------------------------

export function InteractiveMap({
  markers,
  highlightedCode,
  onMarkerClick,
  onMarkerHover,
  height = 480,
  className,
}: InteractiveMapProps) {
  const mapRef = useRef<MapRef>(null);
  const [popupMarker, setPopupMarker] = useState<InteractiveMarkerData | null>(
    null
  );
  const [showScore, setShowScore] = useState(true);
  const [showCompetition, setShowCompetition] = useState(false);
  const [isMapReady, setIsMapReady] = useState(false);

  // Center calculation
  const center = useMemo(() => {
    if (markers.length === 0) return { lat: 37.5665, lng: 126.978 };
    return {
      lat: markers.reduce((s, m) => s + m.lat, 0) / markers.length,
      lng: markers.reduce((s, m) => s + m.lng, 0) / markers.length,
    };
  }, [markers]);

  // Fly to highlighted marker
  useEffect(() => {
    if (!highlightedCode || !mapRef.current) return;
    const m = markers.find((mk) => mk.district_code === highlightedCode);
    if (m) {
      mapRef.current.flyTo({
        center: [m.lng, m.lat],
        duration: 600,
        essential: true,
      });
    }
  }, [highlightedCode, markers]);

  const handleMarkerClick = useCallback(
    (marker: InteractiveMarkerData) => {
      setPopupMarker((prev) =>
        prev?.district_code === marker.district_code ? null : marker
      );
      onMarkerClick(marker.district_code);
    },
    [onMarkerClick]
  );

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-slate-200/60 shadow-sm bg-slate-50",
        className
      )}
    >
      {/* Loading skeleton */}
      {!isMapReady && (
        <div
          className="absolute inset-0 bg-slate-100 animate-pulse flex items-center justify-center z-10"
          style={{ height }}
        >
          <div className="flex items-center gap-2 text-slate-400">
            <MapPin size={20} className="animate-bounce" />
            <span className="text-sm">지도 로딩중...</span>
          </div>
        </div>
      )}

      {/* Layer toggles */}
      <LayerToggles
        showScore={showScore}
        showCompetition={showCompetition}
        onToggleScore={() => setShowScore((p) => !p)}
        onToggleCompetition={() => setShowCompetition((p) => !p)}
      />

      {/* Map */}
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: center.lng,
          latitude: center.lat,
          zoom: 11,
        }}
        style={{ width: "100%", height }}
        mapStyle={MAP_STYLE}
        onLoad={() => setIsMapReady(true)}
        attributionControl={false}
      >
        <NavigationControl
          position="top-right"
          showCompass={false}
        />

        {markers.map((marker) => (
          <Marker
            key={marker.district_code}
            longitude={marker.lng}
            latitude={marker.lat}
            anchor="bottom"
          >
            <ScoreMarkerPin
              marker={marker}
              isHighlighted={highlightedCode === marker.district_code}
              isPopupOpen={popupMarker?.district_code === marker.district_code}
              showCompetition={showCompetition}
              onClick={() => handleMarkerClick(marker)}
              onMouseEnter={() => onMarkerHover(marker.district_code)}
              onMouseLeave={() => onMarkerHover(null)}
            />
          </Marker>
        ))}

        {popupMarker && (
          <DetailPopupCard
            marker={popupMarker}
            onClose={() => setPopupMarker(null)}
          />
        )}
      </Map>

      {/* Score legend */}
      {showScore && <ScoreLegend />}

      {/* Bottom gradient */}
      <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-white/30 to-transparent pointer-events-none" />
    </div>
  );
}

export default InteractiveMap;
