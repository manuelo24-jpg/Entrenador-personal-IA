import React from "react";
import {
  Activity,
  Film,
  BarChart3,
  Sun,
  Moon,
  ShieldAlert,
  LogOut,
  User as UserIcon,
} from "lucide-react";
import { AuthUser } from "../api/client";
import { EpiaLogo } from "./EpiaLogo";

export type NavTab = "home" | "live" | "upload" | "result" | "library" | "progress";

interface NavbarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  darkMode: boolean;
  onToggleDark: () => void;
  user: AuthUser;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onSelectTab,
  darkMode,
  onToggleDark,
  user,
  onLogout,
}) => {
  return (
    <header className="border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur sticky top-0 z-30 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-4">
        <button
          onClick={() => onSelectTab("home")}
          className="flex items-center gap-3 text-left group"
        >
          <EpiaLogo size="md" />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-extrabold tracking-tight text-epia-900 dark:text-white">
                EPIA
              </span>
              <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-epia-50 dark:bg-slate-800 text-epia-500 border border-epia-500/20">
                YOLO11-Pose
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Entrenador Personal de Inteligencia Artificial
            </p>
          </div>
        </button>

        <nav className="flex flex-wrap items-center gap-1.5 bg-slate-100 dark:bg-slate-800/90 p-1 rounded-2xl border border-slate-200/80 dark:border-slate-700">
          <button
            onClick={() => onSelectTab("home")}
            className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition flex items-center gap-2 ${
              activeTab === "home" || activeTab === "live" || activeTab === "upload"
                ? "bg-white dark:bg-epia-500 text-epia-500 dark:text-white shadow-sm"
                : "text-slate-600 dark:text-slate-300 hover:text-epia-900 dark:hover:text-white"
            }`}
          >
            <Activity className="w-4 h-4" />
            Entrenar
          </button>

          <button
            onClick={() => onSelectTab("library")}
            className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition flex items-center gap-2 ${
              activeTab === "library" || activeTab === "result"
                ? "bg-white dark:bg-epia-500 text-epia-500 dark:text-white shadow-sm"
                : "text-slate-600 dark:text-slate-300 hover:text-epia-900 dark:hover:text-white"
            }`}
          >
            <Film className="w-4 h-4" />
            Biblioteca
          </button>

          <button
            onClick={() => onSelectTab("progress")}
            className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition flex items-center gap-2 ${
              activeTab === "progress"
                ? "bg-white dark:bg-epia-500 text-epia-500 dark:text-white shadow-sm"
                : "text-slate-600 dark:text-slate-300 hover:text-epia-900 dark:hover:text-white"
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            Progreso
          </button>
        </nav>

        <div className="flex items-center gap-2">
          <div className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center gap-2 text-xs text-epia-900 dark:text-slate-100">
            <UserIcon className="w-3.5 h-3.5 text-epia-500" />
            <span className="font-semibold max-w-[130px] truncate">
              {user.name}
            </span>
          </div>

          <button
            onClick={onToggleDark}
            title="Cambiar tema claro/oscuro"
            className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 transition"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          <button
            onClick={onLogout}
            title="Cerrar sesión"
            className="px-3 py-2 rounded-xl bg-white dark:bg-slate-800 hover:bg-red-50 dark:hover:bg-epia-bad/20 border border-slate-200 dark:border-slate-700 hover:border-epia-bad/50 text-slate-600 dark:text-slate-300 hover:text-epia-bad text-xs font-semibold transition flex items-center gap-1.5"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Salir</span>
          </button>
        </div>
      </div>

      <div className="bg-slate-50 dark:bg-slate-900 border-t border-slate-200/70 dark:border-slate-800 px-4 py-1 text-center text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-center gap-2">
        <ShieldAlert className="w-3.5 h-3.5 text-epia-500 shrink-0" />
        <span>
          <strong>Aviso de salud:</strong> EPIA es orientativo y no sustituye el consejo profesional. Detén el ejercicio si sientes dolor. Procesado 100 % local.
        </span>
      </div>
    </header>
  );
};
