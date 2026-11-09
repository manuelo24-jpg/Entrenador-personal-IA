import React, { useEffect, useState } from "react";
import {
  BarChart3,
  Trophy,
  Activity,
  AlertTriangle,
  Clock,
  CheckCircle2,
} from "lucide-react";
import {
  ExerciseCatalogItem,
  ProgressStats,
  fetchProgressStats,
} from "../api/client";

interface ProgressViewProps {
  exercises: ExerciseCatalogItem[];
  onOpenVideo: (videoId: string) => void;
}

export const ProgressView: React.FC<ProgressViewProps> = ({
  exercises,
  onOpenVideo,
}) => {
  const [stats, setStats] = useState<ProgressStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProgressStats()
      .then((d) => setStats(d))
      .finally(() => setLoading(false));
  }, []);

  if (loading || !stats) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12 text-center text-slate-500">
        Calculando evolución y récords personales...
      </div>
    );
  }

  const exerciseMap = Object.fromEntries(exercises.map((e) => [e.exercise, e]));

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-epia-900 dark:text-white flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-epia-500" />
          Evolución y Estadísticas Biomecánicas
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Seguimiento de calidad técnica, repeticiones acumuladas, récords personales y áreas de mejora.
        </p>
      </div>

      {/* Top KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
          <span className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">
            Sesiones Completadas
          </span>
          <div className="text-3xl font-extrabold text-epia-900 dark:text-white mt-1">
            {stats.total_sessions}
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
          <span className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">
            Repeticiones Totales
          </span>
          <div className="text-3xl font-extrabold text-epia-900 dark:text-white mt-1">
            {stats.total_reps}
          </div>
          <span className="text-xs text-epia-ok font-semibold">
            ✓ {stats.total_reps_ok} óptimas
          </span>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
          <span className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">
            Puntuación Media
          </span>
          <div className="text-3xl font-extrabold text-epia-500 mt-1">
            {stats.avg_score}/100
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
          <span className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold flex items-center gap-1">
            <Trophy className="w-3.5 h-3.5 text-amber-500" /> Mejor Puntuación
          </span>
          <div className="text-3xl font-extrabold text-amber-500 mt-1">
            {stats.best_score}/100
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
          <span className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold flex items-center gap-1">
            <Clock className="w-3.5 h-3.5 text-epia-500" /> Tiempo Isométrico
          </span>
          <div className="text-3xl font-extrabold text-epia-900 dark:text-white mt-1">
            {stats.total_hold_seconds}s
          </div>
        </div>
      </div>

      {/* Score Progression Chart & Most Frequent Errors */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <h3 className="text-base font-bold text-epia-900 dark:text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-epia-500" />
            Evolución de puntuación por sesión
          </h3>

          {stats.history.length === 0 ? (
            <p className="text-xs text-slate-500 py-8 text-center">
              Aún no hay sesiones finalizadas para graficar la curva de aprendizaje.
            </p>
          ) : (
            <div className="space-y-3 pt-2">
              {stats.history.slice(-10).map((item) => {
                const exMeta = exerciseMap[item.exercise];
                return (
                  <div
                    key={item.id}
                    onClick={() => onOpenVideo(item.id)}
                    className="space-y-1 cursor-pointer group"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-epia-900 dark:text-white group-hover:text-epia-500 transition">
                        {exMeta?.icon} {item.title}
                      </span>
                      <span className="font-bold text-epia-500">
                        {item.score_avg} pts ·{" "}
                        {item.hold_seconds > 0 && item.reps_total === 0
                          ? `${item.hold_seconds}s`
                          : `${item.reps_total} reps`}
                      </span>
                    </div>
                    <div className="w-full h-2.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-epia-500 transition-all"
                        style={{ width: `${Math.max(6, item.score_avg)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <h3 className="text-base font-bold text-epia-900 dark:text-white flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-epia-warn" />
            Errores posturales más frecuentes
          </h3>
          {stats.frequent_errors.length === 0 ? (
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800 text-xs text-slate-500 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-epia-ok shrink-0" />
              <span>Sin errores recurrentes registrados.</span>
            </div>
          ) : (
            <div className="space-y-2.5">
              {stats.frequent_errors.map((err) => (
                <div
                  key={err.rule_id}
                  className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-between gap-2 text-xs"
                >
                  <span className="text-epia-900 dark:text-white font-medium">
                    {err.message}
                  </span>
                  <span className="px-2.5 py-1 rounded-full bg-red-50 dark:bg-epia-bad/25 text-epia-bad font-bold shrink-0">
                    {err.count}x
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Personal Records by Exercise */}
      {stats.by_exercise.length > 0 && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <h3 className="text-base font-bold text-epia-900 dark:text-white flex items-center gap-2">
            <Trophy className="w-5 h-5 text-amber-500" />
            Desglose y récords por ejercicio
          </h3>
          <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {stats.by_exercise.map((b) => {
              const exMeta = exerciseMap[b.exercise];
              return (
                <div
                  key={b.exercise}
                  className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-2"
                >
                  <div className="font-bold text-epia-900 dark:text-white flex items-center gap-2">
                    <span>{exMeta?.icon || "🏋️"}</span>
                    <span>{exMeta?.display_name || b.exercise}</span>
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 space-y-1">
                    <div>
                      Sesiones:{" "}
                      <strong className="text-epia-900 dark:text-white">
                        {b.sessions}
                      </strong>
                    </div>
                    <div>
                      Mejor puntuación:{" "}
                      <strong className="text-epia-500">{b.best_score} pts</strong>
                    </div>
                    <div>
                      Máx. reps en serie:{" "}
                      <strong className="text-epia-900 dark:text-white">
                        {b.max_reps}
                      </strong>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
