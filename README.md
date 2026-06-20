# QWK Analysis

Sistema de análisis de evaluaciones de lectura realizadas por expertos.

## Estructura del Proyecto

```
qwk-analysis/
├── .instructions.md          # Configuración de autocomplete
├── README.md                # Este archivo
├── scripts/                 # Scripts de procesamiento
│   ├── csv_to_json.py      # Conversión CSV → JSON (versión 1)
│   └── convert_clean.py    # Conversión CSV → JSON (versión optimizada)
├── data/                   # Datos de entrada/salida
│   ├── evaluacion_expertos.csv    # Datos originales
│   ├── evaluacion_expertos.json   # JSON convertido
│   └── datos_lectura.json         # Versión alternativa
├── docs/                   # Documentación
└── config/                 # Archivos de configuración
```

## Archivos de Datos

### evaluacion_expertos (CSV/JSON)
- **Registros**: 32 evaluaciones de lectura
- **Campos**:
  - `ID LECTURA`: Identificador único
  - `GRADO`: Nivel escolar (1-4)
  - `Estrategia silábica`: Estado de desarrollo (inicial/en proceso/logrado/avanzado)
  - `Manejo del ritmo`: Estado de desarrollo
  - `Manejo de la respiracion`: Estado de desarrollo
  - `Precisión`: Estado de desarrollo
  - `Fluidez (p/m)`: Palabras por minuto

## Scripts Disponibles

### convert_clean.py (RECOMENDADO)
Script optimizado para convertir CSV a JSON.

```bash
python scripts/convert_clean.py
```

**Características**:
- Parseo correcto de headers (fila 3)
- Filtra columnas de rúbrica innecesarias
- Convierte tipos de datos automáticamente (números/strings)
- Genera JSON limpio y legible

### csv_to_json.py
Primera versión con manejo de errores extendido.

## Próximos Pasos

Integración con `audio-cleaner` para:
- Procesar audios de lectura
- Calcular métricas de WPM
- Validar coincidencia audio-texto
- Generar evaluaciones automáticas

## Configuración Automática

El proyecto está configurado con `.instructions.md` para:
- ✅ Ejecutar acciones sin confirmaciones innecesarias
- ✅ Seguir estructura de carpetas ordenadas
- ✅ Implementar scripts en Python 3.12+
