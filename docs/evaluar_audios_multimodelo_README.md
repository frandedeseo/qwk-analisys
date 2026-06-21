# Script: Evaluar Audios Multimodelo

## Descripción
Script que procesa 32 audios de lectura (8 por grado) mediante 3 modelos distintos, enviándolos al backend `audio-cleaner` para evaluación automática.

## Requisitos
- Backend `audio-cleaner` ejecutándose en `http://localhost:8000`
- Python 3.8+
- Librerías: `requests` (instalar con `pip install requests`)

## Estructura de Entrada

```
qwk-analisys/
├── audios-para-evaluar/
│   ├── 1er grado/         (8 archivos .wav)
│   ├── 2do grado/         (8 archivos .wav)
│   ├── 3er grado/         (8 archivos .wav)
│   └── 4to grado/         (8 archivos .wav)
└── data/
    └── datos_lectura.json
```

## Estructura de Salida

```
prueba-1/
├── gemini-flash/
│   ├── 1er-grado.json
│   ├── 2do-grado.json
│   ├── 3er-grado.json
│   └── 4to-grado.json
├── gemini-pro/
│   ├── 1er-grado.json
│   ├── 2do-grado.json
│   ├── 3er-grado.json
│   └── 4to-grado.json
└── openai-audio/
    ├── 1er-grado.json
    ├── 2do-grado.json
    ├── 3er-grado.json
    └── 4to-grado.json
```

## Modelos Soportados

| Modelo | Parámetro | Descripción |
|--------|-----------|-------------|
| Gemini 3.5 Flash | `gemini-flash` | Rápido y estable |
| Gemini 3.1 Pro | `gemini-pro` | Razonamiento avanzado |
| GPT-Audio-1.5 | `openai-audio` | OpenAI multimodal |

## Uso

### Paso 1: Iniciar Backend
```bash
# En otra terminal, desde el repo audio-cleaner
cd c:\Users\frand\audio-cleaner
python main.py
# O con uvicorn:
# uvicorn main:app --reload
```

### Paso 2: Ejecutar Script
```bash
cd c:\Users\frand\source\qwk-analisys
python scripts/evaluar_audios_multimodelo.py
```

### Output Esperado
```
======================================================================
GENERADOR DE EVALUACIONES MULTIMODELO
======================================================================

[1/5] Validando configuración...
✓ Cargados 32 registros de evaluación

[2/5] Escaneando audios...
✓ 1er grado: 8 audios encontrados
✓ 2do grado: 8 audios encontrados
✓ 3er grado: 8 audios encontrados
✓ 4to grado: 8 audios encontrados
✓ Total de audios encontrados: 32

[3/5] Preparando directorios...
✓ Estructura de directorios creada

[4/5] Iniciando evaluaciones...
Configuración: 3 modelos × 4 grados × 8 audios = 96 evaluaciones

...procesando...

[5/5] Guardando resultados...
✓ gemini-flash    > 1er-grado  : 8 evaluaciones
✓ gemini-flash    > 2do-grado  : 8 evaluaciones
...

======================================================================
RESUMEN
======================================================================
Total de intentos: 96
Exitosos: 96
Tasa de éxito: 100.0%
Salida: C:\Users\frand\source\qwk-analisys\prueba-1
======================================================================
```

## Contenido de JSONs de Salida

Cada archivo contiene un array de evaluaciones:

```json
[
  {
    "id_lectura": 52866,
    "archivo": "lectura_52866_2025-10-29_13-42-40.wav",
    "modelo": "gemini-flash",
    "evaluacion": {
      "estrategia_silabica": {
        "nivel": "Logrado",
        "comentario": "El alumno utiliza correctamente la estrategia silábica..."
      },
      "manejo_ritmo": {
        "nivel": "En proceso",
        "comentario": "Lee con cierta entonación pero aún monótona..."
      },
      "manejo_respiracion": {
        "nivel": "Inicial",
        "comentario": "No hace pausas adecuadas..."
      },
      "precision": {
        "nivel": "Logrado",
        "comentario": "Cometió 1-2 errores aislados..."
      },
      "fluidez_lectora": {
        "nivel": "En proceso",
        "comentario": "60 WPM - Etapa Ortográfica"
      }
    },
    "timestamp": "2026-06-21T10:30:45.123456"
  },
  ...
]
```

## Características del Script

✅ **Reintentos automáticos**: Si falla un audio, reintenta 3 veces  
✅ **Manejo de errores robusto**: Continúa si falla un audio, sin detener todo  
✅ **Progress tracking**: Muestra progreso en tiempo real  
✅ **Validación de entrada**: Verifica que existan archivos y backend  
✅ **Timestamps**: Registra cuándo se realizó cada evaluación  
✅ **Logging detallado**: Información clara de éxito/fracaso  

## Troubleshooting

### Error: "Conexión rechazada"
```
✗ Conexión rechazada para 52866: ¿Backend activo?
```
**Solución**: Asegúrate que audio-cleaner está ejecutándose en `http://localhost:8000`

### Error: "Carpeta no encontrada"
```
✗ 1er grado: Carpeta no encontrada
```
**Solución**: Verifica que los audios están en `audios-para-evaluar/[grado]/`

### Error: "Timeout"
```
✗ Error inesperado: Read timed out
```
**Solución**: El backend está lento. Aumenta `timeout=60` en la línea de `requests.post()`

## Variables Configurables

En el script puedes ajustar:

```python
BASE_URL = "http://localhost:8000"  # URL del backend
ENDPOINT = f"{BASE_URL}/evaluar-lectura"  # Endpoint
MAX_REINTENTOS = 3  # Número de reintentos por audio
timeout = 60  # Segundos de timeout por request
```

## Próximo Paso

Una vez completadas las 96 evaluaciones, puedes ejecutar:
```bash
python scripts/calcular_qwk.py  # Script para calcular métrica QWK
```
