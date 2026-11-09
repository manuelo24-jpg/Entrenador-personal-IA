# 🏋️ EPIA — Entrenador Personal de Inteligencia Artificial

**EPIA** (*Entrenador Personal de Inteligencia Artificial*) es una aplicación web 100 % local para el análisis biomecánico, conteo de repeticiones y corrección postural de ejercicios físicos mediante visión por computador (**YOLO11-pose**).

> ⚠️ **Aviso de salud:** EPIA es una herramienta orientativa de apoyo al entrenamiento y no sustituye la supervisión de un profesional sanitario, fisioterapeuta o entrenador titulado. Detén el ejercicio inmediatamente si sientes dolor o molestia.

---

## 🌐 Puertos y URLs de la aplicación

| Servicio | Puerto | URL de acceso | Descripción |
|---|---:|---|---|
| **Frontend Web (UI EPIA)** | `5173` | **http://localhost:5173** | Interfaz principal de usuario (React + Vite + Tailwind). **Abre esta URL en tu navegador.** |
| **Backend API (FastAPI)** | `8010` | `http://localhost:8010` | Servidor REST y motor de visión por computador. |
| **Documentación Swagger / OpenAPI** | `8010` | `http://localhost:8010/docs` | Documentación interactiva para probar todos los endpoints REST. |
| **Health Check** | `8010` | `http://localhost:8010/api/health` | Estado de salud del servidor. |
| **WebSocket Modo en Directo** | `8010` | `ws://localhost:8010/ws/live` | Canal en tiempo real para el modo webcam (proxificado automáticamente desde el puerto `5173`). |

> 💡 **Nota sobre el proxy:** El servidor de desarrollo de Vite (`5173`) redirige automáticamente todas las peticiones `/api/*` y `/ws/*` hacia el backend (`127.0.0.1:8010`), por lo que solo necesitas abrir **http://localhost:5173** en tu navegador.

---

## ✨ Características principales

- **5 Ejercicios incluidos (MVP):**
  - 💪 **Flexiones** (*Push-ups*) — control de línea corporal, caderas, extensión de rodillas, profundidad y tempo.
  - 🦵 **Sentadillas** (*Squats*) — profundidad respecto al paralelo, inclinación del tronco, avance de rodilla y simetría.
  - 🔥 **Abdominales** (*Sit-ups / Crunches*) — rango de elevación, flexión de rodillas, control cervical y velocidad sin impulso.
  - ⏱️ **Plancha** (*Plank*) — ejercicio isométrico por tiempo efectivo manteniendo alineación hombro-cadera-tobillo.
  - 🚶 **Zancadas** (*Lunges*) — ángulo de rodilla delantera (~90°), verticalidad del tronco y descenso de rodilla trasera.
- **3 Niveles de exigencia configurables por YAML (`backend/configs/exercises/*.yaml`):**
  - 🟢 **Fácil (`easy`):** Tolerancias amplias centradas en seguridad básica y aprendizaje del patrón motor.
  - 🔵 **Medio (`medium`):** Técnica estándar con recorrido completo (ROM).
  - 🔷 **Avanzado (`advanced`):** Precisión biomecánica, control de tempo excéntrico y simetría.
- **Doble modo de entrenamiento:**
  - 📁 **Subir vídeo:** Procesado frame a frame con suavizado One-Euro, generación de vídeo H.264 con overlay Unicode (Pillow), línea de tiempo interactiva de errores e informe detallado.
  - 📹 **En directo (Webcam):** Asistente de colocación en cámara, cuenta atrás 3-2-1, feedback visual en tiempo real vía WebSocket, síntesis de voz (`SpeechSynthesis`) y grabación automática para reprocesado final de alta calidad.
- **Biblioteca y Progreso:**
  - Gestión local con SQLite (`data/epia.db`), filtros por ejercicio/nivel/favoritos, búsqueda, comparación lado a lado con el vídeo original, reprocesado con otro nivel y gráficas de evolución.

---

## 🚀 Requisitos previos

- **Python 3.11+** (verificado también con Python 3.14)
- **Node.js 20+** y **npm 10+**
- **FFmpeg:** Opcional en el PATH del sistema; el proyecto incluye soporte automático embebido mediante `imageio-ffmpeg`.

---

## 🛠️ Instalación desde cero (Primera vez)

### Paso 1: Configurar el Backend (Python + FastAPI)

Abre una terminal en la raíz del proyecto (`Entrenador personal IA`):

**En Windows (PowerShell):**
```powershell
# 1. Crear el entorno virtual
python -m venv backend\.venv

# 2. Instalar dependencias del backend y herramientas de test/lint
.\backend\.venv\Scripts\pip.exe install -e "backend[dev]"

# 3. (Opcional) Instalar motor YOLO11-pose de Ultralytics si aún no está instalado
.\backend\.venv\Scripts\pip.exe install -e "backend[yolo]"
```

**En Linux / WSL2 / macOS:**
```bash
python3 -m venv backend/.venv
./backend/.venv/bin/pip install -e "backend[dev,yolo]"
```

### Paso 2: Configurar el Frontend (React + TypeScript + Vite)

```powershell
cd frontend
npm install
cd ..
```

---

## ▶️ Cómo arrancar la aplicación

Para utilizar **EPIA**, necesitas tener en ejecución simultáneamente el **Backend** (puerto `8010`) y el **Frontend** (puerto `5173`) en dos terminales (o usar el script rápido `start_epia.ps1`).

### Opción A: Arranque rápido en Windows (un solo comando)
Desde la raíz del proyecto en PowerShell:
```powershell
.\start_epia.ps1
```

### Opción B: Arranque manual en 2 terminales

#### Terminal 1 — Levantar el Backend (Puerto `8010`)
**Windows (PowerShell):**
```powershell
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8010
```
**Linux / WSL2 / macOS:**
```bash
cd backend
./.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```
Verás en consola: `Uvicorn running on http://127.0.0.1:8010`

#### Terminal 2 — Levantar el Frontend (Puerto `5173`)
```powershell
cd frontend
npm run dev
```
Verás en consola: `Local: http://localhost:5173/`

👉 **Abre tu navegador en:** **[http://localhost:5173](http://localhost:5173)**

---

## 🧪 Ejecutar pruebas y linter

Desde la raíz del proyecto:

```powershell
# Ejecutar tests unitarios (geometría, suavizado One-Euro, analizadores de los 5 ejercicios y API)
.\backend\.venv\Scripts\pytest.exe backend/tests -v

# Ejecutar linter y comprobación de formato con Ruff
.\backend\.venv\Scripts\ruff.exe check backend/app backend/tests
```
