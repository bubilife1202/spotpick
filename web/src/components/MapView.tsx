"use client";

import React, { useMemo } from 'react';
import Map, { Marker, NavigationControl } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { MapPin } from 'lucide-react';

interface Location {
  lat: number;
  lng: number;
  name: string;
  rank: number;
}

interface MapViewProps {
  locations: Location[];
  selectedLocation: { lat: number; lng: number } | null;
  onLocationSelect: (location: Location) => void;
}

// OpenStreetMap 타일 스타일 정의 (무료, API 키 불필요)
const MAP_STYLE = {
  version: 8 as const,
  sources: {
    osm: {
      type: 'raster' as const,
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    },
  },
  layers: [
    {
      id: 'osm',
      type: 'raster' as const,
      source: 'osm',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

const SEOUL_CENTER = {
  latitude: 37.5665,
  longitude: 126.9780,
  zoom: 11
};

export default function MapView({ locations, selectedLocation, onLocationSelect }: MapViewProps) {
  // 선택된 위치가 변경되면 팝업 등을 표시하거나 스타일을 변경할 수 있습니다.
  // 현재 요구사항은 마커 색상 변경입니다.

  const markers = useMemo(() => {
    return locations.map((location, index) => {
      const isSelected = selectedLocation 
        ? Math.abs(location.lat - selectedLocation.lat) < 0.00001 && 
          Math.abs(location.lng - selectedLocation.lng) < 0.00001
        : false;

      return (
        <Marker
          key={`marker-${index}`}
          latitude={location.lat}
          longitude={location.lng}
          anchor="bottom"
          onClick={(e) => {
            // 이벤트 전파 방지
            e.originalEvent.stopPropagation();
            onLocationSelect(location);
          }}
        >
          <div 
            className={`
              cursor-pointer transition-transform hover:scale-110
              ${isSelected ? 'text-blue-600 z-10 scale-110' : 'text-gray-500 z-0'}
            `}
            aria-label={location.name}
          >
            <MapPin 
              size={isSelected ? 40 : 32} 
              fill={isSelected ? "currentColor" : "none"}
              className="drop-shadow-md"
            />
            {isSelected && (
              <div className="absolute left-1/2 -translate-x-1/2 -top-8 bg-white px-2 py-1 rounded shadow text-xs font-bold whitespace-nowrap text-black border border-gray-200">
                {location.name}
              </div>
            )}
          </div>
        </Marker>
      );
    });
  }, [locations, selectedLocation, onLocationSelect]);

  return (
    <div className="w-full h-full min-h-[280px] rounded-lg overflow-hidden border border-gray-200 shadow-sm relative">
      <Map
        initialViewState={SEOUL_CENTER}
        style={{ width: '100%', height: '100%' }}
        mapStyle={MAP_STYLE}
        attributionControl={true}
      >
        <NavigationControl position="top-right" />
        {markers}
      </Map>
    </div>
  );
}
