export type RiskLevel = "高" | "中" | "低";

export interface Farm {
  id: number;
  name: string;
  town: string;
  crop: string;
  area_mu: number;
  lat: number;
  lng: number;
  polygon: [number, number][];
  soil_type: string;
  irrigation_level: string;
  owner: string;
  risk_level: RiskLevel;
  current_risk_score: number;
  top_factors: { factor: string; contribution: number }[];
  recent_weather: {
    temperature: number;
    humidity: number;
    rainfall: number;
    weather_type: string;
  };
}

export interface AlertItem {
  id: number;
  farm_id: number;
  farm_name: string;
  town: string;
  title: string;
  risk_level: RiskLevel;
  trigger_reason: string;
  status: string;
  owner: string;
  suggestion: string;
  created_at: string;
}

export interface InspectionTask {
  id: number;
  farm_id: number;
  farm_name: string;
  town: string;
  crop: string;
  title: string;
  priority: string;
  assignee: string;
  due_date: string;
  status: string;
  description: string;
  record: string;
}
