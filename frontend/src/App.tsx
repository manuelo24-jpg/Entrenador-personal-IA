import React, { useEffect, useState } from "react";
import {
  Camera,
  Upload,
  CheckCircle2,
  Sliders,
  Sparkles,
  Eye,
  Loader2,
  ArrowRight,
  Target,
} from "lucide-react";
import {
  AuthUser,
  ExerciseCatalogItem,
  fetchCurrentUser,
  fetchExercises,
  setAuthToken,
} from "./api/client";
import { AuthView } from "./components/AuthView";
import { Navbar, NavTab } from "./components/Navbar";
import { LiveSessionView } from "./components/LiveSessionView";
import { UploadVideoView } from "./components/UploadVideoView";
import { VideoResultView } from "./components/VideoResultView";
import { LibraryView } from "./components/LibraryView";
import { ProgressView } from "./components/ProgressView";
import { LEVEL_LABELS } from "./theme";

const FALLBACK_CATALOG: ExerciseCatalogItem[] = [
  {
    exercise: "pushup",
    display_name: "Flexiones",
    description: "Control de línea corporal hombro-cadera-tobillo y extensión de brazos.",
    icon: "💪",
    preferred_view: "side",
    is_isometric: false,
    required_keypoints: ["shoulder", "elbow", "wrist", "hip", "knee", "ankle"],
    levels: {
      easy: { key: "easy", display_name: "Fácil", rules_enabled: ["body_line", "full_rom"], up_threshold: 150, down_threshold: 105 },
      medium: { key: "medium", display_name: "Medio", rules_enabled: ["body_line", "hip_position", "knees_straight", "full_rom"], up_threshold: 160, down_threshold: 90 },
      advanced: { key: "advanced", display_name: "Avanzado", rules_enabled: ["body_line", "hip_position", "knees_straight", "full_rom", "tempo", "symmetry"], up_threshold: 165, down_threshold: 80 },
    },
    messages: {
      body_line: "Mantén el cuerpo en línea recta (hombro-cadera-tobillo)",
      hip_position: "Evita hundir o elevar las caderas",
      knees_straight: "Mantén las rodillas extendidas",
      full_rom: "Baja más: acerca el pecho al suelo",
      tempo: "Controla la bajada más despacio",
      symmetry: "Mantén ambos brazos trabajando de forma simétrica",
    },
  },
  {
    exercise: "squat",
    display_name: "Sentadillas",
    description: "Flexión de rodillas y cadera bajando en control con espalda neutra.",
    icon: "🦵",
    preferred_view: "side",
    is_isometric: false,
    required_keypoints: ["shoulder", "hip", "knee", "ankle"],
    levels: {
      easy: { key: "easy", display_name: "Fácil", rules_enabled: ["trunk_lean", "full_rom"], up_threshold: 155, down_threshold: 110 },
      medium: { key: "medium", display_name: "Medio", rules_enabled: ["trunk_lean", "knee_tracking", "full_rom"], up_threshold: 162, down_threshold: 95 },
      advanced: { key: "advanced", display_name: "Avanzado", rules_enabled: ["trunk_lean", "knee_tracking", "full_rom", "tempo", "symmetry"], up_threshold: 168, down_threshold: 85 },
    },
    messages: {
      trunk_lean: "Mantén el pecho alto y evita inclinar demasiado el tronco",
      knee_tracking: "Evita que las rodillas sobrepasen en exceso la punta del pie",
      full_rom: "Baja más hasta alcanzar el paralelo con los muslos",
      tempo: "Desciende de forma más controlada",
      symmetry: "Reparte el peso por igual en ambas piernas",
    },
  },
  {
    exercise: "situp",
    display_name: "Abdominales",
    description: "Elevación controlada del tronco activando el abdomen sin tirar del cuello.",
    icon: "🔥",
    preferred_view: "side",
    is_isometric: false,
    required_keypoints: ["shoulder", "hip", "knee", "ankle"],
    levels: {
      easy: { key: "easy", display_name: "Fácil", rules_enabled: ["knee_flexion", "full_rom"], up_threshold: 125, down_threshold: 85 },
      medium: { key: "medium", display_name: "Medio", rules_enabled: ["knee_flexion", "neck_alignment", "full_rom"], up_threshold: 130, down_threshold: 75 },
      advanced: { key: "advanced", display_name: "Avanzado", rules_enabled: ["knee_flexion", "neck_alignment", "full_rom", "tempo"], up_threshold: 135, down_threshold: 65 },
    },
    messages: {
      knee_flexion: "Mantén las rodillas flexionadas cerca de 90° con pies apoyados",
      neck_alignment: "No tires del cuello con las manos; mantén la barbilla despejada",
      full_rom: "Eleva más el tronco activando el abdomen",
      tempo: "Evita el impulso brusco y controla la bajada",
    },
  },
  {
    exercise: "plank",
    display_name: "Plancha",
    description: "Isométrico manteniendo hombros, caderas y tobillos en línea recta.",
    icon: "⏱️",
    preferred_view: "side",
    is_isometric: true,
    required_keypoints: ["shoulder", "elbow", "hip", "knee", "ankle"],
    levels: {
      easy: { key: "easy", display_name: "Fácil", rules_enabled: ["body_line"], target_hold_seconds: 20 },
      medium: { key: "medium", display_name: "Medio", rules_enabled: ["body_line", "hip_position", "knees_straight"], target_hold_seconds: 40 },
      advanced: { key: "advanced", display_name: "Avanzado", rules_enabled: ["body_line", "hip_position", "knees_straight", "elbow_alignment"], target_hold_seconds: 60 },
    },
    messages: {
      body_line: "Alinea hombros, caderas y tobillos en línea recta",
      hip_position: "Corrige la altura de la cadera (ni hundida ni en pico)",
      knees_straight: "Extiende completamente las piernas",
      elbow_alignment: "Coloca los codos justo debajo de los hombros",
    },
  },
  {
    exercise: "lunge",
    display_name: "Zancadas",
    description: "Paso amplio hacia delante flexionando ambas rodillas con torso erguido.",
    icon: "🚶",
    preferred_view: "side",
    is_isometric: false,
    required_keypoints: ["shoulder", "hip", "knee", "ankle"],
    levels: {
      easy: { key: "easy", display_name: "Fácil", rules_enabled: ["trunk_vertical", "full_rom"], up_threshold: 155, down_threshold: 112 },
      medium: { key: "medium", display_name: "Medio", rules_enabled: ["trunk_vertical", "knee_tracking", "full_rom"], up_threshold: 162, down_threshold: 98 },
      advanced: { key: "advanced", display_name: "Avanzado", rules_enabled: ["trunk_vertical", "knee_tracking", "full_rom", "tempo", "symmetry"], up_threshold: 168, down_threshold: 90 },
    },
    messages: {
      trunk_vertical: "Mantén el torso erguido y perpendicular al suelo",
      knee_tracking: "Evita que la rodilla delantera sobrepase demasiado el tobillo",
      full_rom: "Baja más hasta que la rodilla delantera forme ~90°",
      tempo: "Desciende de forma más pausada y estable",
      symmetry: "Mantén la estabilidad entre ambas piernas",
    },
  },
];

export function App() {
  // Luminoso blanco por defecto, con opción de modo oscuro
  const [darkMode, setDarkMode] = useState(false);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [activeTab, setActiveTab] = useState<NavTab>("home");
  const [exercises, setExercises] = useState<ExerciseCatalogItem[]>(FALLBACK_CATALOG);
  const [selectedExerciseKey, setSelectedExerciseKey] = useState<string>("pushup");
  const [selectedLevel, setSelectedLevel] = useState<string>("medium");
  const [activeVideoId, setActiveVideoId] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  useEffect(() => {
    fetchCurrentUser()
      .then((u) => setAuthUser(u))
      .finally(() => setCheckingAuth(false));
  }, []);

  useEffect(() => {
    if (!authUser) return;
    fetchExercises()
      .then((list) => {
        if (list && list.length > 0) {
          setExercises(list);
        }
      })
      .catch(() => {});
  }, [authUser]);

  const handleLogout = () => {
    setAuthToken(null);
    setAuthUser(null);
    setActiveTab("home");
  };

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center text-epia-500 gap-2">
        <Loader2 className="w-6 h-6 animate-spin" />
        <span className="font-semibold text-sm text-epia-900 dark:text-white">
          Cargando EPIA...
        </span>
      </div>
    );
  }

  if (!authUser) {
    return (
      <AuthView
        onAuthenticated={(u) => setAuthUser(u)}
        darkMode={darkMode}
        onToggleDark={() => setDarkMode((d) => !d)}
      />
    );
  }

  const currentExercise =
    exercises.find((e) => e.exercise === selectedExerciseKey) || exercises[0];
  const currentLevelCfg =
    currentExercise?.levels?.[selectedLevel] || currentExercise?.levels?.medium;

  const handleOpenVideoResult = (videoId: string) => {
    setActiveVideoId(videoId);
    setActiveTab("result");
  };

  return (
    <div className="min-h-screen bg-slate-50/80 dark:bg-slate-950 text-epia-900 dark:text-slate-100 transition-colors">
      <Navbar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        darkMode={darkMode}
        onToggleDark={() => setDarkMode((d) => !d)}
        user={authUser}
        onLogout={handleLogout}
      />

      {activeTab === "home" && (
        <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
          {/* Clean White Top Banner */}
          <section className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 px-6 py-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="inline-flex items-center gap-1.5 text-xs font-bold text-epia-500">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Hola, {authUser.name} · Panel de configuración rápida</span>
              </div>
              <h1 className="text-xl sm:text-2xl font-extrabold text-epia-900 dark:text-white tracking-tight">
                Configura tu sesión junto a{" "}
                <span className="text-epia-500">EPIA</span>
              </h1>
              <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                Selecciona de izquierda a derecha tu ejercicio, el nivel de exigencia y el modo de entrenamiento.
              </p>
            </div>

            {/* Active Selection Pill */}
            <div className="flex items-center gap-3 bg-slate-50 dark:bg-slate-800/80 px-4 py-3 rounded-2xl border border-slate-200 dark:border-slate-700 shrink-0">
              <span className="text-3xl">{currentExercise.icon}</span>
              <div className="text-xs">
                <span className="text-slate-400 block font-medium">
                  Configuración activa
                </span>
                <span className="font-bold text-epia-900 dark:text-white text-sm">
                  {currentExercise.display_name}
                </span>
                <span className="mx-1.5 text-slate-300">·</span>
                <span className="font-semibold text-epia-500">
                  {LEVEL_LABELS[selectedLevel]?.badge}{" "}
                  {LEVEL_LABELS[selectedLevel]?.label}
                </span>
              </div>
            </div>
          </section>

          {/* HORIZONTAL 3-COLUMN WORKSPACE */}
          <div className="grid lg:grid-cols-12 gap-6 items-stretch">
            {/* COLUMN 1: Paso 1 — Elige tu ejercicio (5 cols) */}
            <section className="lg:col-span-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                  <h2 className="text-sm font-extrabold uppercase tracking-wider text-epia-900 dark:text-white flex items-center gap-2">
                    <span className="w-6 h-6 rounded-lg bg-epia-500 text-white text-xs font-bold flex items-center justify-center">
                      1
                    </span>
                    Elige tu ejercicio
                  </h2>
                  <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                    <Eye className="w-3.5 h-3.5 text-epia-500" />
                    Vista:{" "}
                    <strong className="text-epia-900 dark:text-white">
                      {currentExercise?.preferred_view === "side"
                        ? "Perfil lateral"
                        : "Frontal"}
                    </strong>
                  </span>
                </div>

                {/* Horizontal Exercise Cards List */}
                <div className="space-y-2.5">
                  {exercises.map((ex) => {
                    const isSelected = ex.exercise === selectedExerciseKey;
                    return (
                      <button
                        key={ex.exercise}
                        onClick={() => setSelectedExerciseKey(ex.exercise)}
                        className={`w-full p-3.5 rounded-xl border text-left transition flex items-center justify-between gap-3.5 ${
                          isSelected
                            ? "bg-epia-50/90 dark:bg-epia-500/15 border-epia-500 ring-2 ring-epia-500/15 shadow-sm"
                            : "bg-white dark:bg-slate-800/60 border-slate-200 dark:border-slate-800 hover:border-epia-300 hover:bg-slate-50/70 dark:hover:bg-slate-800"
                        }`}
                      >
                        <div className="flex items-center gap-3.5 min-w-0">
                          <div
                            className={`w-11 h-11 rounded-xl flex items-center justify-center text-2xl shrink-0 ${
                              isSelected
                                ? "bg-white dark:bg-slate-800 shadow-sm border border-epia-100 dark:border-slate-700"
                                : "bg-slate-100 dark:bg-slate-800"
                            }`}
                          >
                            {ex.icon}
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <h3 className="font-bold text-sm text-epia-900 dark:text-white">
                                {ex.display_name}
                              </h3>
                              {ex.is_isometric && (
                                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                                  Isométrico
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                              {ex.description}
                            </p>
                          </div>
                        </div>
                        <div className="shrink-0">
                          {isSelected ? (
                            <CheckCircle2 className="w-5 h-5 text-epia-500" />
                          ) : (
                            <div className="w-5 h-5 rounded-full border-2 border-slate-200 dark:border-slate-700" />
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </section>

            {/* COLUMN 2: Paso 2 — Nivel de exigencia (4 cols) */}
            <section className="lg:col-span-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                  <h2 className="text-sm font-extrabold uppercase tracking-wider text-epia-900 dark:text-white flex items-center gap-2">
                    <span className="w-6 h-6 rounded-lg bg-epia-500 text-white text-xs font-bold flex items-center justify-center">
                      2
                    </span>
                    Nivel de corrección
                  </h2>
                  <span className="text-xs text-slate-400">Tolerancias</span>
                </div>

                {/* Horizontal Segmented Level Selector */}
                <div className="grid grid-cols-3 gap-2 p-1.5 bg-slate-100 dark:bg-slate-800 rounded-xl border border-slate-200/80 dark:border-slate-700">
                  {(["easy", "medium", "advanced"] as const).map((lvlKey) => {
                    const meta = LEVEL_LABELS[lvlKey];
                    const isSelected = selectedLevel === lvlKey;
                    return (
                      <button
                        key={lvlKey}
                        onClick={() => setSelectedLevel(lvlKey)}
                        className={`py-2.5 px-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                          isSelected
                            ? "bg-white dark:bg-epia-500 text-epia-500 dark:text-white shadow-sm"
                            : "text-slate-600 dark:text-slate-400 hover:text-epia-900 dark:hover:text-white"
                        }`}
                      >
                        <span>{meta.badge}</span>
                        <span>{meta.label}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Selected Level Details Card */}
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200/80 dark:border-slate-700 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-epia-900 dark:text-white flex items-center gap-1.5">
                      <Target className="w-4 h-4 text-epia-500" />
                      Exigencia {LEVEL_LABELS[selectedLevel]?.label}
                    </span>
                    {currentLevelCfg?.down_threshold && (
                      <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-white dark:bg-slate-900 text-epia-500 border border-slate-200 dark:border-slate-700">
                        {currentLevelCfg.down_threshold}° ↔{" "}
                        {currentLevelCfg.up_threshold}°
                      </span>
                    )}
                    {currentLevelCfg?.target_hold_seconds && (
                      <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-white dark:bg-slate-900 text-epia-500 border border-slate-200 dark:border-slate-700">
                        Objetivo: {currentLevelCfg.target_hold_seconds}s
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                    {LEVEL_LABELS[selectedLevel]?.desc}
                  </p>
                </div>

                {/* Active Rules List */}
                {currentLevelCfg && (
                  <div className="space-y-2">
                    <span className="text-xs font-bold text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <Sliders className="w-3.5 h-3.5 text-epia-500" />
                      Reglas biomecánicas evaluadas ({currentLevelCfg.rules_enabled.length}):
                    </span>
                    <div className="space-y-1.5">
                      {currentLevelCfg.rules_enabled.map((ruleId) => (
                        <div
                          key={ruleId}
                          className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200/70 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-200 flex items-center gap-2"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5 text-epia-ok shrink-0" />
                          <span>{currentExercise.messages?.[ruleId] || ruleId}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </section>

            {/* COLUMN 3: Paso 3 — Modo de entrenamiento (3 cols) */}
            <section className="lg:col-span-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                  <h2 className="text-sm font-extrabold uppercase tracking-wider text-epia-900 dark:text-white flex items-center gap-2">
                    <span className="w-6 h-6 rounded-lg bg-epia-500 text-white text-xs font-bold flex items-center justify-center">
                      3
                    </span>
                    Iniciar sesión
                  </h2>
                </div>

                <div className="space-y-3.5">
                  {/* Option A: Live Webcam */}
                  <button
                    onClick={() => setActiveTab("live")}
                    className="w-full group p-5 rounded-2xl bg-epia-500 hover:bg-epia-700 text-white text-left shadow-md shadow-epia-500/20 transition flex flex-col justify-between gap-4"
                  >
                    <div className="flex items-center justify-between">
                      <div className="p-2.5 rounded-xl bg-white/20 text-white">
                        <Camera className="w-6 h-6" />
                      </div>
                      <ArrowRight className="w-5 h-5 text-white/80 group-hover:translate-x-1 transition-transform" />
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-base font-extrabold text-white">
                        En Directo (Webcam)
                      </h3>
                      <p className="text-xs text-white/85 leading-relaxed">
                        Corrección en vivo con voz, esqueleto en tiempo real y vídeo guardado al terminar.
                      </p>
                    </div>
                  </button>

                  {/* Option B: Upload Video */}
                  <button
                    onClick={() => setActiveTab("upload")}
                    className="w-full group p-5 rounded-2xl bg-slate-50 dark:bg-slate-800 hover:bg-epia-50/60 dark:hover:bg-slate-700 border-2 border-slate-200 dark:border-slate-700 hover:border-epia-500 text-left transition flex flex-col justify-between gap-4"
                  >
                    <div className="flex items-center justify-between">
                      <div className="p-2.5 rounded-xl bg-epia-50 dark:bg-slate-700 text-epia-500">
                        <Upload className="w-6 h-6" />
                      </div>
                      <ArrowRight className="w-5 h-5 text-slate-400 group-hover:text-epia-500 group-hover:translate-x-1 transition-transform" />
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-base font-extrabold text-epia-900 dark:text-white">
                        Subir y Analizar Vídeo
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                        Sube un vídeo grabado desde tu móvil o PC para obtener el vídeo corregido e informe.
                      </p>
                    </div>
                  </button>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/70 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                💡 <strong>Consejo de encuadre:</strong> Coloca la cámara a la altura de la cadera a ~2 metros para que se te vea de pies a cabeza.
              </div>
            </section>
          </div>
        </main>
      )}

      {activeTab === "live" && currentExercise && (
        <LiveSessionView
          exercise={currentExercise}
          level={selectedLevel}
          onBack={() => setActiveTab("home")}
          onFinishedVideo={handleOpenVideoResult}
        />
      )}

      {activeTab === "upload" && currentExercise && (
        <UploadVideoView
          exercise={currentExercise}
          level={selectedLevel}
          onBack={() => setActiveTab("home")}
          onCompleted={handleOpenVideoResult}
        />
      )}

      {activeTab === "result" && activeVideoId && (
        <VideoResultView
          videoId={activeVideoId}
          onBackToLibrary={() => setActiveTab("library")}
        />
      )}

      {activeTab === "library" && (
        <LibraryView
          exercises={exercises}
          onOpenVideo={handleOpenVideoResult}
        />
      )}

      {activeTab === "progress" && (
        <ProgressView
          exercises={exercises}
          onOpenVideo={handleOpenVideoResult}
        />
      )}
    </div>
  );
}
