# Reglas del proyecto EPIA (Entrenador Personal de Inteligencia Artificial)

- Python 3.11+, tipado estático, formateo con ruff. Frontend React + TS + Tailwind.
- Toda lógica de ejercicios vive en `backend/app/core/exercises/`, una clase por ejercicio.
- Los umbrales NUNCA se hardcodean: van en `backend/configs/exercises/*.yaml` por nivel (`easy`, `medium`, `advanced`).
- Distancias normalizadas por longitud de torso (`torso_length`), nunca en píxeles.
- No usar `cv2.putText` para texto con tildes/símbolos: usar `render.py` (Pillow).
- Cada regla nueva requiere test unitario con secuencias sintéticas.
- Procesado 100 % local, sin llamadas a servicios externos.
- Paleta azul definida en `frontend/src/theme`; no introducir colores sueltos.
- Antes de dar una tarea por terminada: tests y linter en verde.

