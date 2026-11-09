# 🏋️ Plan de Implementación — EPIA (Entrenador Personal de Inteligencia Artificial)

> **Documento:** Plan técnico de implementación v1.1
> **Rol:** Desarrollador de Software Senior especializado en IA
> **Objetivo:** Evolucionar la práctica `flexiones.ipynb` (YOLO11-pose) a **EPIA**, una aplicación completa, multi-ejercicio, con niveles de exigencia, análisis de vídeo, modo en directo y biblioteca de sesiones.
> **Entorno de desarrollo:** Google Antigravity (Windows nativo / WSL2 / Linux multiplataforma).

---

## 1. Resumen ejecutivo

| Aspecto | Decisión |
|---|---|
| Nombre de la aplicación | **EPIA** (*Entrenador Personal de Inteligencia Artificial*) |
| Ejercicios (MVP) | Flexiones, sentadillas, abdominales, plancha, zancadas |
| Niveles | Fácil · Medio · Avanzado (cambian tolerancias, reglas activas y exigencia de tempo) |
| Modos | 1) Subir vídeo → vídeo corregido · 2) Directo (webcam) → feedback en vivo + vídeo corregido al terminar |
| Modelo de pose | YOLO11-pose (Ultralytics) con interfaz intercambiable (MediaPipe / RTMPose) |
| Backend | Python 3.11+ + FastAPI + WebSocket |
| Frontend | React + TypeScript + Vite + Tailwind (web local, tonos azules) |
| Almacenamiento | SQLite + carpeta de ficheros (vídeos, miniaturas, informes) |
| Ejecución | Local (Windows/WSL2/Linux/macOS). Sin enviar datos a la nube |

---

## 2. Análisis de la práctica actual (punto de partida)

### 2.1 Lo que ya funciona bien
- Detección de pose con `yolo11n-pose.pt` (17 keypoints COCO).
- Cálculo de ángulos con `atan2` (codo, espalda, rodilla).
- Máquina de estados simple (`arriba` / `abajo`) para contar repeticiones.
- Clasificación de repetición correcta / incorrecta y feedback visual.

### 2.2 Limitaciones detectadas (a resolver en el proyecto)

| # | Limitación en el código actual | Consecuencia | Solución en EPIA |
|---|---|---|---|
| 1 | Solo usa el **lado derecho** del cuerpo (índices 6, 8, 10, 12, 14, 16) | Falla si el usuario se coloca con el lado izquierdo hacia la cámara | Elegir automáticamente el lado con mayor confianza media |
| 2 | Umbral `diferencia < 150` **en píxeles** (caderas) | Depende de la resolución y la distancia a la cámara | Normalizar por longitud del torso o altura corporal |
| 3 | Umbrales fijos (160°, 90°, 160–190°) | No hay niveles ni adaptación | Perfiles de nivel en ficheros de configuración |
| 4 | Sin suavizado de keypoints | Ángulos «tiemblan», repeticiones falsas | Filtro One-Euro o media móvil exponencial |
| 5 | `cv2.putText` con `°`, `⚠`, `✓`, tildes | OpenCV **no renderiza bien Unicode** (salen `?`) | Renderizar texto con Pillow (fuente TTF) o dibujar overlay en el navegador |
| 6 | Solo cuenta la repetición al subir, sin medir profundidad ni tempo | Repeticiones «a medias» pueden contar | Validar rango de movimiento completo y duración de fase |
| 7 | Un único error por frame, no se acumulan por repetición | Feedback poco útil | Registrar errores por repetición y puntuarla (0–100) |
| 8 | No hay salida de vídeo ni informe | No se puede revisar | Pipeline de vídeo con overlay + informe JSON/PDF |
| 9 | Código acoplado a Colab/Jupyter | No reutilizable | Arquitectura modular con un analizador por ejercicio |
| 10 | Procesa `frame_count % 2` saltándose frames | Pérdida de información en el vídeo final | Procesar todos los frames en offline; adaptativo en directo |
| 11 | Si hay varias personas coge `kpts[0]` | Puede seguir a la persona equivocada | Seleccionar persona por tamaño/centralidad + tracking |

---

## 3. Decisiones técnicas importantes (leer antes de empezar)

### 3.1 ⚖️ Licencia de Ultralytics (AGPL-3.0)
Ultralytics YOLO es gratuito, pero con **licencia AGPL-3.0**: si distribuyes o ofreces el software como servicio, debes publicar tu código bajo AGPL o comprar licencia empresarial. Para un **software de prueba / uso personal / académico** no hay problema. Si en el futuro se comercializa:
- Opción A: licencia Enterprise de Ultralytics.
- Opción B: cambiar el motor a **MediaPipe Pose** o **RTMPose (MMPose)**, ambos Apache-2.0.

👉 Por eso el diseño incluye una **interfaz `PoseEstimator`** para intercambiar el motor sin tocar la lógica de ejercicios.

### 3.2 🎥 Webcam en WSL2
**WSL2 no accede a la webcam de forma nativa** (requiere compilar kernel / usbipd, frágil). Decisión de arquitectura:

> **El navegador de Windows captura la cámara** (`getUserMedia`) y envía los frames por WebSocket al backend que corre en WSL. El usuario abre `http://localhost:5173` desde Windows (WSL2 reenvía `localhost` automáticamente).

Esto además hace la app portable (funciona igual en Linux, macOS o Windows sin tocar la cámara desde Python).

### 3.3 🚀 GPU
- Con GPU NVIDIA: WSL2 soporta CUDA (driver NVIDIA en Windows, **no** instalar driver dentro de WSL). Se instala PyTorch con CUDA.
- Sin GPU: `yolo11n-pose` (nano) funciona en CPU a ~10–20 FPS en un portátil medio. Suficiente para directo con salto de frames y perfectamente válido para vídeo offline.

### 3.4 🎞️ Códec de vídeo
`cv2.VideoWriter` con `mp4v` genera ficheros que **muchos navegadores no reproducen**. Se usará **FFmpeg (libx264 + yuv420p)** para exportar el vídeo final reproducible en el navegador, conservando el audio original si existe.

### 3.5 🩺 Descargo de responsabilidad
Los ángulos y umbrales son orientativos. Se validarán con un/a entrenador/a o fisioterapeuta y la app mostrará un aviso: *«No sustituye el consejo profesional. Detén el ejercicio si sientes dolor.»*

---

## 4. Arquitectura

```
┌──────────────────────────── NAVEGADOR (Windows/Linux/Mac) ────────────────────────────┐
│  React UI (azules)                                                                      │
│  ├─ Selector ejercicio / nivel     ├─ Subida de vídeo     ├─ Biblioteca de sesiones    │
│  ├─ Modo directo: getUserMedia ──► canvas (overlay de esqueleto/ángulos en vivo)       │
│  └─ MediaRecorder (graba el vídeo crudo del directo)                                   │
└───────────────▲──────────────────────────────┬─────────────────────────────────────────┘
                │ REST (JSON)                  │ WebSocket (frames JPEG ⇄ keypoints+feedback)
┌───────────────┴──────────────────────────────▼─────────────────────────────────────────┐
│  BACKEND FastAPI (WSL2 / Linux)                                                         │
│  ┌────────────┐  ┌───────────────┐  ┌────────────────┐  ┌──────────────┐               │
│  │ PoseEngine │─►│ Preprocesado  │─►│ ExerciseAnalyzer│─►│ Renderer     │               │
│  │ (YOLO11)   │  │ suavizado,    │  │ (1 por ejercicio│  │ (overlay Pillow│              │
│  │            │  │ normalización │  │  + nivel)       │  │  + OpenCV)   │               │
│  └────────────┘  └───────────────┘  └────────────────┘  └──────────────┘               │
│  Job Queue (cola de procesado de vídeos) │ FFmpeg │ SQLite │ Sistema de ficheros        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Flujo «Subir vídeo»
1. Usuario elige ejercicio + nivel y sube el vídeo.
2. Backend crea un **job** (`queued → processing → done/error`) y devuelve `job_id`.
3. Worker lee el vídeo frame a frame → pose → suavizado → analizador → overlay → escribe vídeo.
4. FFmpeg recodifica a H.264 + audio original. Se genera miniatura e informe JSON.
5. Frontend consulta progreso (SSE/polling) y muestra el resultado con el reproductor y la línea de tiempo de errores.

### 4.2 Flujo «Directo»
1. Usuario elige ejercicio + nivel → **comprobación de posición** (¿se te ve entero? ¿de perfil/frontal?).
2. Cuenta atrás 3-2-1.
3. El navegador envía frames (≈ 640×360, 10–15 FPS, JPEG calidad 0.7) por WebSocket.
4. El servidor responde **solo JSON** (keypoints, ángulos, estado, reps, errores): el overlay se dibuja en el cliente → baja latencia.
5. A la vez, `MediaRecorder` graba el vídeo crudo en el navegador.
6. Al pulsar *Terminar*, el vídeo crudo se sube y se **reprocesa en modo offline** con el mismo pipeline → vídeo final con correcciones, de máxima calidad y sin saltos de frames.

> Ventaja: el feedback en vivo prioriza velocidad; el vídeo guardado prioriza calidad. Ambos usan **el mismo analizador**, así los resultados son coherentes.

---

## 5. Estructura del repositorio

```
epia/
├── AGENTS.md                      # Reglas para los agentes de Antigravity (ver §14)
├── README.md
├── docker-compose.yml             # Opcional
├── Makefile                       # make setup / dev / test / lint
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py                # FastAPI app
│   │   ├── api/
│   │   │   ├── videos.py          # subida, listado, descarga, borrado
│   │   │   ├── jobs.py            # estado de procesado
│   │   │   ├── live.py            # WebSocket de directo
│   │   │   └── exercises.py       # catálogo de ejercicios y niveles
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── pose/
│   │   │   │   ├── base.py        # interfaz PoseEstimator
│   │   │   │   ├── yolo_pose.py   # implementación YOLO11
│   │   │   │   └── mediapipe_pose.py  # (fase futura)
│   │   │   ├── geometry.py        # ángulos, distancias, normalización
│   │   │   ├── smoothing.py       # One-Euro / EMA
│   │   │   ├── tracking.py        # selección y seguimiento de persona
│   │   │   ├── view.py            # detección de perfil/frontal y lado
│   │   │   ├── exercises/
│   │   │   │   ├── base.py        # clase ExerciseAnalyzer + FSM de repeticiones
│   │   │   │   ├── pushup.py
│   │   │   │   ├── squat.py
│   │   │   │   ├── situp.py
│   │   │   │   ├── plank.py
│   │   │   │   └── lunge.py
│   │   │   ├── scoring.py         # puntuación por repetición y sesión
│   │   │   ├── render.py          # overlay (esqueleto, ángulos, panel, texto Unicode)
│   │   │   └── pipeline.py        # procesado offline de vídeo
│   │   ├── services/
│   │   │   ├── storage.py         # ficheros + miniaturas
│   │   │   ├── ffmpeg.py
│   │   │   └── jobs.py            # cola de trabajos
│   │   └── db/ (models.py, session.py, migrations/)
│   ├── configs/
│   │   └── exercises/             # YAML por ejercicio con niveles (ver §7)
│   ├── models/                    # yolo11n-pose.pt, yolo11s-pose.pt
│   └── tests/
│       ├── unit/                  # geometría, FSM, reglas
│       └── fixtures/              # vídeos cortos etiquetados
├── frontend/
│   ├── package.json
│   └── src/ (pages, components, hooks, api, theme)
├── data/                          # (gitignored) vídeos, miniaturas, informes, SQLite
└── docs/                          # capturas, decisiones (ADR), guía de cámara
```

---

## 6. Motor de pose y preprocesado

### 6.1 Interfaz `PoseEstimator`
```python
class PoseEstimator(Protocol):
    def infer(self, frame_bgr: np.ndarray) -> list[Person]: ...
    # Person: keypoints (17,2) en px, confianzas (17,), bbox, track_id opcional
```

### 6.2 Pipeline por frame
1. **Inferencia** (YOLO11-pose; `imgsz=640`; tamaño de modelo configurable `n/s/m`).
2. **Selección de persona**: la de mayor área de bbox y más cercana al centro; mantener el mismo `track_id` (`model.track(persist=True)`).
3. **Filtrado por confianza**: keypoints con conf < 0.5 se marcan como no fiables (se interpolan hasta N frames; si pasa el límite → mensaje «no te veo bien»).
4. **Suavizado** (One-Euro filter por keypoint) para estabilizar ángulos sin añadir retardo notable.
5. **Normalización**: dividir distancias por la longitud del torso (hombro–cadera) o altura corporal → umbrales independientes de resolución/distancia.
6. **Detección de vista y lado**: perfil vs. frontal (ratio ancho de hombros / longitud del torso); lado visible = el de mayor confianza media.
7. **Analizador** del ejercicio → estado, ángulos, errores, evento de repetición.

### 6.3 Keypoints COCO usados
`0` nariz · `5/6` hombros · `7/8` codos · `9/10` muñecas · `11/12` caderas · `13/14` rodillas · `15/16` tobillos (impar = izquierda, par = derecha).

---

## 7. Ejercicios, reglas y niveles

### 7.1 Concepto de «nivel de corrección»
El nivel **no cambia el ejercicio, cambia la exigencia con la que se evalúa**:

| Nivel | Filosofía | Qué cambia |
|---|---|---|
| 🟢 **Fácil** | Aprender el patrón | Tolerancias amplias, solo 2–3 reglas críticas (seguridad), feedback con mensajes motivadores, sin exigir tempo |
| 🔵 **Medio** | Técnica sólida | Tolerancias medias, todas las reglas básicas, rango de movimiento completo |
| 🔷 **Avanzado** | Técnica de precisión | Tolerancias estrictas, reglas extra (simetría, control de tempo, profundidad), puntuación exigente |

### 7.2 Formato de configuración (ejemplo `pushup.yaml`)
```yaml
exercise: pushup
display_name: Flexiones
preferred_view: side          # side | front
required_keypoints: [shoulder, elbow, wrist, hip, knee, ankle]
phases:
  up:   { metric: elbow_angle, op: ">",  }
  down: { metric: elbow_angle, op: "<",  }
levels:
  easy:
    up_threshold: 150          # grados: codo casi extendido
    down_threshold: 105        # basta con bajar a ~100°
    body_line_tolerance: 25    # |180 - ángulo hombro-cadera-tobillo|
    hip_sag_ratio: 0.30        # fracción del torso
    check_knees_straight: false
    min_phase_seconds: 0.0
    rules_enabled: [body_line]
  medium:
    up_threshold: 160
    down_threshold: 90
    body_line_tolerance: 15
    hip_sag_ratio: 0.20
    check_knees_straight: true
    min_phase_seconds: 0.3
    rules_enabled: [body_line, hip_position, knees_straight, full_rom]
  advanced:
    up_threshold: 165
    down_threshold: 80
    body_line_tolerance: 10
    hip_sag_ratio: 0.12
    check_knees_straight: true
    min_phase_seconds: 0.6     # bajada controlada
    symmetry_tolerance: 12     # diferencia codo izq/der (si vista frontal-oblicua)
    rules_enabled: [body_line, hip_position, knees_straight, full_rom, tempo, symmetry]
messages:
  body_line:     "Mantén el cuerpo en línea recta"
  hip_position:  "Caderas a la altura de hombros y tobillos"
  full_rom:      "Baja más: pecho cerca del suelo"
  tempo:         "Baja más despacio (≥ 2 s)"
```
> Los valores son **punto de partida**; se calibrarán con vídeos reales (§12).

### 7.3 Catálogo MVP

| Ejercicio | Vista ideal | Métrica de fase | Reglas principales | Reglas avanzadas |
|---|---|---|---|---|
| **Flexiones** | Perfil | Ángulo de codo (hombro-codo-muñeca) | Línea cuerpo (hombro-cadera-tobillo), caderas no hundidas/elevadas, piernas rectas, rango completo | Tempo controlado, simetría, codos ≤ 45–60° del torso |
| **Sentadillas** | Perfil (frontal para rodillas) | Ángulo de rodilla (cadera-rodilla-tobillo) | Profundidad (muslo vs. paralelo), inclinación del tronco, rodillas no pasan excesivamente la punta del pie, talones apoyados | Valgo de rodilla (vista frontal), simetría, tempo, profundidad bajo paralelo |
| **Abdominales** (crunch/sit-up) | Perfil | Ángulo de cadera/tronco (hombro-cadera-rodilla) | Rango de elevación del tronco, rodillas flexionadas ~90°, no tirar del cuello (mano-cabeza-hombro) | Control de bajada, sin impulso (velocidad máxima), pies fijos |
| **Plancha** (isométrico) | Perfil | Tiempo en posición válida (cronómetro) | Línea del cuerpo, caderas, codos bajo hombros, cabeza neutra | Penalización por micro-pérdidas de postura, tiempo objetivo |
| **Zancadas** | Perfil | Ángulo rodilla delantera | Rodilla delantera ~90°, tronco vertical, rodilla trasera cerca del suelo | Equilibrio (oscilación lateral de caderas), simetría entre piernas |

> **Siguientes candidatos (fase 2):** puente de glúteos, jumping jacks, fondos en banco, burpees, elevaciones de rodilla.

### 7.4 Máquina de estados de repeticiones (base común)
```
        ángulo cruza down_threshold            ángulo cruza up_threshold
 UP  ─────────────────────────────►  DOWN  ─────────────────────────────►  UP (+1 rep)
 (esperando)                      (fase excéntrica/concéntrica)         evaluar errores acumulados
```
Mejoras sobre la práctica original:
- **Histéresis** y confirmación de N frames para evitar falsos disparos.
- **Acumular errores durante toda la repetición** (no solo en el instante final).
- Registrar por repetición: duración, ángulo mínimo/máximo, errores, **puntuación 0–100**.
- Rechazar movimientos demasiado rápidos o parciales (no cuentan o cuentan como «incompleta»).
- Estados de sistema: `NO_PERSON`, `POSITIONING`, `READY`, `ACTIVE`, `PAUSED`.

### 7.5 Puntuación
```
puntuación_rep = 100 − Σ penalización(error) × severidad
severidad = desviación_sobre_tolerancia / tolerancia   (acotada 0–1)
```
Resumen de sesión: repeticiones válidas / parciales / incorrectas, puntuación media, **errores más frecuentes** («3 de 10 con caderas hundidas») y tendencia de fatiga (la técnica empeora en las últimas repeticiones).

---

## 8. Salida de vídeo corregido (overlay)

Elementos dibujados sobre el vídeo:
- **Esqueleto** con colores según estado: 🟦 azul = correcto · 🟧 naranja = advertencia · 🟥 rojo = error (la paleta cromática de la UI es azul, pero el semáforo de errores debe ser universalmente comprensible).
- **Arcos y valores de ángulo** en articulaciones clave (codo, rodilla, cadera).
- **Línea guía ideal** (ej.: línea recta hombro-tobillo) frente a la real, para visualizar la desviación.
- **Panel**: ejercicio, nivel, repeticiones (✔ / ✖), puntuación, cronómetro (plancha).
- **Mensajes de corrección** con texto y, opcionalmente, **marca temporal** en la línea de tiempo.
- **Resumen final** (últimos 3–5 s): puntuación, errores frecuentes, consejo principal.
- Texto con **Pillow + fuente TTF** (soporta tildes, `°`, emojis simples) → resuelve la limitación n.º 5.

Extras de exportación: **informe JSON** (frame a frame resumido), **informe PDF** de la sesión y **CSV** de ángulos para análisis.

---

## 9. API (resumen)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/exercises` | Catálogo de ejercicios, niveles y vistas recomendadas |
| `POST` | `/api/videos` | Sube vídeo (`exercise`, `level`) → `job_id` |
| `GET` | `/api/jobs/{id}` | Estado y progreso (`queued/processing/done/error`, %) |
| `GET` | `/api/videos` | Listado con filtros (ejercicio, nivel, fecha, favorito, texto) |
| `GET` | `/api/videos/{id}` | Metadatos + informe |
| `GET` | `/api/videos/{id}/stream` | Vídeo procesado (con soporte `Range`) |
| `GET` | `/api/videos/{id}/original` | Vídeo original |
| `PATCH` | `/api/videos/{id}` | Renombrar, etiquetar, favorito, notas |
| `DELETE` | `/api/videos/{id}` | Eliminar (original + procesado + miniaturas) |
| `POST` | `/api/videos/{id}/reprocess` | Reprocesar con otro nivel/ejercicio sin resubir |
| `WS` | `/ws/live?exercise=&level=` | Directo: frames in → JSON out |
| `POST` | `/api/live/{session}/finish` | Sube el vídeo crudo del directo y lanza el procesado final |

### Modelo de datos (SQLite)
```
videos(id, title, exercise, level, source[upload|live], original_path, processed_path,
       thumbnail_path, duration_s, fps, created_at, favorite, notes, status)
sessions(id, video_id, reps_total, reps_ok, reps_partial, reps_bad, score_avg, report_json)
reps(id, session_id, index, start_t, end_t, min_angle, max_angle, score, errors_json)
tags(id, name)  ·  video_tags(video_id, tag_id)
settings(key, value)   # preferencias: voz, idioma, nivel por defecto, tema
```

---

## 10. Diseño de la interfaz (sencilla, deportiva, azules)

### 10.1 Sistema de diseño
| Token | Valor | Uso |
|---|---|---|
| `--blue-900` | `#0B2545` | Fondo oscuro / cabeceras |
| `--blue-700` | `#13408A` | Botones primarios (hover) |
| `--blue-500` | `#1E6FF2` | **Color principal**, acciones |
| `--blue-300` | `#6FA8FF` | Detalles, gráficas |
| `--blue-100` | `#E6F0FF` | Fondos de tarjeta (modo claro) |
| `--cyan-400` | `#22D3EE` | Acento / progreso |
| `--ok` / `--warn` / `--bad` | `#16A34A` / `#F59E0B` / `#DC2626` | Solo para feedback técnico |

- Tipografía: **Inter** (o Poppins para títulos). Bordes redondeados (12–16 px), sombras suaves.
- **Modo claro y oscuro** (el oscuro es el predeterminado en directo para reducir distracciones).
- Iconografía clara por ejercicio; botones grandes (se usará a distancia de la pantalla).
- Accesibilidad: contraste AA, no depender solo del color (iconos + texto), mensajes de voz opcionales.

### 10.2 Pantallas

**1. Inicio**
```
┌──────────────────────────────────────────┐
│  EPIA                         ⚙️  🌙      │
├──────────────────────────────────────────┤
│  1) Elige ejercicio                      │
│  [💪 Flexiones][🦵 Sentadillas][🔥 Abdo] │
│  [⏱️ Plancha ][🚶 Zancadas ]             │
│                                          │
│  2) Nivel de corrección                  │
│  ( 🟢 Fácil )( 🔵 Medio )( 🔷 Avanzado ) │
│                                          │
│  3) ¿Cómo quieres entrenar?              │
│  [ 📹 En directo ]   [ 📁 Subir vídeo ]  │
└──────────────────────────────────────────┘
```

**2. Directo:** vista de cámara grande con overlay · panel lateral (reps, puntuación, mensaje actual) · guía de colocación previa · botones *Pausar / Terminar y guardar* · interruptor de voz.

**3. Subir vídeo:** arrastrar y soltar, vista previa, barra de progreso del job, aviso de requisitos (vídeo de perfil, cuerpo completo, buena luz).

**4. Resultado:** reproductor con vídeo corregido · **línea de tiempo con marcadores de error clicables** · lista de repeticiones con su puntuación · botón *Comparar con original* (lado a lado) · *Reprocesar con otro nivel* · *Descargar*.

**5. Biblioteca:** cuadrícula de miniaturas · filtros (ejercicio, nivel, fecha, favoritos) · búsqueda · renombrar / etiquetar / borrar · selección múltiple · vista de lista.

**6. Progreso:** gráficas de puntuación media, repeticiones por semana, errores más frecuentes, récords personales.

---

## 11. Funcionalidades adicionales recomendadas

Cosas importantes que no estaban en la petición y que aportan mucho valor:

| Prioridad | Funcionalidad | Por qué |
|---|---|---|
| 🔴 Alta | **Asistente de colocación de cámara** («aléjate», «gírate de perfil», «se te cortan los pies») | La calidad de la detección depende más de la cámara que del modelo |
| 🔴 Alta | **Indicador de confianza / «no te veo bien»** en vez de corregir en falso | Evita feedback erróneo y frustración |
| 🔴 Alta | **Procesado local y privacidad** (nada sale del equipo, borrado total en un clic) | Son vídeos de personas; sensible (RGPD) |
| 🔴 Alta | **Aviso de salud** y modo «principiante» por defecto | Seguridad del usuario |
| 🟠 Media | **Feedback por voz** (SpeechSynthesis del navegador, mensajes cortos, con límite de frecuencia) | No miras la pantalla mientras entrenas |
| 🟠 Media | **Cuenta atrás y temporizador de descansos** / series y objetivos | Convierte la herramienta en un entrenamiento real |
| 🟠 Media | **Modo series**: p. ej. 3×10 con descanso | Uso real en gimnasio |
| 🟠 Media | **Comparar dos vídeos** (antes / después) | Mide mejora |
| 🟠 Media | **Detección de fatiga** (la técnica se degrada) | Prevención de lesiones |
| 🟡 Baja | Informe PDF para compartir con entrenador/a | Útil en contexto profesional |
| 🟡 Baja | Idiomas ES/EN (i18n desde el principio) | Escalable |
| 🟡 Baja | PWA / acceso desde el móvil en la red local (usar el móvil como cámara) | Mejor ángulo de cámara |
| 🟡 Baja | Detección de ejercicio automática («esto parece una sentadilla») | Comodidad (fase futura) |
| 🟡 Baja | Ajuste del modelo con datos propios (fine-tuning) para ejercicios concretos | Precisión futura |

---

## 12. Estrategia de pruebas y calibración

1. **Pruebas unitarias**: geometría (ángulos conocidos), FSM de repeticiones (secuencias sintéticas de ángulos), reglas por nivel.
2. **Dataset propio de validación**: 5–10 vídeos cortos por ejercicio (correcto, y con cada error típico provocado a propósito), distintas personas, luz y ángulos. Etiquetar manualmente número de repeticiones y errores.
3. **Métricas objetivo (MVP)**
   - Conteo de repeticiones: **≥ 95 %** de acierto en vídeos de perfil bien encuadrados.
   - Detección de errores marcados: **recall ≥ 80 %**, falsos positivos **< 15 %** en nivel Medio.
   - Latencia en directo: **< 150 ms** por frame (GPU) / **< 300 ms** (CPU).
   - Vídeo offline: velocidad ≥ 1× tiempo real en GPU, ≥ 0.5× en CPU.
4. **Calibración con profesional**: revisar umbrales de cada nivel con un/a entrenador/a.
5. **Pruebas de robustez**: ropa holgada, poca luz, oclusión parcial, varias personas, cámara baja/alta.
6. **CI**: lint (ruff), tipos (mypy), tests (pytest), build frontend.

---

## 13. Hoja de ruta por fases

| Fase | Objetivo | Entregables | Criterio de aceptación | Esfuerzo orientativo |
|---|---|---|---|---|
| **0. Preparación** | Entorno y repo | WSL2 + Python + Node + FFmpeg + repo, `AGENTS.md`, `Makefile` | `make dev` levanta backend y frontend vacíos | 0,5–1 día |
| **1. Núcleo de pose** | Migrar el notebook a módulos | `PoseEstimator`, `geometry`, `smoothing`, selección de persona, tests | Reproduce la práctica de flexiones desde un script con suavizado | 2–3 días |
| **2. Motor de ejercicios** | Arquitectura de analizadores + niveles YAML | `ExerciseAnalyzer`, FSM, `pushup` y `squat` con 3 niveles | Cuenta reps correctamente en vídeos de prueba; tests verdes | 3–4 días |
| **3. Pipeline de vídeo** | Vídeo → vídeo corregido | `pipeline.py`, `render.py` (Pillow), FFmpeg, informe JSON | Vídeo H.264 reproducible en navegador con overlay y resumen | 3 días |
| **4. Backend/API** | Subida, jobs, biblioteca | FastAPI, SQLite, cola de trabajos, endpoints de §9 | Subir → procesar → descargar vía API; borrar limpia ficheros | 3–4 días |
| **5. Frontend base** | UI azul, flujo de subida y biblioteca | Pantallas 1, 3, 4, 5; tema claro/oscuro | Flujo completo subir-ver-gestionar sin tocar la terminal | 4–5 días |
| **6. Modo directo** | WebSocket + overlay en cliente + grabación | Asistente de colocación, cuenta atrás, MediaRecorder, reproceso final | Sesión en directo genera vídeo corregido guardado en biblioteca | 4–5 días |
| **7. Más ejercicios** | Abdominales, plancha, zancadas | Analizadores + YAML + tests + vídeos de validación | Cada ejercicio cumple métricas de §12 | 4–6 días |
| **8. Calidad y extras** | Voz, series, progreso, PDF, i18n | Pantalla de progreso, informe PDF, feedback por voz | Checklist de §11 (prioridad alta y media) cubierta | 4–5 días |
| **9. Cierre** | Pulido, docs, empaquetado | README, guía de cámara, Docker, vídeo demo | Instalación desde cero siguiendo el README en < 30 min | 2 días |

**Total orientativo:** ~6–8 semanas en solitario a ritmo parcial; el **MVP utilizable** (fases 0–5, con flexiones y sentadillas, subida de vídeo y biblioteca) en **~3 semanas**.

---

## 14. Cómo trabajar con Google Antigravity

### 14.1 Preparación del entorno (WSL2 + Ubuntu)
```bash
# En PowerShell (Windows, una sola vez)
wsl --install -d Ubuntu-24.04
wsl --update

# Dentro de Ubuntu (WSL)
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip \
     ffmpeg git build-essential libgl1 libglib2.0-0
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs

# Proyecto
mkdir -p ~/posecoach && cd ~/posecoach && git init
python3.11 -m venv .venv && source .venv/bin/activate
pip install "ultralytics" fastapi "uvicorn[standard]" python-multipart sqlalchemy \
            pillow numpy opencv-python-headless pyyaml pytest ruff
# GPU NVIDIA (opcional): instalar PyTorch con CUDA según https://pytorch.org
```
> Trabaja **dentro del sistema de ficheros de WSL** (`~/posecoach`), no en `/mnt/c/...`: es mucho más rápido.
> Comprueba en tu versión de Antigravity cómo abrir carpetas de WSL (extensión/remoto tipo VS Code). Si tu versión no lo soporta, abre el proyecto por la ruta `\\wsl$\Ubuntu-24.04\home\<usuario>\posecoach` y lanza los comandos en una terminal WSL.

### 14.2 Fichero `AGENTS.md` (reglas persistentes para los agentes)
Incluye en la raíz del repo:
```markdown
# Reglas del proyecto EPIA (Entrenador Personal de Inteligencia Artificial)
- Python 3.11+, tipado estático, formateo con ruff. Frontend React + TS + Tailwind.
- Toda lógica de ejercicios vive en backend/app/core/exercises/, una clase por ejercicio.
- Los umbrales NUNCA se hardcodean: van en backend/configs/exercises/*.yaml por nivel.
- Distancias normalizadas por longitud de torso, nunca en píxeles.
- No usar cv2.putText para texto con tildes/símbolos: usar render.py (Pillow).
- Cada regla nueva requiere test unitario con secuencias sintéticas.
- Procesado 100 % local, sin llamadas a servicios externos.
- Paleta azul definida en frontend/src/theme; no introducir colores sueltos.
- Antes de dar una tarea por terminada: `make lint test` en verde.
```

### 14.3 Estrategia de agentes
- **Una fase = una conversación/tarea de agente** con criterio de aceptación explícito (§13).
- Pide al agente que **plantee un plan y lo revises** antes de generar código (fases 2, 3 y 6 son las críticas).
- Usa el navegador integrado del agente para verificar la UI (fases 5 y 6) y revisa los artefactos/capturas que genere.
- Commits pequeños por fase; ramas `feat/fase-N`.

### 14.4 Prompts sugeridos (copiar y pegar)

**Fase 1 — Núcleo de pose**
> «Lee `flexiones.ipynb`. Crea `backend/app/core/pose/` con una interfaz `PoseEstimator` y la implementación YOLO11-pose. Añade `geometry.py` (ángulo con `atan2`, normalización por longitud de torso), `smoothing.py` (One-Euro) y selección de la persona principal. Incluye tests unitarios. No toques la lógica de ejercicios todavía.»

**Fase 2 — Motor de ejercicios**
> «Implementa `ExerciseAnalyzer` (clase base con FSM de repeticiones, histéresis, acumulación de errores por repetición y puntuación 0–100) y los analizadores `pushup` y `squat` leyendo umbrales de YAML por nivel (fácil/medio/avanzado). Entrega primero un plan y espera mi aprobación. Añade tests con secuencias sintéticas de ángulos.»

**Fase 3 — Pipeline de vídeo**
> «Crea `pipeline.py` que procese un vídeo completo con el analizador elegido y genere un vídeo con overlay (esqueleto coloreado, ángulos, panel de reps, mensajes) usando Pillow para el texto, lo recodifique con FFmpeg a H.264/yuv420p conservando audio y genere un informe JSON. Añade barra de progreso por callback.»

**Fase 6 — Directo**
> «Implementa el WebSocket `/ws/live`: el cliente envía frames JPEG a ~12 FPS y el servidor responde JSON con keypoints, ángulos, estado y feedback. En el frontend dibuja el overlay en `<canvas>`, graba con MediaRecorder y, al finalizar, sube el vídeo para reprocesarlo con el pipeline offline. Incluye asistente de colocación y cuenta atrás.»

---

## 15. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Ángulos de cámara inadecuados → falsos errores | Alta | Alto | Asistente de colocación, indicador de confianza, vista recomendada por ejercicio |
| Rendimiento insuficiente en CPU en directo | Media | Medio | Modelo nano, reducir resolución/FPS, salto adaptativo de frames, vídeo final offline |
| Umbrales incorrectos para algunos cuerpos/morfologías | Media | Alto | Normalización, niveles con tolerancia, calibración con profesional, ajustes por usuario |
| Licencia AGPL si se comercializa | Media | Alto | Interfaz `PoseEstimator` + plan B MediaPipe/RTMPose o licencia enterprise |
| Webcam en WSL2 | Alta | Medio | Captura en navegador (§3.2) |
| Vídeos no reproducibles en navegador | Media | Medio | FFmpeg H.264 + `yuv420p` + `faststart` |
| Oclusiones (suelo, ropa, mobiliario) en ejercicios tumbado | Alta | Medio | Interpolación corta, mensaje de reencuadre, vista de perfil con espacio libre |
| Privacidad de los vídeos | Media | Alto | Todo local, borrado total, sin telemetría, aviso en primer uso |
| Lesiones por seguir consejos erróneos | Baja | Muy alto | Aviso de salud, reglas de seguridad prioritarias, validación profesional |

---

## 16. Definición de «hecho» del MVP

- [ ] Elegir **ejercicio** (mín. flexiones y sentadillas) y **nivel** (fácil/medio/avanzado) desde la UI.
- [ ] **Subir un vídeo** y obtener el vídeo con esqueleto, ángulos, contador y mensajes de corrección.
- [ ] **Modo directo** con feedback en pantalla y vídeo corregido guardado al terminar.
- [ ] **Biblioteca**: listar, reproducir, renombrar, etiquetar, favorito, descargar y borrar.
- [ ] Diseño en tonos azules, claro/oscuro, usable sin manual.
- [ ] Funciona en **WSL2** con acceso desde el navegador de Windows.
- [ ] Tests unitarios y de validación pasan; métricas de §12 cumplidas en el dataset propio.
- [ ] README con instalación desde cero.

---

## 17. Próximos pasos inmediatos

1. Crear el repo y el fichero `AGENTS.md` (§14.2).
2. Preparar WSL2 + dependencias (§14.1).
3. **Grabar el dataset de validación** (vídeos de perfil, buen encuadre, con errores provocados): es lo que más condicionará la calidad final y conviene empezar cuanto antes.
4. Lanzar la **Fase 1** con el prompt de §14.4 y revisar el plan del agente antes de aprobar.
5. Una vez validada la Fase 2 con flexiones y sentadillas, decidir qué ejercicio adicional priorizar.
