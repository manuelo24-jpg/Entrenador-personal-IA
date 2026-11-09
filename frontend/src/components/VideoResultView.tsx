import React, { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Download,
  RefreshCw,
  Columns,
  Star,
  CheckCircle2,
  Clock,
  Award,
  Loader2,
} from "lucide-react";
import {
  VideoSummary,
  fetchJobStatus,
  fetchVideoDetail,
  patchVideo,
  reprocessVideoById,
} from "../api/client";
import { LEVEL_LABELS } from "../theme";

interface VideoResultViewProps {
  videoId: string;
  onBackToLibrary: () => void;
}

export const VideoResultView: React.FC<VideoResultViewProps> = ({
  videoId,
  onBackToLibrary,
}) => {
  const processedVideoRef = useRef<HTMLVideoElement | null>(null);
  const originalVideoRef = useRef<HTMLVideoElement | null>(null);

  const [video, setVideo] = useState<VideoSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [compareMode, setCompareMode] = useState(false);
  const [reprocessLevel, setReprocessLevel] = useState("medium");
  const [reprocessing, setReprocessing] = useState(false);
  const [reprocessProgress, setReprocessProgress] = useState(0);
  const [streamKey, setStreamKey] = useState(Date.now());

  const loadDetail = async () => {
    setLoading(true);
    try {
      const data = await fetchVideoDetail(videoId);
      setVideo(data);
      setReprocessLevel(data.level);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDetail();
  }, [videoId]);

  const seekToSecond = (sec: number) => {
    if (processedVideoRef.current) {
      processedVideoRef.current.currentTime = Math.max(0, sec);
      processedVideoRef.current.play().catch(() => {});
    }
    if (compareMode && originalVideoRef.current) {
      originalVideoRef.current.currentTime = Math.max(0, sec);
      originalVideoRef.current.play().catch(() => {});
    }
  };

  const handleToggleFavorite = async () => {
    if (!video) return;
    const updated = await patchVideo(video.id, { favorite: !video.favorite });
    setVideo(updated);
  };

  const handleReprocess = async () => {
    if (!video) return;
    setReprocessing(true);
    setReprocessProgress(5);
    try {
      const res = await reprocessVideoById(video.id, reprocessLevel, video.exercise);
      const poll = window.setInterval(async () => {
        const st = await fetchJobStatus(res.job_id);
        setReprocessProgress(st.progress);
        if (st.status === "done") {
          clearInterval(poll);
          setReprocessing(false);
          setStreamKey(Date.now());
          await loadDetail();
        } else if (st.status === "error") {
          clearInterval(poll);
          setReprocessing(false);
        }
      }, 900);
    } catch {
      setReprocessing(false);
    }
  };

  if (loading || !video) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-16 flex flex-col items-center justify-center text-slate-500">
        <Loader2 className="w-8 h-8 animate-spin text-epia-500 mb-2" />
        <span>Cargando informe biomecánico de EPIA...</span>
      </div>
    );
  }

  const report = video.report;
  const levelMeta = LEVEL_LABELS[video.level] || LEVEL_LABELS.medium;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Top Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBackToLibrary}
            className="px-3.5 py-2 rounded-xl bg-white dark:bg-slate-900 hover:bg-slate-100 text-sm font-semibold text-epia-900 dark:text-slate-100 flex items-center gap-2 border border-slate-200 dark:border-slate-800 shadow-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Biblioteca
          </button>
          <div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-epia-900 dark:text-white flex items-center gap-2">
              {video.title}
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Ejercicio:{" "}
              <strong className="text-epia-900 dark:text-white uppercase">
                {video.exercise}
              </strong>{" "}
              · Nivel:{" "}
              <span className="text-epia-500 font-semibold">
                {levelMeta.badge} {levelMeta.label}
              </span>{" "}
              · Duración: {video.duration_s}s
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleToggleFavorite}
            className={`px-3.5 py-2 rounded-xl text-xs font-semibold border flex items-center gap-1.5 transition ${
              video.favorite
                ? "bg-amber-50 dark:bg-amber-500/20 border-amber-400 text-amber-600 dark:text-amber-300"
                : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300"
            }`}
          >
            <Star className={`w-4 h-4 ${video.favorite ? "fill-amber-400 text-amber-400" : ""}`} />
            Favorito
          </button>

          <button
            onClick={() => setCompareMode((v) => !v)}
            className={`px-3.5 py-2 rounded-xl text-xs font-semibold border flex items-center gap-1.5 transition ${
              compareMode
                ? "bg-epia-500 border-epia-500 text-white"
                : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200"
            }`}
          >
            <Columns className="w-4 h-4" />
            {compareMode ? "Vista única" : "Comparar con original"}
          </button>

          <a
            href={`/api/videos/${video.id}/stream`}
            download={`${video.title.replace(/\s+/g, "_")}_EPIA.mp4`}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-epia-500 hover:bg-epia-700 text-white flex items-center gap-1.5 shadow-sm"
          >
            <Download className="w-4 h-4" />
            Descargar vídeo
          </a>
        </div>
      </div>

      {/* Video Player(s) */}
      <div
        className={`grid gap-4 ${
          compareMode ? "md:grid-cols-2" : "grid-cols-1 max-w-4xl mx-auto"
        }`}
      >
        <div className="bg-white dark:bg-slate-900 rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 shadow-md">
          <div className="bg-slate-50 dark:bg-slate-800 px-4 py-2 text-xs font-bold text-epia-500 border-b border-slate-200 dark:border-slate-700 flex justify-between">
            <span>Vídeo Corregido EPIA (Overlay Biomecánico)</span>
            <span>H.264</span>
          </div>
          <video
            key={`proc-${streamKey}`}
            ref={processedVideoRef}
            src={`/api/videos/${video.id}/stream?t=${streamKey}`}
            controls
            className="w-full max-h-[500px] object-contain bg-black"
          />
        </div>

        {compareMode && (
          <div className="bg-white dark:bg-slate-900 rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 shadow-md">
            <div className="bg-slate-50 dark:bg-slate-800 px-4 py-2 text-xs font-bold text-slate-500 border-b border-slate-200 dark:border-slate-700 flex justify-between">
              <span>Vídeo Original (Sin Correcciones)</span>
              <span>Original</span>
            </div>
            <video
              key={`orig-${streamKey}`}
              ref={originalVideoRef}
              src={`/api/videos/${video.id}/original?t=${streamKey}`}
              controls
              className="w-full max-h-[500px] object-contain bg-black"
            />
          </div>
        )}
      </div>

      {/* Interactive Error Timeline */}
      {report?.error_timeline && report.error_timeline.length > 0 && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-epia-500 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Línea de tiempo interactiva de correcciones (clic para saltar al instante)
            </h3>
            <span className="text-xs text-slate-500">
              {report.error_timeline.length} eventos detectados
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {report.error_timeline.map((ev, idx) => (
              <button
                key={idx}
                onClick={() => seekToSecond(ev.timestamp)}
                className="px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-800 hover:bg-epia-50 border border-epia-bad/40 text-xs flex items-center gap-2 transition"
              >
                <span className="font-mono font-bold text-epia-500">
                  {ev.timestamp.toFixed(1)}s
                </span>
                <span className="text-epia-900 dark:text-white">{ev.message}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Summary KPIs & Reprocess Card */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-epia-900 dark:text-white flex items-center gap-2">
              <Award className="w-5 h-5 text-epia-500" />
              Resumen de rendimiento e informe técnico
            </h3>
            {report?.fatigue_detected && (
              <span className="px-3 py-1 rounded-full bg-amber-50 dark:bg-epia-warn/20 border border-epia-warn text-xs font-bold text-epia-warn">
                ⚠ Fatiga detectada en últimas repeticiones
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 text-center">
              <span className="text-xs text-slate-500">Puntuación Media</span>
              <div className="text-3xl font-extrabold text-epia-500 mt-1">
                {video.score_avg}/100
              </div>
            </div>
            <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 text-center">
              <span className="text-xs text-slate-500">
                {video.hold_seconds > 0 && video.reps_total === 0 ? "Tiempo Plancha" : "Total Reps"}
              </span>
              <div className="text-3xl font-extrabold text-epia-900 dark:text-white mt-1">
                {video.hold_seconds > 0 && video.reps_total === 0
                  ? `${video.hold_seconds}s`
                  : video.reps_total}
              </div>
            </div>
            <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 text-center">
              <span className="text-xs text-slate-500">Correctas / Parciales</span>
              <div className="text-2xl font-extrabold text-epia-ok mt-1">
                ✓ {video.reps_ok}{" "}
                <span className="text-epia-warn text-lg">~ {video.reps_partial}</span>
              </div>
            </div>
            <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 text-center">
              <span className="text-xs text-slate-500">Con Errores</span>
              <div className="text-3xl font-extrabold text-epia-bad mt-1">
                ✗ {video.reps_bad}
              </div>
            </div>
          </div>

          {report?.advice && (
            <div className="p-4 rounded-xl bg-epia-50/70 dark:bg-slate-800 border border-epia-500/30 text-sm text-epia-900 dark:text-slate-100 flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-epia-500 shrink-0" />
              <span>
                <strong>Consejo del entrenador EPIA:</strong> {report.advice}
              </span>
            </div>
          )}

          {/* Repetitions Table */}
          {report?.reps && report.reps.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 text-slate-500 uppercase">
                    <th className="py-2.5 px-3"># Rep</th>
                    <th className="py-2.5 px-3">Instante</th>
                    <th className="py-2.5 px-3">Duración</th>
                    <th className="py-2.5 px-3">Rango Angular</th>
                    <th className="py-2.5 px-3">Puntuación</th>
                    <th className="py-2.5 px-3">Observaciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {report.reps.map((r) => (
                    <tr
                      key={r.index}
                      onClick={() => seekToSecond(r.start_t)}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/60 cursor-pointer transition"
                    >
                      <td className="py-2.5 px-3 font-bold text-epia-900 dark:text-white">
                        Rep {r.index}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-epia-500">
                        {r.start_t.toFixed(1)}s – {r.end_t.toFixed(1)}s
                      </td>
                      <td className="py-2.5 px-3 text-slate-500">
                        {r.duration_s.toFixed(2)}s
                      </td>
                      <td className="py-2.5 px-3 text-epia-900 dark:text-white">
                        {Math.round(r.min_angle)}° ↔ {Math.round(r.max_angle)}°
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2.5 py-0.5 rounded-full font-bold ${
                            r.status === "ok"
                              ? "bg-emerald-50 text-epia-ok"
                              : r.status === "partial"
                              ? "bg-amber-50 text-epia-warn"
                              : "bg-red-50 text-epia-bad"
                          }`}
                        >
                          {Math.round(r.score)} pts
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-600 dark:text-slate-300">
                        {r.errors.length > 0
                          ? r.errors.map((e) => e.message).join(" · ")
                          : "✓ Ejecución limpia"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right Side: Reprocess with Another Level */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <h3 className="text-base font-bold text-epia-900 dark:text-white flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-epia-500" />
              Reprocesar con otro nivel de exigencia
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Evalúa este mismo vídeo aplicando las reglas y tolerancias de otro nivel sin volver a subir el fichero.
            </p>

            <div className="space-y-2">
              {(["easy", "medium", "advanced"] as const).map((lvl) => {
                const m = LEVEL_LABELS[lvl];
                return (
                  <button
                    key={lvl}
                    onClick={() => setReprocessLevel(lvl)}
                    className={`w-full p-3 rounded-xl border text-left transition flex items-center justify-between ${
                      reprocessLevel === lvl
                        ? "bg-epia-50 dark:bg-epia-500/20 border-epia-500 text-epia-900 dark:text-white"
                        : "bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"
                    }`}
                  >
                    <span className="text-sm font-bold">
                      {m.badge} {m.label}
                    </span>
                    {video.level === lvl && (
                      <span className="text-[11px] px-2 py-0.5 rounded bg-white dark:bg-slate-900 text-epia-500 border border-slate-200 dark:border-slate-700 font-semibold">
                        Actual
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {reprocessing ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-epia-500 font-semibold">
                <span className="flex items-center gap-1.5">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Recalculando biomecánica...
                </span>
                <span>{reprocessProgress}%</span>
              </div>
              <div className="w-full h-2.5 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-epia-500 transition-all"
                  style={{ width: `${Math.max(8, reprocessProgress)}%` }}
                />
              </div>
            </div>
          ) : (
            <button
              onClick={handleReprocess}
              className="w-full py-3 rounded-xl bg-epia-500 hover:bg-epia-700 text-white text-sm font-bold shadow-md shadow-epia-500/20 transition flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Reprocesar en nivel {LEVEL_LABELS[reprocessLevel]?.label}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
