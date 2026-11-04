// Shapes served by the FastAPI directory endpoints. Fields are optional on purpose:
// the backend owns the schema and the UI must render whatever subset arrives.

export type Kind = "program" | "resource" | "tier";

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- backend-owned, loosely typed payload
export type Item = Record<string, any> & { kind?: Kind; id?: string };

export interface Section {
  id: string;
  title: string;
  subtitle?: string;
  kind: Kind;
  items: Item[];
}

export interface DirectoryResponse {
  sections: Section[];
  counts?: Record<string, number>;
}

export interface SearchResponse {
  results: Item[];
  query?: unknown;
  ms?: number;
}

export const SCHEDULE_LABEL: Record<string, string> = {
  "full-time-day": "Full-time · daytime",
  "part-time-day": "Part-time · daytime",
  "part-time-evening": "Evenings",
  "self-paced": "Self-paced",
};

export const LEVEL_LABEL: Record<string, string> = {
  basics: "Digital basics",
  entry: "Entry level",
  career: "Career program",
};

export const LANG_LABEL: Record<string, string> = {
  en: "English",
  es: "Español",
  zh: "中文",
  "zh-hant": "繁中",
  yue: "粵語",
  tl: "Filipino",
  fil: "Filipino",
  vi: "Tiếng Việt",
  ru: "Русский",
  ar: "العربية",
};

export function itemKind(item: Item, fallback: Kind): Kind {
  const k = item.kind;
  return k === "program" || k === "resource" || k === "tier" ? k : fallback;
}

export function itemTitle(item: Item): string {
  return String(item.name ?? item.program ?? item.label ?? item.title ?? item.id ?? "Untitled");
}

export function programCost(item: Item): number {
  return (Number(item.tuition_usd) || 0) + (Number(item.materials_usd) || 0) + (Number(item.exam_fees_usd) || 0);
}
