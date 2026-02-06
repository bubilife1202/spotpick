const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002/api/v1";

export interface AreaStats {
  floating_population: number;
  competitor_count: number;
  survival_rate_1y: number;
  survival_rate_3y: number;
}

export interface NearbyStore {
  name: string;
  score: number;
}

export interface TimeAnalysis {
  peak_time: string;
  time_00_06: number;
  time_06_11: number;
  time_11_14: number;
  time_14_17: number;
  time_17_21: number;
  time_21_24: number;
}

export interface DayAnalysis {
  peak_day: string;
  weekday_ratio: number;
  weekend_ratio: number;
  mon: number;
  tue: number;
  wed: number;
  thu: number;
  fri: number;
  sat: number;
  sun: number;
}

export interface CustomerAnalysis {
  main_age_group: string;
  male_ratio: number;
  female_ratio: number;
  age_10: number;
  age_20: number;
  age_30: number;
  age_40: number;
  age_50: number;
  age_60: number;
}

export interface Competition {
  store_count: number;
  new_stores: number;
  closed_stores: number;
  franchise_stores: number;
  franchise_ratio: number;
}

export interface LocationRecommendation {
  rank: number;
  lat: number;
  lng: number;
  address: string;
  area_name: string;
  area_type: string;
  success_probability: number;
  confidence: number;
  estimated_monthly_rent: number;
  estimated_monthly_sales?: number;
  survival_rate_2y?: number;
  risk_factors: string[];
  recommendations: string[];
  key_success_factors: string[];
  nearby_successful_stores: NearbyStore[];
  area_stats: AreaStats;
  time_analysis?: TimeAnalysis;
  day_analysis?: DayAnalysis;
  customer_analysis?: CustomerAnalysis;
  competition?: Competition;
}

export interface RecommendationResponse {
  total_candidates: number;
  recommendations: LocationRecommendation[];
}

export interface QuickRecommendation {
  recommendation: {
    area_name: string;
    district: string;
    success_probability: string;
    monthly_rent: string;
    key_factors: string[];
    main_risk: string;
    tip: string | null;
  };
  alternatives: Array<{
    area_name: string;
    success_probability: string;
    monthly_rent: string;
  }>;
}

export interface LocationAnalysis {
  location: { lat: number; lng: number };
  nearest_area: string;
  distance_to_area_center: number;
  category: string;
  analysis: {
    success_probability: number;
    confidence: number;
    risk_factors: string[];
    recommendations: string[];
  };
  features: {
    floating_population: number;
    competitor_count: number;
    competitor_density: number;
    avg_rent_price: number;
    nearby_subway: boolean;
    office_ratio: number;
  };
  nearby_successful_stores: Array<{
    name: string;
    score: number;
    distance_km: number;
  }>;
}

export async function getRecommendations(params: {
  category?: string;
  budget_min: number;
  budget_max: number;
  preferred_district?: string;
  has_takeout?: boolean;
  top_n?: number;
}): Promise<RecommendationResponse> {
  const response = await fetch(`${API_BASE}/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      category: params.category || "coffee",
      budget_min: params.budget_min,
      budget_max: params.budget_max,
      preferred_district: params.preferred_district,
      has_takeout: params.has_takeout ?? true,
      // Beta: keep response fast (and map geocoding bounded).
      top_n: params.top_n || 5,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to fetch recommendations");
  }

  return response.json();
}

export async function getQuickRecommendation(
  budget: number,
  district?: string
): Promise<QuickRecommendation> {
  const params = new URLSearchParams({ budget: budget.toString() });
  if (district) params.append("district", district);

  const response = await fetch(`${API_BASE}/recommendations/quick?${params}`);
  if (!response.ok) throw new Error("Failed to fetch quick recommendation");
  return response.json();
}

export async function analyzeLocation(
  lat: number,
  lng: number,
  category: string = "coffee"
): Promise<LocationAnalysis> {
  const params = new URLSearchParams({
    lat: lat.toString(),
    lng: lng.toString(),
    category,
  });

  const response = await fetch(`${API_BASE}/recommendations/analyze?${params}`);
  if (!response.ok) throw new Error("Failed to analyze location");
  return response.json();
}

export interface Area {
  id: string;
  name: string;
  type: string;
  district: string;
  lat: number;
  lng: number;
  floating_population: number;
  avg_rent_price: number;
  coffee_shop_count: number;
  avg_success_score: number;
  survival_rate_1y: number;
  survival_rate_3y: number;
}

export async function getAreas(): Promise<{ total: number; items: Area[] }> {
  const response = await fetch(`${API_BASE}/areas`);
  if (!response.ok) throw new Error("Failed to fetch areas");
  return response.json();
}

export async function compareAreas(
  areaNames: string[]
): Promise<{
  areas: Array<{
    name: string;
    district: string;
    type: string;
    floating_population: number;
    avg_rent_price: number;
    competitor_count: number;
    survival_rate_3y: number;
    avg_success_score: number;
  }>;
  analysis: {
    best_survival_rate: string;
    lowest_rent: string;
    highest_traffic: string;
    recommendation: string;
  };
}> {
  const params = new URLSearchParams({ area_names: areaNames.join(",") });
  const response = await fetch(`${API_BASE}/areas/compare?${params}`);
  if (!response.ok) throw new Error("Failed to compare areas");
  return response.json();
}
