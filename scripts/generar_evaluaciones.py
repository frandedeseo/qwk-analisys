"""
Script para evaluar audios de lectura mediante el backend audio-cleaner
Genera evaluaciones con 3 modelos distintos y organiza resultados por grado

Uso:
    python generar_evaluaciones.py                    -> corre los 3 modelos
    python generar_evaluaciones.py openai-audio        -> corre solo ese modelo
    python generar_evaluaciones.py gemini-flash gemini-pro  -> corre esos dos

Esto te permite re-correr solamente el/los modelo(s) que fallaron sin pisar
los JSON ya guardados de los modelos que sí funcionaron.
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
import requests
from typing import Dict, List, Optional
import time

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/evaluar-lectura"

# Textos de lectura por grado
TEXTOS_LECTURA = {
    1: "Los perros tienen muy buen olfato y oído. Es un animal inteligente y fiel. Es el mejor amigo del hombre.",
    2: "En el sistema solar hay ocho planetas. Marte es el cuarto planeta más cercano al sol. Es el segundo más pequeño. Su color es rojizo. Desde la Tierra se lo puede observar con un telescopio. Hace varios años los científicos investigan si hubo vida en ese planeta.",
    3: "Los dinosaurios son animales que vivieron en la tierra hace muchos años. Eran animales salvajes, muy feroces y peligrosos. El Tiranosaurio Rex era uno de los dinosaurios más conocidos. Era un animal de gran tamaño. Tenía dientes muy filosos y grandes garras para atrapar a sus presas.",
    4: "El búho es un ave de comportamiento nocturno. Por lo tanto, al haber escasez de luz, intercepta a sus presas a través del sonido. Es famoso y conocido por permanecer despierto durante la noche y descansar de día. A diferencia de las lechuzas, los búhos poseen plumas sobre su cabeza que son confundidas con orejas. La lechuza no posee estas plumas."
}

MODELOS_DISPONIBLES = ["gemini-flash", "gemini-pro", "openai-audio", "gemini-flash-thinking"]

# Si pasás modelos por línea de comandos, corre solo esos.
# Si no pasás nada, corre los 3 (comportamiento original).
if len(sys.argv) > 1:
    MODELOS = [m for m in sys.argv[1:] if m in MODELOS_DISPONIBLES]
    invalidos = [m for m in sys.argv[1:] if m not in MODELOS_DISPONIBLES]
    if invalidos:
        print(f"✗ Modelo(s) inválido(s): {invalidos}")
        print(f"  Disponibles: {MODELOS_DISPONIBLES}")
        sys.exit(1)
    if not MODELOS:
        print(f"✗ No especificaste ningún modelo válido. Disponibles: {MODELOS_DISPONIBLES}")
        sys.exit(1)
else:
    MODELOS = MODELOS_DISPONIBLES

NOMBRE_GRADOS = {
    1: "1er-grado",
    2: "2do-grado",
    3: "3er-grado",
    4: "4to-grado"
}

# Rutas
PROYECTO_ROOT = Path(__file__).parent.parent
AUDIOS_DIR = PROYECTO_ROOT / "audios-para-evaluar"
SALIDA_DIR = PROYECTO_ROOT / "prueba-1"
DATOS_JSON = PROYECTO_ROOT / "data" / "datos_lectura.json"

# ============================================================================
# UTILIDADES
# ============================================================================

def cargar_datos_evaluacion() -> Dict[int, dict]:
    """Carga el JSON de datos de evaluación y crea mapeo ID_LECTURA -> datos"""
    with open(DATOS_JSON, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    mapeo = {item['ID LECTURA']: item for item in datos}
    return mapeo

def extraer_id_lectura(nombre_archivo: str) -> Optional[int]:
    """Extrae el ID LECTURA del nombre del archivo
    Formato: lectura_52866_2025-10-29_13-42-40.wav
    """
    match = re.search(r'lectura_(\d+)_', nombre_archivo)
    return int(match.group(1)) if match else None

def obtener_audios_por_grado() -> Dict[int, List[Path]]:
    """Agrupa audios por grado"""
    audios = {1: [], 2: [], 3: [], 4: []}

    for i in range(1, 5):
        nombre_carpeta = f"{i}{'er' if i == 1 else 'do' if i == 2 else 'er' if i == 3 else 'to'} grado"
        carpeta = AUDIOS_DIR / nombre_carpeta

        if carpeta.exists():
            wav_files = sorted(carpeta.glob("*.wav"))
            audios[i] = wav_files
            print(f"✓ {nombre_carpeta}: {len(wav_files)} audios encontrados")
        else:
            print(f"✗ {nombre_carpeta}: Carpeta no encontrada en {carpeta}")

    return audios

def crear_estructura_directorios():
    """Crea la estructura de directorios para salida"""
    SALIDA_DIR.mkdir(exist_ok=True)
    for modelo in MODELOS:
        (SALIDA_DIR / modelo).mkdir(exist_ok=True)
    print(f"✓ Estructura de directorios creada en {SALIDA_DIR}")

def evaluar_audio(archivo_audio: Path, texto: str, modelo: str,
                  id_lectura: int, max_reintentos: int = 3) -> Optional[dict]:
    """Envía un audio al backend para evaluación

    Args:
        archivo_audio: Ruta del archivo WAV
        texto: Texto que el alumno debía leer
        modelo: Modelo a usar (gemini-flash, gemini-pro, openai-audio)
        id_lectura: ID LECTURA para referencia
        max_reintentos: Número máximo de reintentos

    Returns:
        Respuesta del backend o None si error
    """

    for intento in range(max_reintentos):
        try:
            with open(archivo_audio, 'rb') as f:
                files = {
                    'audio': (archivo_audio.name, f, 'audio/wav'),
                    'text': (None, texto),
                    'model': (None, modelo)
                }

                response = requests.post(ENDPOINT, files=files, timeout=180)

                if response.status_code == 200:
                    resultado = response.json()
                    return {
                        'id_lectura': id_lectura,
                        'archivo': archivo_audio.name,
                        'modelo': modelo,
                        'evaluacion': resultado,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    # Mostramos la respuesta completa (no truncada) para
                    # poder diagnosticar el error real del backend.
                    print(f"  ✗ Error {response.status_code} para {id_lectura}:")
                    print(f"    {response.text}")
                    if intento < max_reintentos - 1:
                        print(f"    Reintentando ({intento + 1}/{max_reintentos})...")
                        time.sleep(2)

        except requests.exceptions.ConnectionError as e:
            print(f"  ✗ Conexión rechazada para {id_lectura}: ¿Backend activo?")
            if intento < max_reintentos - 1:
                print(f"    Reintentando en 3 segundos...")
                time.sleep(3)
        except Exception as e:
            print(f"  ✗ Error inesperado para {id_lectura}: {str(e)}")
            if intento < max_reintentos - 1:
                time.sleep(1)

    return None

# ============================================================================
# FLUJO PRINCIPAL
# ============================================================================

def ejecutar_evaluaciones():
    """Ejecuta el flujo completo de evaluación"""

    print("\n" + "="*70)
    print("GENERADOR DE EVALUACIONES MULTIMODELO")
    print(f"Modelos a ejecutar: {MODELOS}")
    print("="*70)

    # 1. Validar setup
    print("\n[1/5] Validando configuración...")
    if not DATOS_JSON.exists():
        print(f"✗ Error: No encontrado {DATOS_JSON}")
        return

    if not AUDIOS_DIR.exists():
        print(f"✗ Error: No encontrado {AUDIOS_DIR}")
        return

    datos_evaluacion = cargar_datos_evaluacion()
    print(f"✓ Cargados {len(datos_evaluacion)} registros de evaluación")

    # 2. Obtener audios
    print("\n[2/5] Escaneando audios...")
    audios_por_grado = obtener_audios_por_grado()
    total_audios = sum(len(audios) for audios in audios_por_grado.values())
    print(f"✓ Total de audios encontrados: {total_audios}")

    # 3. Crear estructura
    print("\n[3/5] Preparando directorios...")
    crear_estructura_directorios()

    # 4. Ejecutar evaluaciones
    print("\n[4/5] Iniciando evaluaciones...")
    total_audios_por_modelo = sum(len(a) for a in audios_por_grado.values())
    print(f"Configuración: {len(MODELOS)} modelo(s) × {total_audios_por_modelo} audios = {len(MODELOS) * total_audios_por_modelo} evaluaciones\n")

    resultados_por_modelo_grado = {
        modelo: {grado: [] for grado in range(1, 5)}
        for modelo in MODELOS
    }

    total_intentos = 0
    total_exitosos = 0

    for modelo in MODELOS:
        print(f"\n{'='*70}")
        print(f"MODELO: {modelo.upper()}")
        print(f"{'='*70}")

        for grado in range(1, 5):
            print(f"\n  Grado {grado}: {NOMBRE_GRADOS[grado]}")
            audios = audios_por_grado[grado]

            if not audios:
                print(f"    ⚠ Sin audios para procesar")
                continue

            for idx, archivo_audio in enumerate(audios, 1):
                total_intentos += 1
                id_lectura = extraer_id_lectura(archivo_audio.name)

                if id_lectura is None:
                    print(f"    ✗ [{idx}/{len(audios)}] No se pudo extraer ID de {archivo_audio.name}")
                    continue

                print(f"    ⏳ [{idx}/{len(audios)}] ID {id_lectura}...", end=" ")

                resultado = evaluar_audio(
                    archivo_audio,
                    TEXTOS_LECTURA[grado],
                    modelo,
                    id_lectura
                )

                if resultado:
                    resultados_por_modelo_grado[modelo][grado].append(resultado)
                    total_exitosos += 1
                    print("✓")
                else:
                    print("✗")

    # 5. Guardar resultados
    print("\n[5/5] Guardando resultados...")

    for modelo in MODELOS:
        for grado in range(1, 5):
            evaluaciones = resultados_por_modelo_grado[modelo][grado]

            nombre_grado = NOMBRE_GRADOS[grado]
            archivo_salida = SALIDA_DIR / modelo / f"{nombre_grado}.json"

            with open(archivo_salida, 'w', encoding='utf-8') as f:
                json.dump(evaluaciones, f, ensure_ascii=False, indent=2)

            print(f"✓ {modelo:15} > {nombre_grado:12}: {len(evaluaciones)} evaluaciones")

    # Resumen
    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)
    print(f"Total de intentos: {total_intentos}")
    print(f"Exitosos: {total_exitosos}")
    print(f"Tasa de éxito: {(total_exitosos/total_intentos*100):.1f}%" if total_intentos > 0 else "N/A")
    print(f"Salida: {SALIDA_DIR}")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        ejecutar_evaluaciones()
    except KeyboardInterrupt:
        print("\n✗ Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n✗ Error fatal: {str(e)}")
        import traceback
        traceback.print_exc()