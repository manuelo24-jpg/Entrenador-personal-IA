export interface AuthUser {
  id: string;
  name: string;
  email: string;
  created_at?: string | null;
}

const TOKEN_STORAGE_KEY = "epia_auth_token";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setAuthToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...(extra || {}) };
  const token = getAuthToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function registerRequest(
  name: string,
  email: string,
  password: string
): Promise<{ token: string; user: AuthUser }> {
  const res = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Error al registrar usuario" }));
    throw new Error(err.detail || "Error al registrar usuario");
  }
  return res.json();
}

export async function loginRequest(
  email: string,
  password: string
): Promise<{ token: string; user: AuthUser }> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Credenciales inválidas" }));
    throw new Error(err.detail || "Credenciales inválidas");
  }
  return res.json();
}

export async function fetchCurrentUser(): Promise<AuthUser | null> {
  const token = getAuthToken();
  if (!token) return null;
  const res = await fetch("/api/auth/me", {
    headers: authHeaders(),
  });
  if (!res.ok) {
    setAuthToken(null);
    return null;
  }
  const data = await res.json();
  return data.user || null;
}

export interface LevelConfig {
  key: string;
  display_name: string;
  rules_enabled: string[];
  up_threshold?: number;
  down_threshold?: number;
  target_hold_seconds?: number;
}

export interface ExerciseCatalogItem {
  exercise: string;
  display_name: string;
  description: string;
  icon: string;
  preferred_view: "side" | "front";
  is_isometric: boolean;
  required_keypoints: string[];
  levels: Record<string, LevelConfig>;
  messages: Record<string, string>;
}

export interface RepErrorItem {
  rule_id: string;
  message: string;
  severity: number;
}

export interface RepItem {
  index: number;
  start_t: number;
  end_t: number;
  duration_s: number;
  min_angle: number;
  max_angle: number;
  score: number;
  status: "ok" | "partial" | "bad";
  errors: RepErrorItem[];
}

export interface ErrorTimelineEvent {
  timestamp: number;
  rule_id: string;
  message: string;
  severity: number;
}

export interface SessionReport {
  exercise: string;
  level: string;
  reps_total: number;
  reps_ok: number;
  reps_partial: number;
  reps_bad: number;
  hold_seconds: number;
  score_avg: number;
  top_errors: { rule_id: string; message: string; count: number }[];
  fatigue_detected: boolean;
  advice: string;
  reps: RepItem[];
  error_timeline: ErrorTimelineEvent[];
}

export interface VideoSummary {
  id: string;
  title: string;
  exercise: string;
  level: string;
  source: "upload" | "live";
  duration_s: number;
  fps: number;
  created_at: string;
  favorite: boolean;
  notes: string;
  tags: string[];
  status: "queued" | "processing" | "done" | "error";
  has_thumbnail: boolean;
  reps_total: number;
  reps_ok: number;
  reps_partial: number;
  reps_bad: number;
  hold_seconds: number;
  score_avg: number;
  report?: SessionReport;
}

export interface JobStatus {
  job_id: string;
  video_id: string;
  exercise: string;
  level: string;
  status: "queued" | "processing" | "done" | "error";
  progress: number;
  error_message?: string | null;
}

export interface LiveKeypoint {
  index: number;
  x: number;
  y: number;
  conf: number;
  state: "ok" | "warn" | "bad";
}

export interface LiveFrameAnalysis {
  type: "frame_analysis";
  timestamp: number;
  state: "NO_PERSON" | "POSITIONING" | "ACTIVE";
  phase: string;
  primary_angle: number;
  angles: Record<string, number>;
  reps_total: number;
  reps_ok: number;
  reps_partial: number;
  reps_bad: number;
  hold_seconds: number;
  current_score: number;
  active_errors: RepErrorItem[];
  placement_status: string;
  placement_message: string;
  dominant_side: string;
  keypoints: LiveKeypoint[];
  ideal_line_norm?: { x: number; y: number }[] | null;
}

export interface ProgressStats {
  total_sessions: number;
  total_reps: number;
  total_reps_ok: number;
  total_hold_seconds: number;
  avg_score: number;
  best_score: number;
  history: {
    id: string;
    title: string;
    date: string;
    exercise: string;
    level: string;
    score_avg: number;
    reps_total: number;
    reps_ok: number;
    hold_seconds: number;
  }[];
  by_exercise: {
    exercise: string;
    sessions: number;
    reps_total: number;
    best_score: number;
    max_reps: number;
  }[];
  frequent_errors: {
    rule_id: string;
    message: string;
    count: number;
  }[];
}

export async function fetchExercises(): Promise<ExerciseCatalogItem[]> {
  const res = await fetch("/api/exercises", { headers: authHeaders() });
  if (!res.ok) throw new Error("Error al cargar el catálogo de ejercicios");
  return res.json();
}

export async function uploadVideoFile(
  file: File | Blob,
  exercise: string,
  level: string,
  title?: string,
  source: "upload" | "live" = "upload",
  filename = "sesion_epia.mp4"
): Promise<{ video_id: string; job_id: string; status: string }> {
  const form = new FormData();
  form.append("file", file, file instanceof File ? file.name : filename);
  form.append("exercise", exercise);
  form.append("level", level);
  if (title) form.append("title", title);
  form.append("source", source);

  const res = await fetch("/api/videos", {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Error subiendo vídeo" }));
    throw new Error(err.detail || "Error subiendo vídeo");
  }
  return res.json();
}

export async function fetchJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`/api/jobs/${jobId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("No se pudo consultar el estado del trabajo");
  return res.json();
}

export async function fetchVideos(params?: {
  exercise?: string;
  level?: string;
  favorite?: boolean;
  q?: string;
}): Promise<VideoSummary[]> {
  const search = new URLSearchParams();
  if (params?.exercise) search.set("exercise", params.exercise);
  if (params?.level) search.set("level", params.level);
  if (params?.favorite !== undefined) search.set("favorite", String(params.favorite));
  if (params?.q) search.set("q", params.q);

  const query = search.toString();
  const res = await fetch(`/api/videos${query ? `?${query}` : ""}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Error cargando biblioteca de vídeos");
  return res.json();
}

export async function fetchVideoDetail(videoId: string): Promise<VideoSummary> {
  const res = await fetch(`/api/videos/${videoId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Vídeo no encontrado");
  return res.json();
}

export async function patchVideo(
  videoId: string,
  payload: { title?: string; favorite?: boolean; notes?: string; tags?: string[] }
): Promise<VideoSummary> {
  const res = await fetch(`/api/videos/${videoId}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("No se pudo actualizar el vídeo");
  return res.json();
}

export async function deleteVideoById(videoId: string): Promise<void> {
  const res = await fetch(`/api/videos/${videoId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("No se pudo eliminar el vídeo");
}

export async function reprocessVideoById(
  videoId: string,
  level: string,
  exercise?: string
): Promise<{ video_id: string; job_id: string; status: string }> {
  const res = await fetch(`/api/videos/${videoId}/reprocess`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ level, exercise }),
  });
  if (!res.ok) throw new Error("No se pudo lanzar el reprocesado");
  return res.json();
}

export async function fetchProgressStats(): Promise<ProgressStats> {
  const res = await fetch("/api/stats", { headers: authHeaders() });
  if (!res.ok) throw new Error("No se pudieron cargar las estadísticas");
  return res.json();
}
