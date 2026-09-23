export type FieldKey =
  | "title"
  | "context"
  | "need"
  | "users"
  | "data"
  | "constraints"
  | "expected_result"
  | "success_criteria"
  | "contact"
  | "interaction_format";

export type CriterionKey =
  | "context_need"
  | "data"
  | "expected_result"
  | "success_criteria"
  | "constraints"
  | "users"
  | "business_link";

export type LevelKey = "draft" | "working" | "ready" | "priority";
export type TaskStatus = "clarifying" | "review" | "published";
export type FieldStatus = "empty" | "suggested" | "confirmed";
export type ProposalStatus = "submitted" | "selected" | "rejected";
export type ProviderName = "openai" | "brev" | "stub";

export interface Evidence {
  source: string;
  quote: string;
} // source: "draft" | "answer:q1" | ...

export interface CardField {
  value: string | null;
  status: FieldStatus;
  source: "ai" | "user" | null;
  evidence: Evidence[];
  updated_at: string | null;
}
export type Card = Record<FieldKey, CardField>;

export interface Question {
  id: string; // "q1", "q2", ... уникален в пределах задачи
  field: FieldKey;
  question: string;
  why: string; // зачем спрашиваем, одна строка
  points_gain: number; // сколько баллов может дать ответ
  answer: string | null;
  round: number; // 1 — первичные вопросы, 2+ — дополнительные
}

export interface Check {
  id: string;
  label: string;
  field: FieldKey;
  points: number;
  passed: boolean;
}
export interface CriterionScore {
  criterion: CriterionKey;
  label: string;
  max: number;
  earned: number;
  checks: Check[];
}
export interface MissingItem {
  check_id: string;
  criterion: CriterionKey;
  field: FieldKey;
  hint: string;
  points_gain: number;
}
export interface Level {
  key: LevelKey;
  label: string;
  min: number;
  max: number;
}
export interface Achievement {
  key: string;
  label: string;
  description: string;
  earned: boolean;
}

export interface Rating {
  score: number; // 0..100, только подтверждённые поля
  potential_score: number; // если подтвердить все suggested-поля
  delta: number; // изменение с прошлого пересчёта
  level: Level;
  next_level: { key: LevelKey; label: string; points_needed: number } | null;
  breakdown: CriterionScore[]; // всегда 7 критериев, сумма max = 100
  missing: MissingItem[]; // по убыванию points_gain
  achievements: Achievement[];
}

export interface AiMeta {
  provider_used: ProviderName;
  model: string;
  degraded: boolean; // ответил не первый провайдер цепочки
  trace_ids: number[];
}

export interface TaskDetail {
  id: number;
  business: { id: number; name: string };
  status: TaskStatus;
  topic: string | null;
  draft_text: string;
  card: Card;
  questions: Question[];
  rating: Rating;
  catalog_position: number | null; // место в каталоге, если опубликована
  catalog_position_preview: number; // место при текущем score (для неопубликованной — «если опубликовать сейчас»)
  proposals_count: number;
  ai: AiMeta | null; // мета последнего AI-вызова по задаче
  created_at: string;
  updated_at: string;
  published_at: string | null;
}

export interface TaskSummary {
  // для списка «Мои задачи»
  id: number;
  title: string | null;
  status: TaskStatus;
  topic: string | null;
  score: number;
  level: Level;
  proposals_count: number;
  updated_at: string;
}

export interface CatalogItem {
  id: number;
  title: string;
  topic: string | null;
  business_name: string;
  score: number;
  level: Level;
  highlighted: boolean; // level = priority
  needs_clarification: boolean; // level = draft
  need_preview: string; // до 160 символов
  proposals_count: number;
  position: number; // 1-based, по умолчательной сортировке
  published_at: string;
}

export interface PublicTask {
  // карточка для команд: только confirmed-поля
  id: number;
  title: string;
  topic: string | null;
  business_name: string;
  card: Partial<Record<FieldKey, string>>;
  rating: Rating;
  position: number;
  proposals_count: number;
  published_at: string;
}

export interface Business {
  id: number;
  name: string;
  industry: string | null;
}
export interface Team {
  id: number;
  name: string;
  interests: string[];
  skills: string[];
  technologies: string[];
  progress_points: number;
}

export interface Milestone {
  id: number;
  proposal_id: number;
  title: string;
  points: number;
  status: "pending" | "confirmed";
  confirmed_at: string | null;
}

export interface Proposal {
  id: number;
  task: { id: number; title: string };
  team: Team;
  idea: string;
  plan: string;
  timeline: string;
  prototype_url: string | null;
  status: ProposalStatus;
  business_comment: string | null;
  milestones: Milestone[];
  created_at: string;
  decided_at: string | null;
}

export interface Recommendation {
  task: CatalogItem;
  match: number; // 0..1
  reasons: string[]; // человекочитаемые причины
  matched_terms: string[]; // совпавшие навыки и технологии
}

export interface ScoreEvent {
  score: number;
  delta: number;
  level: LevelKey;
  reason: string;
  created_at: string;
}

export interface AiTrace {
  id: number;
  task_id: number | null;
  operation: "analyze_draft" | "build_card" | "embed" | string;
  provider: ProviderName | "tfidf";
  model: string;
  prompt_version: string | null;
  status: "ok" | "repaired" | "fallback" | "failed";
  input_redacted: string;
  raw_output: string;
  parsed: unknown;
  errors: string[];
  grounding_rejected: { field: FieldKey; value: string; reason: string }[];
  latency_ms: number;
  created_at: string;
}

export interface Health {
  status: "ok";
  version: string;
  ai: {
    mode: "auto" | ProviderName;
    chain: { name: ProviderName; model: string; available: boolean }[];
  };
  embeddings: { chain: string[]; active: string };
}
export interface Meta {
  fields: {
    key: FieldKey;
    label: string;
    criterion: CriterionKey | null;
    placeholder: string;
  }[];
  criteria: {
    key: CriterionKey;
    label: string;
    weight: number;
    description: string;
  }[];
  levels: Level[];
  topics: { key: string; label: string }[];
}

export interface CardPatch {
  fields: Partial<
    Record<
      FieldKey,
      {
        value?: string | null; // передан → value, status=confirmed, source=user; null или "" → поле очищено (empty)
        confirm?: boolean; // true без value → suggested становится confirmed
        reject?: boolean; // true → suggested становится empty
      }
    >
  >;
}
