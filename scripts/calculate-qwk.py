"""
Calcula Quadratic Weighted Kappa (QWK) entre evaluaciones predichas y ground truth.

Ignora fluidez lectora.
Reporta QWK:
  - Por modelo (todos los grados agrupados)
  - Por grado × modelo
Dentro de cada reporte: un valor por criterio + promedio de los 4.
Exporta también un CSV para análisis posterior.

Uso:
    python calcular_qwk.py
    python calcular_qwk.py --salida prueba-1  # override del directorio de resultados
"""

import json
import csv
import argparse
from pathlib import Path
from collections import defaultdict

import numpy as np
from sklearn.metrics import cohen_kappa_score

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

PROYECTO_ROOT = Path(__file__).parent.parent
SALIDA_DIR    = PROYECTO_ROOT / "prueba-1"
DATOS_JSON    = PROYECTO_ROOT / "data" / "datos_lectura.json"

MODELOS = ["gemini-flash", "gemini-pro", "openai-audio"]

NOMBRE_GRADOS = {
    1: "1er-grado",
    2: "2do-grado",
    3: "3er-grado",
    4: "4to-grado",
}

# Escala ordinal compartida por ground truth y predicciones
NIVEL_A_INT = {
    "inicial":    0,
    "en proceso": 1,
    "logrado":    2,
    "avanzado":   3,
}

# (clave en ground truth JSON, clave en el dict de criterios predicho)
CRITERIOS = [
    ("Estrategia silábica",     "estrategia_silabica"),
    ("Manejo del ritmo",        "manejo_ritmo"),
    ("Manejo de la respiracion","manejo_respiracion"),
    ("Precisión",               "precision"),
]

# Labels cortos para tablas
LABEL_CORTO = {
    "Estrategia silábica":      "Silábica",
    "Manejo del ritmo":         "Ritmo",
    "Manejo de la respiracion": "Respiración",
    "Precisión":                "Precisión",
}

# ============================================================================
# UTILIDADES
# ============================================================================

def normalizar_nivel(s) -> int | None:
    """Convierte una cadena de nivel a entero ordinal (0-3). None si no reconoce."""
    if not s:
        return None
    n = str(s).lower().strip()
    return NIVEL_A_INT.get(n)


def _id_desde_archivo(nombre: str) -> int | None:
    """Extrae el ID numérico del nombre de archivo. Ej: 'lectura_52866_2025-10-29.wav' → 52866."""
    import re
    m = re.search(r"lectura_(\d+)_", nombre)
    return int(m.group(1)) if m else None


def extraer_criterios(item: dict) -> tuple[int | None, dict | None]:
    """
    Extrae (id_lectura, dict_de_criterios) de un elemento del batch JSON.

    Resolución de id_lectura (en orden de prioridad):
      1. Campo 'id_lectura' explícito.
      2. Campo 'archivo' → regex lectura_(NUM)_.
      3. Sin ninguno → devuelve (None, None) para ser descartado.

    Maneja tres estructuras de evaluacion:

    Estructura A — batch nuevo (match_info removido):
        {
          "id_lectura": 123,
          "evaluacion": {
              "palabras_por_minuto": ...,
              "evaluacion": {                <- criterios reales aquí
                  "estrategia_silabica": {"nivel": ..., "comentario": ...},
                  ...
              }
          }
        }

    Estructura B — batch viejo (con match_info):
        {
          "id_lectura": 123,
          "evaluacion": {
              "match": true, "palabras_por_minuto": ...,
              "evaluacion": { "estrategia_silabica": ... }
          }
        }

    Estructura C — respuesta directa sin wrapper de batch (ej. test_rapido.py
                    guardado accidentalmente), sin id_lectura pero con 'archivo':
        {
          "archivo": "lectura_52866_2025-10-29.wav",
          "palabras_por_minuto": ...,
          "evaluacion": { "estrategia_silabica": ... }
        }
    """
    # 1. id_lectura explícito
    if "id_lectura" in item:
        id_lectura = item["id_lectura"]
    # 2. Intentar extraerlo del nombre de archivo
    elif "archivo" in item:
        id_lectura = _id_desde_archivo(item["archivo"])
        if id_lectura is None:
            return None, None  # nombre de archivo no tiene el patrón esperado
    else:
        return None, None  # sin forma de identificar el registro
    outer = item.get("evaluacion")

    if not isinstance(outer, dict):
        return id_lectura, None

    # Caso más común: outer["evaluacion"] contiene los criterios
    inner = outer.get("evaluacion")
    if isinstance(inner, dict) and "estrategia_silabica" in inner:
        return id_lectura, inner

    # Fallback: outer ya ES el dict de criterios
    if "estrategia_silabica" in outer:
        return id_lectura, outer

    return id_lectura, None


def calcular_qwk(y_true: list, y_pred: list) -> float | None:
    """Calcula QWK con labels=[0,1,2,3]. Devuelve None si no hay suficientes datos."""
    if len(y_true) < 2:
        return None
    try:
        return cohen_kappa_score(
            y_true, y_pred,
            weights="quadratic",
            labels=[0, 1, 2, 3]
        )
    except Exception:
        return None


def fmt(val: float | None, width: int = 8) -> str:
    """Formatea un QWK para tabla."""
    s = f"{val:+.3f}" if val is not None else "N/A"
    return s.center(width)


# ============================================================================
# CARGA DE DATOS
# ============================================================================

def cargar_ground_truth(path: Path) -> dict[int, dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {item["ID LECTURA"]: item for item in data}


def cargar_predicciones(salida_dir: Path, modelo: str, grado: int) -> list[dict]:
    archivo = salida_dir / modelo / f"{NOMBRE_GRADOS[grado]}.json"
    if not archivo.exists():
        return []
    with open(archivo, encoding="utf-8") as f:
        return json.load(f)


# ============================================================================
# CONSTRUCCIÓN DE PARES (y_true, y_pred) POR CRITERIO
# ============================================================================

def construir_pares(gt: dict, salida_dir: Path):
    """
    Devuelve:
      pares[modelo][grado][gt_field] = {"y_true": [...], "y_pred": [...]}
      stats[modelo][grado] = {
          "procesados": N,   <- matcheados con GT y criterios OK
          "sin_id":     M,   <- sin id_lectura ni archivo con patron reconocible
          "sin_eval":   P,   <- tienen ID pero evaluacion con estructura irreconocible
          "sin_gt":     K,   <- ID no encontrado en ground truth
      }
    """
    advertencias = []
    pares = {}
    stats = {}

    for modelo in MODELOS:
        pares[modelo] = {}
        stats[modelo] = {}

        for grado in range(1, 5):
            pares[modelo][grado] = {
                gt_field: {"y_true": [], "y_pred": []}
                for gt_field, _ in CRITERIOS
            }
            stats[modelo][grado] = {
                "procesados": 0,
                "sin_id":     0,
                "sin_eval":   0,
                "sin_gt":     0,
            }

            predicciones = cargar_predicciones(salida_dir, modelo, grado)

            for idx, item in enumerate(predicciones):
                id_lectura, criterios_pred = extraer_criterios(item)

                if id_lectura is None:
                    stats[modelo][grado]["sin_id"] += 1
                    advertencias.append(
                        f"  ⚠ {modelo}/{NOMBRE_GRADOS[grado]} item #{idx}: "
                        f"sin 'id_lectura' ni 'archivo' reconocible — descartado."
                    )
                    continue

                if criterios_pred is None:
                    stats[modelo][grado]["sin_eval"] += 1
                    advertencias.append(
                        f"  ⚠ {modelo}/{NOMBRE_GRADOS[grado]} ID {id_lectura}: "
                        f"estructura de evaluacion no reconocida — descartado."
                    )
                    continue

                if id_lectura not in gt:
                    stats[modelo][grado]["sin_gt"] += 1
                    advertencias.append(
                        f"  ⚠ {modelo}/{NOMBRE_GRADOS[grado]} ID {id_lectura}: "
                        f"no encontrado en ground truth — descartado."
                    )
                    continue

                gt_item = gt[id_lectura]
                item_ok = True

                for gt_field, pred_field in CRITERIOS:
                    gt_nivel = normalizar_nivel(gt_item.get(gt_field, ""))

                    pred_raw = criterios_pred.get(pred_field, {})
                    if isinstance(pred_raw, dict):
                        pred_nivel = normalizar_nivel(pred_raw.get("nivel", ""))
                    else:
                        pred_nivel = normalizar_nivel(pred_raw)

                    if gt_nivel is None or pred_nivel is None:
                        item_ok = False
                        continue

                    pares[modelo][grado][gt_field]["y_true"].append(gt_nivel)
                    pares[modelo][grado][gt_field]["y_pred"].append(pred_nivel)

                if item_ok:
                    stats[modelo][grado]["procesados"] += 1
                else:
                    stats[modelo][grado]["sin_eval"] += 1

    return pares, stats, advertencias


# ============================================================================
# CÁLCULO DE QWK
# ============================================================================

def qwk_tabla(pares, scope: str, modelo: str | None = None, grado: int | None = None):
    """
    Dado un scope ("modelo" o "grado"), devuelve dict de QWKs para impresión.

    Si scope == "modelo": agrega todos los grados para ese modelo.
    Si scope == "grado":  agrega todos los modelos no (ya viene de un grado fijo y modelo fijo).
    Internamente siempre calcula por criterio + promedio.

    Retorna: {gt_field: qwk_value, "_promedio": avg_qwk}
    """
    resultado = {}

    for gt_field, _ in CRITERIOS:
        if scope == "modelo_global":
            # Un modelo, todos los grados
            y_true = []
            y_pred = []
            for g in range(1, 5):
                y_true += pares[modelo][g][gt_field]["y_true"]
                y_pred += pares[modelo][g][gt_field]["y_pred"]
        else:
            # Un modelo, un grado
            y_true = pares[modelo][grado][gt_field]["y_true"]
            y_pred = pares[modelo][grado][gt_field]["y_pred"]

        resultado[gt_field] = calcular_qwk(y_true, y_pred)

    validos = [v for v in resultado.values() if v is not None]
    resultado["_promedio"] = float(np.mean(validos)) if validos else None
    return resultado


# ============================================================================
# IMPRESIÓN DE TABLAS
# ============================================================================

COL_W  = 12   # ancho columna QWK
LABEL_W = 22  # ancho columna modelo/grado

def imprimir_tabla(titulo: str, filas: list[tuple[str, dict]]):
    """
    filas: [(label_fila, {gt_field: qwk, "_promedio": qwk}), ...]
    """
    criterio_labels = [LABEL_CORTO[c] for c, _ in CRITERIOS] + ["Promedio"]
    sep = "-" * (LABEL_W + COL_W * len(criterio_labels))

    print(f"\n{'='*len(sep)}")
    print(titulo)
    print(sep)
    header = f"{'':>{LABEL_W}}" + "".join(l.center(COL_W) for l in criterio_labels)
    print(header)
    print(sep)

    for label, qwks in filas:
        row = f"{label:>{LABEL_W}}"
        for gt_field, _ in CRITERIOS:
            row += fmt(qwks.get(gt_field), COL_W)
        row += fmt(qwks.get("_promedio"), COL_W)
        print(row)

    print(sep)


# ============================================================================
# EXPORTAR CSV
# ============================================================================

def exportar_csv(pares, salida_dir: Path):
    """Exporta una fila por (modelo, grado, criterio) con el QWK."""
    archivo = salida_dir / "qwk_resultados.csv"

    filas = []
    for modelo in MODELOS:
        for grado in range(1, 5):
            for gt_field, _ in CRITERIOS:
                yt = pares[modelo][grado][gt_field]["y_true"]
                yp = pares[modelo][grado][gt_field]["y_pred"]
                qwk = calcular_qwk(yt, yp)
                filas.append({
                    "modelo":    modelo,
                    "grado":     grado,
                    "criterio":  LABEL_CORTO[gt_field],
                    "n":         len(yt),
                    "qwk":       f"{qwk:.4f}" if qwk is not None else "",
                })

        # Fila global por modelo
        for gt_field, _ in CRITERIOS:
            yt = sum((pares[modelo][g][gt_field]["y_true"] for g in range(1, 5)), [])
            yp = sum((pares[modelo][g][gt_field]["y_pred"] for g in range(1, 5)), [])
            qwk = calcular_qwk(yt, yp)
            filas.append({
                "modelo":   modelo,
                "grado":    "GLOBAL",
                "criterio": LABEL_CORTO[gt_field],
                "n":        len(yt),
                "qwk":      f"{qwk:.4f}" if qwk is not None else "",
            })

    with open(archivo, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["modelo", "grado", "criterio", "n", "qwk"])
        writer.writeheader()
        writer.writerows(filas)

    return archivo


# ============================================================================
# MAIN
# ============================================================================

def main(salida_dir: Path):
    print("\n" + "=" * 70)
    print("QWK — EVALUACIÓN LECTORA INFANTIL")
    print(f"Directorio de resultados: {salida_dir}")
    print("=" * 70)

    if not DATOS_JSON.exists():
        print(f"✗ No se encontró ground truth en {DATOS_JSON}")
        return

    gt = cargar_ground_truth(DATOS_JSON)
    print(f"✓ Ground truth: {len(gt)} registros")

    pares, stats, advertencias = construir_pares(gt, salida_dir)

    # ── Tabla 1: por modelo (todos los grados) ──────────────────────────────
    filas_modelo = []
    for modelo in MODELOS:
        qwks = qwk_tabla(pares, scope="modelo_global", modelo=modelo)
        filas_modelo.append((modelo, qwks))

    imprimir_tabla("QWK POR MODELO  (todos los grados)", filas_modelo)

    # ── Tabla 2: por grado (desglose por modelo) ─────────────────────────────
    for grado in range(1, 5):
        filas_grado = []
        for modelo in MODELOS:
            qwks = qwk_tabla(pares, scope="grado", modelo=modelo, grado=grado)
            filas_grado.append((modelo, qwks))

        imprimir_tabla(
            f"QWK — {NOMBRE_GRADOS[grado].upper()}",
            filas_grado
        )

    # ── Resumen de datos procesados ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("DATOS PROCESADOS")
    print("-" * 70)
    print(f"{'Modelo':<18} {'Grado':<14} {'OK':>6} {'Sin ID':>8} {'Sin eval':>10} {'Sin GT':>8}")
    print("-" * 70)
    for modelo in MODELOS:
        for grado in range(1, 5):
            s = stats[modelo][grado]
            if sum(s.values()) == 0:
                continue
            print(
                f"{modelo:<18} {NOMBRE_GRADOS[grado]:<14}"
                f" {s['procesados']:>6}"
                f" {s['sin_id']:>8}"
                f" {s['sin_eval']:>10}"
                f" {s['sin_gt']:>8}"
            )
    print("-" * 70)

    # ── Advertencias de items descartados ─────────────────────────────────────
    if advertencias:
        print(f"\n⚠ {len(advertencias)} item(s) no pudieron procesarse:")
        for msg in advertencias:
            print(msg)

    # ── CSV ──────────────────────────────────────────────────────────────────
    csv_path = exportar_csv(pares, salida_dir)
    print(f"\n✓ Resultados exportados a: {csv_path}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula QWK entre predicciones y ground truth.")
    parser.add_argument(
        "--salida",
        type=Path,
        default=None,
        help="Directorio de resultados (default: prueba-1 relativo a la raíz del proyecto)"
    )
    args = parser.parse_args()

    salida = args.salida if args.salida else SALIDA_DIR
    main(salida)