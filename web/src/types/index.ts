export interface Store {
  id: string;
  name: string;
  category: string;
  address: string;
  lat: number;
  lng: number;
  review_count: number;
  avg_review_score: number;
  success_score?: number;
  survival_months?: number;
  is_closed: boolean;
}

export interface CommercialArea {
  id: string;
  name: string;
  type: string;
  lat: number;
  lng: number;
  region_code: string;
  population?: number;
  floating_population?: number;
  avg_rent_price?: number;
}

export interface SuccessFactors {
  survival_score: number;
  review_score: number;
  growth_score: number;
  stability_score: number;
  total_score: number;
}

export interface Prediction {
  success_probability: number;
  confidence: number;
  risk_factors: string[];
  recommendations: string[];
}
