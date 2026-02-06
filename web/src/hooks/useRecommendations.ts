import { useQuery } from "@tanstack/react-query";
import {
  getRecommendations,
  getQuickRecommendation,
  analyzeLocation,
  getAreas,
  compareAreas,
} from "@/lib/api";

export function useRecommendations(params: {
  budget_min: number;
  budget_max: number;
  preferred_district?: string;
  enabled?: boolean;
}) {
  return useQuery({
    queryKey: ["recommendations", params],
    queryFn: () => getRecommendations(params),
    enabled: params.enabled !== false,
  });
}

export function useQuickRecommendation(budget: number, district?: string) {
  return useQuery({
    queryKey: ["quick-recommendation", budget, district],
    queryFn: () => getQuickRecommendation(budget, district),
    enabled: budget > 0,
  });
}

export function useLocationAnalysis(
  lat: number | null,
  lng: number | null,
  category: string = "coffee"
) {
  return useQuery({
    queryKey: ["location-analysis", lat, lng, category],
    queryFn: () => analyzeLocation(lat!, lng!, category),
    enabled: lat !== null && lng !== null,
  });
}

export function useAreas() {
  return useQuery({
    queryKey: ["areas"],
    queryFn: getAreas,
  });
}

export function useCompareAreas(areaNames: string[]) {
  return useQuery({
    queryKey: ["compare-areas", areaNames],
    queryFn: () => compareAreas(areaNames),
    enabled: areaNames.length >= 2,
  });
}
