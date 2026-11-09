/**
 * Sistema de diseño cromático oficial de EPIA (Entrenador Personal de Inteligencia Artificial)
 * Balance de blancos luminosos, grises pizarra suaves y acentos azules deportivos.
 */
export const EPIA_THEME = {
  white: "#FFFFFF",
  surface: "#F8FAFC",
  surfaceMuted: "#F1F5F9",
  borderLight: "#E2E8F0",
  blue900: "#0B2545",
  blue800: "#0F315E",
  blue700: "#13408A",
  blue500: "#1E6FF2",
  blue300: "#6FA8FF",
  blue100: "#E6F0FF",
   blue50: "#F0F6FF",
  cyan400: "#22D3EE",
  ok: "#16A34A",
  warn: "#F59E0B",
  bad: "#DC2626",
} as const;

export const SKELETON_EDGES: [number, number][] = [
  [5, 6],
  [5, 7],
  [7, 9],
  [6, 8],
  [8, 10],
  [5, 11],
  [6, 12],
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
];

export const LEVEL_LABELS: Record<string, { label: string; badge: string; desc: string }> = {
  easy: {
    label: "Fácil",
    badge: "🟢",
    desc: "Tolerancias amplias centradas en aprender el patrón motor con seguridad.",
  },
  medium: {
    label: "Medio",
    badge: "🔵",
    desc: "Técnica sólida con recorrido completo (ROM) y control de alineación.",
  },
  advanced: {
    label: "Avanzado",
    badge: "🔷",
    desc: "Máxima precisión: control de tempo excéntrico, profundidad y simetría.",
  },
};
