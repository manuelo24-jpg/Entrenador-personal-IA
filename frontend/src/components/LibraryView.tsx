import React, { useEffect, useState } from "react";
import {
  Search,
  Star,
  Trash2,
  Play,
  Film,
  Filter,
  Edit3,
  Check,
} from "lucide-react";
import {
  ExerciseCatalogItem,
  VideoSummary,
  deleteVideoById,
  fetchVideos,
  patchVideo,
} from "../api/client";
import { LEVEL_LABELS } from "../theme";

interface LibraryViewProps {
  exercises: ExerciseCatalogItem[];
  onOpenVideo: (videoId: string) => void;
}

export const LibraryView: React.FC<LibraryViewProps> = ({
  exercises,
  onOpenVideo,
}) => {
  const [videos, setVideos] = useState<VideoSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterExercise, setFilterExercise] = useState("");
  const [filterLevel, setFilterLevel] = useState("");
  const [onlyFavorites, setOnlyFavorites] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const loadVideos = async () => {
    setLoading(true);
    try {
      const list = await fetchVideos({
        exercise: filterExercise || undefined,
        level: filterLevel || undefined,
        favorite: onlyFavorites ? true : undefined,
        q: searchQuery || undefined,
      });
      setVideos(list);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVideos();
  }, [filterExercise, filterLevel, onlyFavorites, searchQuery]);

  const handleToggleFav = async (v: VideoSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    await patchVideo(v.id, { favorite: !v.favorite });
    await loadVideos();
  };

  const handleDelete = async (v: VideoSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`¿Eliminar "${v.title}" y todos sus ficheros locales?`)) {
      return;
    }
    await deleteVideoById(v.id);
    await loadVideos();
  };

  const handleStartRename = (v: VideoSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(v.id);
    setEditTitle(v.title);
  };

  const handleSaveRename = async (videoId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await patchVideo(videoId, { title: editTitle });
    setEditingId(null);
    await loadVideos();
  };

  const exerciseMap = Object.fromEntries(exercises.map((e) => [e.exercise, e]));

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-epia-900 dark:text-white flex items-center gap-2">
            <Film className="w-6 h-6 text-epia-500" />
            Biblioteca de Sesiones EPIA
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Revisa tus grabaciones corregidas, filtra por ejercicio o nivel y compara tu evolución.
          </p>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar por título o notas..."
            className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-epia-900 dark:text-white focus:outline-none focus:border-epia-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400 shrink-0" />
          <select
            value={filterExercise}
            onChange={(e) => setFilterExercise(e.target.value)}
            className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-epia-900 dark:text-white"
          >
            <option value="">Todos los ejercicios</option>
            {exercises.map((ex) => (
              <option key={ex.exercise} value={ex.exercise}>
                {ex.icon} {ex.display_name}
              </option>
            ))}
          </select>
        </div>

        <select
          value={filterLevel}
          onChange={(e) => setFilterLevel(e.target.value)}
          className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-epia-900 dark:text-white"
        >
          <option value="">Todos los niveles</option>
          <option value="easy">🟢 Fácil</option>
          <option value="medium">🔵 Medio</option>
          <option value="advanced">🔷 Avanzado</option>
        </select>

        <button
          onClick={() => setOnlyFavorites((v) => !v)}
          className={`px-4 py-2 rounded-xl text-sm font-semibold border flex items-center justify-center gap-2 transition ${
            onlyFavorites
              ? "bg-amber-50 dark:bg-amber-500/20 border-amber-400 text-amber-600 dark:text-amber-300"
              : "bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-epia-900"
          }`}
        >
          <Star className={`w-4 h-4 ${onlyFavorites ? "fill-amber-400 text-amber-400" : ""}`} />
          Solo favoritos
        </button>
      </div>

      {/* Videos Grid */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">Cargando sesiones...</div>
      ) : videos.length === 0 ? (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-12 text-center space-y-2 shadow-sm">
          <Film className="w-10 h-10 text-epia-500 mx-auto" />
          <p className="text-base font-bold text-epia-900 dark:text-white">
            No hay sesiones guardadas todavía
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Sube un vídeo o realiza una sesión en directo para ver aquí tus análisis biomecánicos.
          </p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {videos.map((v) => {
            const exMeta = exerciseMap[v.exercise];
            const lvlMeta = LEVEL_LABELS[v.level] || LEVEL_LABELS.medium;
            return (
              <div
                key={v.id}
                onClick={() => onOpenVideo(v.id)}
                className="group bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-epia-500 rounded-2xl overflow-hidden shadow-sm hover:shadow-md cursor-pointer transition flex flex-col justify-between"
              >
                <div>
                  <div className="relative aspect-video bg-slate-100 dark:bg-slate-800 flex items-center justify-center overflow-hidden">
                    {v.has_thumbnail ? (
                      <img
                        src={`/api/videos/${v.id}/thumbnail`}
                        alt={v.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                      />
                    ) : (
                      <span className="text-4xl">{exMeta?.icon || "🏋️"}</span>
                    )}
                    <div className="absolute bottom-2.5 left-3 right-3 flex items-center justify-between text-xs">
                      <span className="px-2.5 py-1 rounded-full bg-white/95 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-700 font-semibold text-epia-900 dark:text-white shadow-sm">
                        {exMeta?.icon} {exMeta?.display_name || v.exercise}
                      </span>
                      <span className="px-2.5 py-1 rounded-full bg-epia-500 text-white font-bold shadow-sm">
                        {Math.round(v.score_avg)} pts
                      </span>
                    </div>
                  </div>

                  <div className="p-4 space-y-2">
                    {editingId === v.id ? (
                      <div
                        className="flex items-center gap-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="w-full px-2.5 py-1 rounded-lg bg-slate-50 dark:bg-slate-800 border border-epia-500 text-sm text-epia-900 dark:text-white"
                        />
                        <button
                          onClick={(e) => handleSaveRename(v.id, e)}
                          className="p-1.5 rounded-lg bg-epia-ok text-white"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <h3 className="font-bold text-epia-900 dark:text-white truncate">
                        {v.title}
                      </h3>
                    )}

                    <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                      <span>
                        {lvlMeta.badge} {lvlMeta.label}
                      </span>
                      <span className="font-medium">
                        {v.hold_seconds > 0 && v.reps_total === 0
                          ? `⏱ ${v.hold_seconds}s`
                          : `Reps: ${v.reps_total} (✓${v.reps_ok})`}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="px-4 py-2.5 bg-slate-50 dark:bg-slate-800/60 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                  <span className="text-[11px] text-slate-400">
                    {v.created_at ? new Date(v.created_at).toLocaleDateString("es-ES") : ""}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={(e) => handleStartRename(v, e)}
                      title="Renombrar"
                      className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={(e) => handleToggleFav(v, e)}
                      title="Favorito"
                      className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500"
                    >
                      <Star
                        className={`w-3.5 h-3.5 ${
                          v.favorite ? "fill-amber-400 text-amber-400" : ""
                        }`}
                      />
                    </button>
                    <button
                      onClick={(e) => handleDelete(v, e)}
                      title="Eliminar"
                      className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-epia-bad/30 text-slate-500 hover:text-epia-bad"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    <span className="p-1.5 rounded-lg bg-epia-50 dark:bg-epia-500/20 text-epia-500">
                      <Play className="w-3.5 h-3.5" />
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
