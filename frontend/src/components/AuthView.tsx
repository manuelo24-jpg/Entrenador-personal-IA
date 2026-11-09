import React, { useState } from "react";
import {
  LogIn,
  UserPlus,
  Mail,
  Lock,
  User,
  AlertCircle,
  Loader2,
  ShieldCheck,
  Sun,
  Moon,
} from "lucide-react";
import {
  AuthUser,
  loginRequest,
  registerRequest,
  setAuthToken,
} from "../api/client";
import { EpiaLogo } from "./EpiaLogo";

interface AuthViewProps {
  onAuthenticated: (user: AuthUser) => void;
  darkMode: boolean;
  onToggleDark: () => void;
}

export const AuthView: React.FC<AuthViewProps> = ({
  onAuthenticated,
  darkMode,
  onToggleDark,
}) => {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (mode === "register") {
      if (name.trim().length < 2) {
        setErrorMsg("Introduce tu nombre (mínimo 2 caracteres).");
        return;
      }
      if (password.length < 6) {
        setErrorMsg("La contraseña debe tener al menos 6 caracteres.");
        return;
      }
      if (password !== confirmPassword) {
        setErrorMsg("Las contraseñas no coinciden.");
        return;
      }
    }

    setLoading(true);
    try {
      const res =
        mode === "login"
          ? await loginRequest(email, password)
          : await registerRequest(name, email, password);
      setAuthToken(res.token);
      onAuthenticated(res.user);
    } catch (err: any) {
      setErrorMsg(err.message || "Error de autenticación");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-50 dark:bg-slate-950 text-epia-900 dark:text-slate-100 transition-colors">
      {/* Top Bar */}
      <div className="max-w-7xl w-full mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <EpiaLogo size="sm" />
          <span className="font-extrabold text-lg tracking-tight text-epia-900 dark:text-white">
            EPIA
          </span>
        </div>
        <button
          onClick={onToggleDark}
          title="Cambiar tema claro/oscuro"
          className="p-2.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 shadow-sm transition"
        >
          {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>

      {/* Centered Auth Card */}
      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-xl space-y-6">
          {/* Brand Logo & Heading */}
          <div className="flex flex-col items-center text-center space-y-3">
            <EpiaLogo size="xl" />
            <div>
              <div className="flex items-center justify-center gap-2">
                <h1 className="text-3xl font-extrabold tracking-tight text-epia-900 dark:text-white">
                  EPIA
                </h1>
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-epia-50 dark:bg-slate-800 text-epia-500 border border-epia-500/20">
                  YOLO11-Pose
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Entrenador Personal de Inteligencia Artificial
              </p>
            </div>
          </div>

          {/* Mode Tabs */}
          <div className="grid grid-cols-2 p-1 rounded-2xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setErrorMsg(null);
              }}
              className={`py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 ${
                mode === "login"
                  ? "bg-white dark:bg-epia-500 text-epia-500 dark:text-white shadow-sm"
                  : "text-slate-500 dark:text-slate-400 hover:text-epia-900 dark:hover:text-white"
              }`}
            >
              <LogIn className="w-4 h-4" />
              Iniciar Sesión
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("register");
                setErrorMsg(null);
              }}
              className={`py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 ${
                mode === "register"
                  ? "bg-white dark:bg-epia-500 text-epia-500 dark:text-white shadow-sm"
                  : "text-slate-500 dark:text-slate-400 hover:text-epia-900 dark:hover:text-white"
              }`}
            >
              <UserPlus className="w-4 h-4" />
              Registrarse
            </button>
          </div>

          {errorMsg && (
            <div className="p-3.5 rounded-xl bg-red-50 dark:bg-epia-bad/20 border border-epia-bad/40 text-xs font-medium text-epia-bad dark:text-red-200 flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 text-epia-bad shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                  Nombre o Alias
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Tu nombre"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-epia-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-epia-500 focus:bg-white dark:focus:bg-slate-800 transition"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                Correo Electrónico
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="atleta@epia.local"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-epia-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-epia-500 focus:bg-white dark:focus:bg-slate-800 transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                Contraseña
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-epia-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-epia-500 focus:bg-white dark:focus:bg-slate-800 transition"
                />
              </div>
            </div>

            {mode === "register" && (
              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                  Confirmar Contraseña
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-epia-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-epia-500 focus:bg-white dark:focus:bg-slate-800 transition"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 rounded-xl bg-epia-500 hover:bg-epia-700 disabled:opacity-50 text-white font-bold text-sm shadow-md shadow-epia-500/20 transition flex items-center justify-center gap-2 mt-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Verificando...
                </>
              ) : mode === "login" ? (
                <>
                  <LogIn className="w-4 h-4" />
                  Acceder a EPIA
                </>
              ) : (
                <>
                  <UserPlus className="w-4 h-4" />
                  Crear cuenta y entrar
                </>
              )}
            </button>
          </form>

          <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <ShieldCheck className="w-4 h-4 text-epia-500 shrink-0" />
            <span>Tus datos y vídeos se guardan 100 % en tu equipo local.</span>
          </div>
        </div>
      </div>

      {/* Footer Disclaimer */}
      <footer className="py-3 px-4 text-center text-xs text-slate-400 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
        EPIA — Entrenador Personal de Inteligencia Artificial · Procesado local con YOLO11-pose
      </footer>
    </div>
  );
};
