export type EsStatus = {
  connected: boolean;
  cluster: string | null;
  inference_id: string | null;
  programs: number;
  applications: number;
  error: string | null;
};

export type Health = { mistral: boolean; mistral_model?: string; elastic: EsStatus };

export type Housing = {
  source: string;
  source_url?: string;
  buildings: number;
  units: number;
  affordable_units: number;
  family_size_units?: number;
  neighborhoods: number;
  by_neighborhood: { neighborhood: string; buildings: number; units: number }[];
  by_program: { program: string; buildings: number; units: number }[];
  query?: unknown;
  took_ms?: number;
  ms?: number;
  /** ISO time DataSF last updated the dataset (from its metadata). */
  source_updated_at?: string | null;
  /** ISO time the dataset was last loaded into Elasticsearch. */
  synced_at?: string | null;
};

export type ImpactScope = "all" | "live";

export type BudgetItem = { item: string; amount: number };

export type Budget = {
  items: BudgetItem[];
  total: number;
  recipients?: number;
  per_recipient?: number;
  grant_share?: number;
  expected_completers?: number;
  expected_successes?: number;
  per_successful_outcome?: number;
  note?: string;
};

export type Targets = {
  activated?: number;
  goal_check_rate?: number;
  decision_days?: number;
  completion_rate?: number;
  placement_rate?: number;
  housing_stability?: number;
};

export type Impact = {
  total: number;
  by_status: Record<string, number>;
  by_tier: Record<string, number>;
  by_language?: Record<string, number>;
  by_property: { property: string; residents: number; approved: number }[];
  dollars: { free_program_value: number; public_aid: number; grant: number };
  outcomes: { completed: number; placed_or_raise: number };
  funnel?: { stage: string; count: number }[];
  median_decision_days: number | null;
  simulated_count?: number;
  live_count?: number;
  took_ms?: number;
  scope?: ImpactScope;
  query?: unknown;
  budget?: Budget;
  targets?: Targets;
  ms?: number;
};

export type Loaded<T> = { data: T | null; error: { message: string; stage: string } | null; at: number | null };
