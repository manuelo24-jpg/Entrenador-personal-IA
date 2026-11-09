import React, { useState, useEffect } from "react";
import { Upload, CheckCircle2, AlertCircle, Loader2, ArrowLeft, Video } from "lucide-react";
import {
  ExerciseCatalogItem,
  fetchJobStatus,
  uploadVideoFile,
} from "../api/client";
import { LEVEL_LABELS } from "../theme";

interface UploadVideoViewProps {
  exercise: ExerciseCatalogItem;
  level: string;
  onBack: () => void;
  onCompleted: (videoId: string) => void;
}

export const UploadVideoView: React.FC<UploadVideoViewProps> = ({
  exercise,
  level,
  onBack,
  onCompleted,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [title, setTitle] = useState<string>(
    `${exercise.display_name} — Nivel ${LEVEL_LABELS[level]?.label || level}`
  );
  const [jobId, setJobId] = useState<string | null>(null);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [status, setStatus] = useState<string>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    if (!jobId || !videoId) return;
    const timer = setInterval(async () => {
      try {
        const st = await fetchJobStatus(jobId);
        setProgress(st.progress);
        setStatus(st.status);
        if (st.status === "done") {
          clearInterval(timer);
          onCompleted(videoId);
        } else if (st.status === "error") {
          clearInterval(timer);
          setErrorMsg(st.error_message || "Error durante el procesado del vídeo");
        }
      } catch (err: any) {
        setErrorMsg(err.message || "Error consultando el progreso");
      }
    }, 900);
    return () => clearInterval(timer);
  }, [jobId, videoId, onCompleted]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setErrorMsg(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    try {
      setStatus("uploading");
      setProgress(2);
      setErrorMsg(null);
      const res = await uploadVideoFile(
        selectedFile,
        exercise.exercise,
        level,
        title,
        "upload"
      );
      setVideoId(res.video_id);
      setJobId(res.job_id);
      setStatus("processing");
    } catch (err: any) {
      setStatus("error");
      setErrorMsg(err.message || "Fallo al subir el vídeo");
    }
  };

  const levelMeta = LEVEL_LABELS[level] || LEVEL_LABELS.medium;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-5">
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:text-epia-500 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Volver al configurador
        </button>
        <div className="flex items-center gap-2 text-xs sm:text-sm bg-white dark:bg-slate-900 px-3.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span>{exercise.icon}</span>
          <span className="font-bold text-epia-900 dark:text-white">{exercise.display_name}</span>
          <span className="text-slate-300">·</span>
          <span className="text-epia-500 font-semibold">
            {levelMeta.badge} {levelMeta.label}
          </span>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-6">
        <div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-epia-900 dark:text-white flex items-center gap-2">
            <Video className="w-6 h-6 text-epia-500" />
            Analizar vídeo de entrenamiento
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Sube tu grabación para que EPIA genere el vídeo corregido con esqueleto biomecánico, ángulos, conteo de repeticiones e informe de errores.
          </p>
        </div>

        <div className="grid sm:grid-cols-3 gap-3 text-xs bg-slate-50 dark:bg-slate-800/70 p-4 rounded-xl border border-slate-200/80 dark:border-slate-700 text-slate-700 dark:text-slate-300">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-epia-500 shrink-0 mt-0.5" />
            <span>
              <strong>Vista recomendada:</strong>{" "}
              {exercise.preferred_view === "side" ? "Perfil lateral completo" : "Vista frontal"}
            </span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-epia-500 shrink-0 mt-0.5" />
            <span>
              <strong>Encuadre:</strong> Cuerpo entero visible de pies a cabeza sin cortes.
            </span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-epia-500 shrink-0 mt-0.5" />
            <span>
              <strong>Privacidad:</strong> El vídeo se procesa 100 % en tu equipo local.
            </span>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6 items-start">
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                Título de la sesión
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-epia-900 dark:text-white focus:outline-none focus:border-epia-500 focus:bg-white transition"
                placeholder="Ej. Serie de flexiones — Lunes"
              />
            </div>

            <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-epia-500 rounded-2xl p-8 cursor-pointer bg-slate-50/70 dark:bg-slate-800/40 hover:bg-epia-50/40 transition text-center">
              <Upload className="w-9 h-9 text-epia-500 mb-2.5" />
              <span className="text-sm font-bold text-epia-900 dark:text-white">
                {selectedFile
                  ? selectedFile.name
                  : "Haz clic o arrastra un vídeo (.mp4, .webm, .mov)"}
              </span>
              <span className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Soporta grabaciones desde móvil o webcam
              </span>
              <input
                type="file"
                accept="video/mp4,video/webm,video/quicktime,video/*"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>
          </div>

          <div className="space-y-4">
            {previewUrl ? (
              <div className="rounded-xl overflow-hidden bg-slate-900 border border-slate-200 dark:border-slate-700 max-h-64 flex justify-center">
                <video src={previewUrl} controls className="max-h-64 object-contain" />
              </div>
            ) : (
              <div className="h-56 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex flex-col items-center justify-center text-slate-400 text-xs p-6 text-center">
                <Video className="w-8 h-8 mb-2 stroke-1" />
                <span>La vista previa del vídeo aparecerá aquí tras seleccionarlo</span>
              </div>
            )}
          </div>
        </div>

        {errorMsg && (
          <div className="p-4 rounded-xl bg-red-50 dark:bg-epia-bad/20 border border-epia-bad/40 text-sm text-epia-bad dark:text-red-200 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-epia-bad shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {(status === "uploading" || status === "processing" || status === "queued") && (
          <div className="space-y-2 bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2 text-epia-500 font-semibold">
                <Loader2 className="w-4 h-4 animate-spin" />
                Procesando pose y biomecánica con YOLO11...
              </span>
              <span className="font-bold text-epia-900 dark:text-white">{progress}%</span>
            </div>
            <div className="w-full h-2.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
              <div
                className="h-full bg-epia-500 transition-all duration-300"
                style={{ width: `${Math.max(5, progress)}%` }}
              />
            </div>
          </div>
        )}

        <div className="flex justify-end pt-2 border-t border-slate-100 dark:border-slate-800">
          <button
            disabled={
              !selectedFile ||
              status === "uploading" ||
              status === "processing" ||
              status === "queued"
            }
            onClick={handleUpload}
            className="px-6 py-3 rounded-xl bg-epia-500 hover:bg-epia-700 disabled:opacity-40 text-white font-bold text-sm shadow-md shadow-epia-500/20 transition flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Analizar y generar vídeo corregido
          </button>
        </div>
      </div>
    </div>
  );
};
