from __future__ import annotations

import platform
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.core.exercises.base import FrameAnalysis
from app.core.pose.base import SIDE_JOINT_MAP, SKELETON_EDGES, Person
from app.core.scoring import SessionSummary

# EPIA Blue Palette & Status Colors (RGB for Pillow)
COLOR_BG_DARK = (11, 37, 69, 215)  # #0B2545
COLOR_BLUE_PRIMARY = (30, 111, 242)  # #1E6FF2
COLOR_CYAN_ACCENT = (34, 211, 238)  # #22D3EE
COLOR_OK = (22, 163, 74)  # #16A34A
COLOR_WARN = (245, 158, 11)  # #F59E0B
COLOR_BAD = (220, 38, 38)  # #DC2626
COLOR_WHITE = (248, 250, 252)
COLOR_MUTED = (148, 163, 184)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a TrueType font with full Unicode/Spanish support across Windows, Linux, and macOS."""
    candidates: list[str] = []
    sys_name = platform.system().lower()
    if "windows" in sys_name:
        candidates = [
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        ]
    elif "darwin" in sys_name:
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]

    for font_path in candidates:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size=size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


class OverlayRenderer:
    """Renders skeleton, joint angles, HUD panel, and Unicode feedback onto video frames."""

    def __init__(
        self, exercise_display: str, level_display: str, is_isometric: bool = False
    ) -> None:
        self.exercise_display = exercise_display
        self.level_display = level_display
        self.is_isometric = is_isometric
        self._font_sm = _load_font(15, bold=False)
        self._font_md = _load_font(18, bold=True)
        self._font_lg = _load_font(26, bold=True)
        self._font_xl = _load_font(34, bold=True)

    def render_frame(
        self,
        frame_bgr: np.ndarray,
        person: Person | None,
        analysis: FrameAnalysis,
    ) -> np.ndarray:
        """Draw skeleton, ideal guide line, joint angles, and EPIA HUD panel on a BGR frame."""
        h, w = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb).convert("RGBA")
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        if person is not None:
            # 1. Draw ideal guide line if available
            if analysis.ideal_line is not None:
                p1, p2 = analysis.ideal_line
                draw.line(
                    [(p1[0], p1[1]), (p2[0], p2[1])],
                    fill=(34, 211, 238, 150),
                    width=3,
                )

            # 2. Draw skeleton edges
            for i, j in SKELETON_EDGES:
                if person.confidences[i] < 0.35 or person.confidences[j] < 0.35:
                    continue
                st_i = analysis.joint_states.get(i, "ok")
                st_j = analysis.joint_states.get(j, "ok")
                if "bad" in (st_i, st_j):
                    edge_color = (*COLOR_BAD, 235)
                elif "warn" in (st_i, st_j):
                    edge_color = (*COLOR_WARN, 235)
                else:
                    edge_color = (*COLOR_BLUE_PRIMARY, 230)

                p_i = (float(person.keypoints[i, 0]), float(person.keypoints[i, 1]))
                p_j = (float(person.keypoints[j, 0]), float(person.keypoints[j, 1]))
                draw.line([p_i, p_j], fill=edge_color, width=4)

            # 3. Draw keypoints
            for idx in range(5, 17):
                if person.confidences[idx] < 0.35:
                    continue
                kx, ky = float(person.keypoints[idx, 0]), float(person.keypoints[idx, 1])
                st = analysis.joint_states.get(idx, "ok")
                fill_col = (
                    COLOR_BAD
                    if st == "bad"
                    else (COLOR_WARN if st == "warn" else COLOR_CYAN_ACCENT)
                )
                r = 6
                draw.ellipse(
                    [(kx - r, ky - r), (kx + r, ky + r)],
                    fill=(*fill_col, 255),
                    outline=(255, 255, 255, 230),
                    width=2,
                )

            # 4. Draw primary angle badge near the active side joint
            side = analysis.dominant_side
            jmap = SIDE_JOINT_MAP.get(side, SIDE_JOINT_MAP["right"])
            for metric_name, val in analysis.angles.items():
                target_joint = "elbow"
                if "knee" in metric_name:
                    target_joint = "knee"
                elif "hip" in metric_name or "body_line" in metric_name or "trunk" in metric_name:
                    target_joint = "hip"
                j_idx = jmap.get(target_joint, 8)
                jx, jy = float(person.keypoints[j_idx, 0]), float(person.keypoints[j_idx, 1])
                label = f"{int(round(val))}°"
                draw.rounded_rectangle(
                    [(jx + 10, jy - 14), (jx + 68, jy + 12)],
                    radius=6,
                    fill=(11, 37, 69, 210),
                    outline=(*COLOR_CYAN_ACCENT, 190),
                    width=1,
                )
                draw.text((jx + 16, jy - 11), label, font=self._font_sm, fill=COLOR_WHITE)

        # 5. Draw top-left EPIA HUD panel
        panel_w = min(340, w - 24)
        panel_h = 152
        draw.rounded_rectangle(
            [(16, 16), (16 + panel_w, 16 + panel_h)],
            radius=14,
            fill=COLOR_BG_DARK,
            outline=(*COLOR_BLUE_PRIMARY, 200),
            width=2,
        )
        draw.text(
            (30, 26),
            f"EPIA · {self.exercise_display}",
            font=self._font_md,
            fill=COLOR_CYAN_ACCENT,
        )
        draw.text(
            (30, 50),
            f"Nivel: {self.level_display}  |  Fase: {analysis.phase}",
            font=self._font_sm,
            fill=COLOR_MUTED,
        )

        if self.is_isometric:
            main_stat = f"Tiempo: {analysis.hold_seconds:.1f} s"
        else:
            main_stat = (
                f"Reps: {analysis.reps_total}  "
                f"(✓{analysis.reps_ok}  ~{analysis.reps_partial}  ✗{analysis.reps_bad})"
            )
        draw.text((30, 78), main_stat, font=self._font_md, fill=COLOR_WHITE)

        score_col = (
            COLOR_OK
            if analysis.current_score >= 80
            else (COLOR_WARN if analysis.current_score >= 60 else COLOR_BAD)
        )
        draw.text(
            (30, 112),
            f"Puntuación técnica: {int(round(analysis.current_score))}/100",
            font=self._font_md,
            fill=(*score_col, 255),
        )

        # 6. Draw bottom feedback banner
        banner_msg = ""
        banner_color = COLOR_OK
        if analysis.state != "ACTIVE":
            banner_msg = analysis.placement_message or "Ajusta tu posición frente a la cámara"
            banner_color = COLOR_WARN
        elif analysis.active_errors:
            top_err = max(analysis.active_errors, key=lambda e: e.get("severity", 0.0))
            banner_msg = f"⚠ {top_err['message']}"
            banner_color = COLOR_BAD if top_err.get("severity", 0.5) >= 0.45 else COLOR_WARN
        else:
            banner_msg = "✓ Técnica correcta — mantén el ritmo"
            banner_color = COLOR_OK

        banner_y1 = h - 64
        banner_y2 = h - 16
        draw.rounded_rectangle(
            [(16, banner_y1), (w - 16, banner_y2)],
            radius=12,
            fill=(11, 37, 69, 225),
            outline=(*banner_color, 240),
            width=2,
        )
        draw.text((32, banner_y1 + 13), banner_msg, font=self._font_md, fill=COLOR_WHITE)

        combined = Image.alpha_composite(pil_img, overlay).convert("RGB")
        return cv2.cvtColor(np.array(combined), cv2.COLOR_RGB2BGR)

    def render_summary_card(
        self,
        width: int,
        height: int,
        summary: SessionSummary,
    ) -> np.ndarray:
        """Create an end-of-session summary frame in BGR format."""
        pil_img = Image.new("RGB", (width, height), (11, 37, 69))
        draw = ImageDraw.Draw(pil_img)

        pad_x = max(32, width // 10)
        pad_y = max(32, height // 8)
        draw.rounded_rectangle(
            [(pad_x, pad_y), (width - pad_x, height - pad_y)],
            radius=20,
            fill=(19, 64, 138),
            outline=COLOR_CYAN_ACCENT,
            width=3,
        )

        tx = pad_x + 36
        ty = pad_y + 32
        draw.text(
            (tx, ty),
            f"EPIA — Resumen de Sesión ({self.exercise_display})",
            font=self._font_lg,
            fill=COLOR_CYAN_ACCENT,
        )
        ty += 44
        draw.text(
            (tx, ty),
            f"Nivel: {self.level_display}   |   Puntuación Media: {summary.score_avg:.1f} / 100",
            font=self._font_md,
            fill=COLOR_WHITE,
        )
        ty += 40

        if self.is_isometric:
            stats_line = f"Tiempo efectivo mantenido: {summary.hold_seconds:.1f} segundos"
        else:
            stats_line = (
                f"Total: {summary.reps_total} reps   ·   "
                f"✓ Correctas: {summary.reps_ok}   ·   "
                f"~ Parciales: {summary.reps_partial}   ·   "
                f"✗ Incorrectas: {summary.reps_bad}"
            )
        draw.text((tx, ty), stats_line, font=self._font_md, fill=COLOR_WHITE)
        ty += 44

        if summary.top_errors:
            draw.text((tx, ty), "Errores más frecuentes:", font=self._font_md, fill=COLOR_WARN)
            ty += 28
            for err in summary.top_errors[:3]:
                draw.text(
                    (tx + 14, ty),
                    f"• {err['message']} ({err['count']}x)",
                    font=self._font_sm,
                    fill=COLOR_WHITE,
                )
                ty += 24
        else:
            draw.text(
                (tx, ty),
                "✓ Sin errores técnicos significativos registrados.",
                font=self._font_md,
                fill=COLOR_OK,
            )
            ty += 32

        ty += 12
        draw.text(
            (tx, ty), f"Consejo EPIA: {summary.advice}", font=self._font_sm, fill=COLOR_CYAN_ACCENT
        )

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
