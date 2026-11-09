import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  ArrowLeft,
  Camera,
  Volume2,
  VolumeX,
  Play,
  Square,
  RotateCcw,
  Loader2,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import {
  ExerciseCatalogItem,
  LiveFrameAnalysis,
  fetchJobStatus,
  uploadVideoFile,
} from "../api/client";
import { EPIA_THEME, LEVEL_LABELS, SKELETON_EDGES } from "../theme";

interface LiveSessionViewProps {
  exercise: ExerciseCatalogItem;
  level: string;
  onBack: () => void;
  onFinishedVideo: (videoId: string) => void;
}

export const LiveSessionView: React.FC<LiveSessionViewProps> = ({
  exercise,
  level,
  onBack,
  onFinishedVideo,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  const lastSpokenRef = useRef<{ text: string; time: number }>({ text: "", time: 0 });

  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [analysis, setAnalysis] = useState<LiveFrameAnalysis | null>(null);
  const [savingVideo, setSavingVideo] = useState(false);
  const [saveProgress, setSaveProgress] = useState(0);

  const speakMessage = useCallback(
    (text: string) => {
      if (!voiceEnabled || typeof window === "undefined" || !("speechSynthesis" in window)) {
        return;
      }
      const now = Date.now();
      if (text === lastSpokenRef.current.text && now - lastSpokenRef.current.time < 5500) {
        return;
      }
      if (now - lastSpokenRef.current.time < 3200) {
        return;
      }
      lastSpokenRef.current = { text, time: now };
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = "es-ES";
      utter.rate = 1.05;
      window.speechSynthesis.speak(utter);
    },
    [voiceEnabled]
  );

  const drawOverlay = useCallback((data: LiveFrameAnalysis) => {
    const canvas = overlayCanvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const w = video.videoWidth || 640;
    const h = video.videoHeight || 360;
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, w, h);

    if (data.ideal_line_norm && data.ideal_line_norm.length === 2) {
      const [p1, p2] = data.ideal_line_norm;
      ctx.save();
      ctx.strokeStyle = EPIA_THEME.cyan400;
      ctx.lineWidth = 2.5;
      ctx.setLineDash([6, 6]);
      ctx.beginPath();
      ctx.moveTo(p1.x * w, p1.y * h);
      ctx.lineTo(p2.x * w, p2.y * h);
      ctx.stroke();
      ctx.restore();
    }

    const kpts = data.keypoints || [];
    if (kpts.length < 17) return;

    for (const [i, j] of SKELETON_EDGES) {
      const ki = kpts[i];
      const kj = kpts[j];
      if (!ki || !kj || ki.conf < 0.35 || kj.conf < 0.35) continue;

      let stroke: string = EPIA_THEME.blue500;
      if (ki.state === "bad" || kj.state === "bad") stroke = EPIA_THEME.bad;
      else if (ki.state === "warn" || kj.state === "warn") stroke = EPIA_THEME.warn;

      ctx.strokeStyle = stroke;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(ki.x * w, ki.y * h);
      ctx.lineTo(kj.x * w, kj.y * h);
      ctx.stroke();
    }

    for (let idx = 5; idx < 17; idx++) {
      const kp = kpts[idx];
      if (!kp || kp.conf < 0.35) continue;
      const cx = kp.x * w;
      const cy = kp.y * h;
      ctx.fillStyle =
        kp.state === "bad"
          ? EPIA_THEME.bad
          : kp.state === "warn"
          ? EPIA_THEME.warn
          : EPIA_THEME.cyan400;
      ctx.beginPath();
      ctx.arc(cx, cy, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    let stream: MediaStream | null = null;
    let intervalId: number | null = null;

    async function initCameraAndWs() {
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 360 }, facingMode: "user" },
          audio: false,
        });

        if (cancelled) {
          mediaStream.getTracks().forEach((t) => t.stop());
          return;
        }

        stream = mediaStream;
        const videoEl = videoRef.current;
        if (videoEl) {
          if (videoEl.srcObject !== mediaStream) {
            videoEl.srcObject = mediaStream;
          }
          try {
            await videoEl.play();
          } catch (playErr: any) {
            if (playErr?.name !== "AbortError") {
              throw playErr;
            }
          }
          if (!cancelled) {
            setCameraError(null);
            setCameraReady(true);
          }
        }

        if (cancelled) return;

        const proto = window.location.protocol === "https:" ? "wss" : "ws";
        const wsUrl = `${proto}://${window.location.host}/ws/live?exercise=${encodeURIComponent(
          exercise.exercise
        )}&level=${encodeURIComponent(level)}`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onmessage = (ev) => {
          if (cancelled) return;
          try {
            const payload = JSON.parse(ev.data);
            if (payload.type === "frame_analysis") {
              setAnalysis(payload);
              drawOverlay(payload);
              if (payload.active_errors?.length > 0) {
                speakMessage(payload.active_errors[0].message);
              }
            }
          } catch {
            // ignore malformed frame message
          }
        };

        intervalId = window.setInterval(() => {
          if (
            cancelled ||
            !wsRef.current ||
            wsRef.current.readyState !== WebSocket.OPEN ||
            !videoRef.current ||
            videoRef.current.readyState < 2
          ) {
            return;
          }
          const capCanvas = captureCanvasRef.current;
          if (!capCanvas) return;
          const vw = 640;
          const vh = 360;
          capCanvas.width = vw;
          capCanvas.height = vh;
          const ctx = capCanvas.getContext("2d");
          if (!ctx) return;
          ctx.drawImage(videoRef.current, 0, 0, vw, vh);
          const dataUrl = capCanvas.toDataURL("image/jpeg", 0.7);
          wsRef.current.send(
            JSON.stringify({
              frame: dataUrl,
              timestamp: performance.now() / 1000.0,
            })
          );
        }, 120);
      } catch (err: any) {
        if (cancelled || err?.name === "AbortError") return;
        setCameraError(
          err.message ||
            "No se pudo acceder a la webcam. Verifica los permisos del navegador."
        );
      }
    }

    initCameraAndWs();

    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, [exercise.exercise, level, drawOverlay, speakMessage]);

  const startCountdownAndRecord = () => {
    setCountdown(3);
    speakMessage("Preparado: tres, dos, uno, empieza");
    let current = 3;
    const timer = window.setInterval(() => {
      current -= 1;
      if (current > 0) {
        setCountdown(current);
      } else {
        clearInterval(timer);
        setCountdown(null);
        beginRecording();
      }
    }, 1000);
  };

  const beginRecording = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "reset" }));
    }
    const stream = videoRef.current?.srcObject as MediaStream | null;
    if (!stream) return;

    recordedChunksRef.current = [];
    const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
      ? "video/webm;codecs=vp9"
      : "video/webm";
    const recorder = new MediaRecorder(stream, { mimeType });
    recorder.ondataavailable = (ev) => {
      if (ev.data && ev.data.size > 0) {
        recordedChunksRef.current.push(ev.data);
      }
    };
    recorder.start(500);
    mediaRecorderRef.current = recorder;
    setIsRecording(true);
  };

  const stopAndFinishSession = async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;

    setIsRecording(false);
    setSavingVideo(true);
    setSaveProgress(10);

    await new Promise<void>((resolve) => {
      recorder.onstop = () => resolve();
      recorder.stop();
    });

    const blob = new Blob(recordedChunksRef.current, { type: "video/webm" });
    try {
      const res = await uploadVideoFile(
        blob,
        exercise.exercise,
        level,
        `Directo: ${exercise.display_name} (${LEVEL_LABELS[level]?.label || level})`,
        "live",
        "directo_epia.webm"
      );

      const poll = window.setInterval(async () => {
        try {
          const st = await fetchJobStatus(res.job_id);
          setSaveProgress(st.progress);
          if (st.status === "done") {
            clearInterval(poll);
            onFinishedVideo(res.video_id);
          } else if (st.status === "error") {
            clearInterval(poll);
            setSavingVideo(false);
          }
        } catch {
          clearInterval(poll);
          setSavingVideo(false);
        }
      }, 900);
    } catch {
      setSavingVideo(false);
    }
  };

  const resetCounters = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "reset" }));
    }
  };

  const levelMeta = LEVEL_LABELS[level] || LEVEL_LABELS.medium;

  return (
    <div className="max-w-7xl mx-auto px-4 py-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:text-epia-500 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Volver al configurador
        </button>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setVoiceEnabled((v) => !v)}
            className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 border transition ${
              voiceEnabled
                ? "bg-epia-50 dark:bg-epia-500/20 border-epia-500 text-epia-500 dark:text-white"
                : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-500"
            }`}
          >
            {voiceEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            Voz {voiceEnabled ? "Activada" : "Silenciada"}
          </button>

          <button
            onClick={resetCounters}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 flex items-center gap-1.5 shadow-sm"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reiniciar serie
          </button>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main Live Camera Canvas */}
        <div className="lg:col-span-2 relative rounded-2xl overflow-hidden bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-lg aspect-video flex items-center justify-center">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            onLoadedMetadata={() => {
              setCameraError(null);
              setCameraReady(true);
            }}
            className="w-full h-full object-cover"
          />
          <canvas
            ref={overlayCanvasRef}
            className="absolute inset-0 w-full h-full pointer-events-none"
          />
          <canvas ref={captureCanvasRef} className="hidden" />

          {/* Placement Assistant Banner */}
          {analysis && (
            <div
              className={`absolute top-4 left-4 right-4 px-4 py-2.5 rounded-xl backdrop-blur-md border text-xs sm:text-sm font-semibold flex items-center justify-between shadow-sm ${
                analysis.placement_status === "ok"
                  ? "bg-white/90 dark:bg-slate-900/90 border-epia-ok text-epia-900 dark:text-white"
                  : "bg-white/95 dark:bg-slate-900/90 border-epia-warn text-epia-900 dark:text-white"
              }`}
            >
              <span className="flex items-center gap-2">
                {analysis.placement_status === "ok" ? (
                  <CheckCircle2 className="w-4 h-4 text-epia-ok shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-epia-warn shrink-0" />
                )}
                {analysis.placement_message}
              </span>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                Vista: {analysis.dominant_side === "left" ? "Izquierda" : "Derecha"}
              </span>
            </div>
          )}

          {countdown !== null && (
            <div className="absolute inset-0 bg-slate-900/75 backdrop-blur-sm flex items-center justify-center">
              <span className="text-8xl font-extrabold text-white animate-ping">
                {countdown}
              </span>
            </div>
          )}

          {cameraError && (
            <div className="absolute inset-0 bg-white/95 dark:bg-slate-900/95 p-6 flex flex-col items-center justify-center text-center">
              <Camera className="w-12 h-12 text-epia-bad mb-3" />
              <p className="text-base font-bold text-epia-900 dark:text-white">
                {cameraError}
              </p>
            </div>
          )}
        </div>

        {/* Right Telemetry Panel (Clean White Card) */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col justify-between space-y-6">
          <div className="space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
              <div>
                <span className="text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                  Entrenamiento en vivo
                </span>
                <h3 className="text-xl font-extrabold text-epia-900 dark:text-white flex items-center gap-2 mt-0.5">
                  <span>{exercise.icon}</span>
                  <span>{exercise.display_name}</span>
                </h3>
              </div>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-epia-50 dark:bg-slate-800 text-epia-500 border border-epia-500/20">
                {levelMeta.badge} {levelMeta.label}
              </span>
            </div>

            {/* Rep Counter / Hold Timer */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-50 dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700 rounded-xl p-4 text-center">
                <span className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">
                  {exercise.is_isometric ? "Tiempo Efectivo" : "Repeticiones"}
                </span>
                <div className="text-4xl font-extrabold text-epia-900 dark:text-white mt-1">
                  {exercise.is_isometric
                    ? `${analysis?.hold_seconds?.toFixed(1) || "0.0"}s`
                    : analysis?.reps_total ?? 0}
                </div>
                {!exercise.is_isometric && (
                  <div className="text-xs mt-1 space-x-2">
                    <span className="text-epia-ok font-bold">
                      ✓ {analysis?.reps_ok ?? 0}
                    </span>
                    <span className="text-epia-warn font-bold">
                      ~ {analysis?.reps_partial ?? 0}
                    </span>
                    <span className="text-epia-bad font-bold">
                      ✗ {analysis?.reps_bad ?? 0}
                    </span>
                  </div>
                )}
              </div>

              <div className="bg-slate-50 dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700 rounded-xl p-4 text-center">
                <span className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">
                  Puntuación
                </span>
                <div className="text-4xl font-extrabold text-epia-500 mt-1">
                  {Math.round(analysis?.current_score ?? 100)}
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Fase:{" "}
                  <strong className="text-epia-900 dark:text-white">
                    {analysis?.phase || "UP"}
                  </strong>
                </div>
              </div>
            </div>

            {/* Live Joint Angles */}
            <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200/70 dark:border-slate-700 rounded-xl p-4 space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Ángulos articulares en tiempo real
              </span>
              {analysis && Object.keys(analysis.angles).length > 0 ? (
                <div className="grid grid-cols-2 gap-2 pt-1">
                  {Object.entries(analysis.angles).map(([k, val]) => (
                    <div
                      key={k}
                      className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-3 py-2 rounded-lg flex items-center justify-between text-xs"
                    >
                      <span className="text-slate-500 dark:text-slate-400">
                        {k.replace("_angle", "")}
                      </span>
                      <span className="font-bold text-epia-900 dark:text-white">
                        {Math.round(val)}°
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Colócate frente a la cámara para medir ángulos...
                </p>
              )}
            </div>

            {/* Active Feedback Messages */}
            <div className="space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Corrección postural instantánea
              </span>
              {analysis?.active_errors && analysis.active_errors.length > 0 ? (
                <div className="space-y-2">
                  {analysis.active_errors.map((err, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-xl bg-red-50 dark:bg-epia-bad/20 border border-epia-bad/50 text-xs font-semibold text-epia-bad dark:text-red-200 flex items-center gap-2"
                    >
                      <AlertTriangle className="w-4 h-4 text-epia-bad shrink-0" />
                      <span>{err.message}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-3 rounded-xl bg-emerald-50 dark:bg-epia-ok/20 border border-epia-ok/40 text-xs font-semibold text-epia-ok dark:text-emerald-200 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-epia-ok shrink-0" />
                  <span>Postura alineada correctamente</span>
                </div>
              )}
            </div>
          </div>

          {/* Recording Controls */}
          <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
            {savingVideo ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-epia-500 font-semibold">
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generando vídeo final H.264...
                  </span>
                  <span>{saveProgress}%</span>
                </div>
                <div className="w-full h-2.5 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-epia-500 transition-all"
                    style={{ width: `${Math.max(10, saveProgress)}%` }}
                  />
                </div>
              </div>
            ) : !isRecording ? (
              <button
                disabled={!cameraReady || countdown !== null}
                onClick={startCountdownAndRecord}
                className="w-full py-3.5 rounded-xl bg-epia-500 hover:bg-epia-700 disabled:opacity-40 text-white font-bold text-sm shadow-md shadow-epia-500/20 transition flex items-center justify-center gap-2"
              >
                <Play className="w-4 h-4" />
                Iniciar grabación de serie (3-2-1)
              </button>
            ) : (
              <button
                onClick={stopAndFinishSession}
                className="w-full py-3.5 rounded-xl bg-epia-bad hover:bg-red-700 text-white font-bold text-sm shadow-md transition flex items-center justify-center gap-2"
              >
                <Square className="w-4 h-4" />
                Terminar y guardar vídeo corregido
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
