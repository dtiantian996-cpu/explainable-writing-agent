export type TaskType = "task1_academic" | "task1_general" | "task2";
export type AssessmentStatus = "queued" | "processing" | "completed" | "failed";

export interface AuthUser {
  id: string;
  email: string;
  displayName: string;
  role: string;
}

export interface AuthSessionResponse {
  user: AuthUser;
}

export interface AuthLoginPayload {
  email: string;
  password: string;
}

export interface AuthRegisterPayload extends AuthLoginPayload {
  displayName: string;
}

export interface ReportDimension {
  score: number;
  reasonBullets: string[];
}

export interface SuggestionItem {
  errorType: string;
  sourceText: string;
  explanation: string;
  revision: string;
  revisedSentence: string;
  positionStart: number;
  positionEnd: number;
}

export interface HighlightItem {
  type: string;
  location: string;
  explanation: string;
  encouragement: string;
}

export interface NotebookSummary {
  totalItems: number;
  reviewedItems: number;
  pendingReviewCount: number;
  dominantErrorType: string;
}

export type KnowledgeStatus = "disabled" | "fallback" | "enabled";

export interface KnowledgeSource {
  id: string;
  title: string;
  type: string;
  score: number;
  rerankScore?: number | null;
  ieltsTask?: string | null;
  excerpt: string;
  selectionReason: string;
}

export interface AssessmentMeta {
  wordCount: number;
  sourceMode: string;
  generatedAt: string;
  knowledgeStatus: KnowledgeStatus;
  knowledgeTask: string | null;
  knowledgeWarnings: string[];
  knowledgeSources: KnowledgeSource[];
}

export interface RadarPoint {
  dimension: string;
  score: number;
}

export interface ComparisonPoint {
  dimension: string;
  score: number;
  ieltsTarget: number;
}

export interface HeatmapPoint {
  section: string;
  value: number;
}

export interface ErrorPortraitPoint {
  type: string;
  count: number;
}

export interface WordCloudPoint {
  word?: string;
  text?: string;
  weight: number;
}

export interface ChartsData {
  radar: RadarPoint[];
  heatmap: HeatmapPoint[];
  trendLine: number[];
  wordCloud: WordCloudPoint[];
  comparison: ComparisonPoint[];
  errorPortrait: ErrorPortraitPoint[];
}

export interface ProfileDominantError {
  type: string;
  count: number;
  share: number;
}

export interface AssessmentCompletedResponse {
  assessmentId: string;
  essayText: string;
  meta: AssessmentMeta;
  report: {
    grammar_accuracy: ReportDimension;
    task_response: ReportDimension;
    coherence_cohesion: ReportDimension;
    lexical_resource: ReportDimension;
  };
  suggestions: SuggestionItem[];
  highlights: HighlightItem[];
  chartsData: ChartsData;
  profile: ProfileResponse;
  notebookSummary: NotebookSummary;
}

export interface AssessmentCreateResponse {
  assessmentId: string;
  status: AssessmentStatus;
  etaSeconds: number;
}

export interface AssessmentProgressResponse {
  assessmentId: string;
  status: AssessmentStatus;
  progressMessage: string;
  progressPercent: number;
  errorMessage: string | null;
}

export interface HistoryItem {
  assessmentId: string;
  topic: string;
  taskType: TaskType;
  overallScore: number;
  status: AssessmentStatus;
  createdAt: string;
}

export interface NotebookItem {
  id: string;
  assessmentId: string;
  sourceEssayTitle: string;
  taskType: TaskType;
  errorType: string;
  sourceText: string;
  explanation: string;
  revision: string;
  revisedSentence: string;
  status: string;
  createdAt: string;
}

export interface NotebookResponse {
  summary: NotebookSummary;
  items: NotebookItem[];
}

export interface ProfileResponse {
  averageScore: number;
  recentScores: number[];
  dominantErrors: ProfileDominantError[];
  learningPath: string[];
  nextTargetScore: number;
  summaryNarrative: string;
}
