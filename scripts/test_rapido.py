"""
Prueba rápida de UN solo audio contra el backend, antes de lanzar
el lote completo de 96 evaluaciones.

Muestra la respuesta completa (sin truncar) para poder ver el error
real si algo falla.

Uso:
    python test_rapido.py <ruta_audio.wav> <modelo> [grado]

Ejemplo:
    python test_rapido.py "audios-para-evaluar/1er grado/lectura_52866_2025-10-29_13-42-40.wav" openai-audio 1

Modelos válidos: gemini-flash, gemini-pro, openai-audio
"""

import sys
import json
from pathlib import Path
import requests

BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/evaluar-lectura"

MODELOS_VALIDOS = ["gemini-flash", "gemini-pro", "openai-audio"]

TEXTOS_LECTURA = {
    1: "Los perros tienen muy buen olfato y oído. Es un animal inteligente y fiel. Es el mejor amigo del hombre.",
    2: "En el sistema solar hay ocho planetas. Marte es el cuarto planeta más cercano al sol. Es el segundo más pequeño. Su color es rojizo. Desde la Tierra se lo puede observar con un telescopio. Hace varios años los científicos investigan si hubo vida en ese planeta.",
    3: "Los dinosaurios son animales que vivieron en la tierra hace muchos años. Eran animales salvajes, muy feroces y peligrosos. El Tiranosaurio Rex era uno de los dinosaurios más conocidos. Era un animal de gran tamaño. Tenía dientes muy filosos y grandes garras para atrapar a sus presas.",
    4: "El búho es un ave de comportamiento nocturno. Por lo tanto, al haber escasez de luz, intercepta a sus presas a través del sonido. Es famoso y conocido por permanecer despierto durante la noche y descansar de día. A diferencia de las lechuzas, los búhos poseen plumas sobre su cabeza que son confundidas con orejas. La lechuza no posee estas plumas."
}


def chequear_backend_activo() -> bool:
    try:
        requests.get(BASE_URL, timeout=5)
        print(f"✓ El backend responde en {BASE_URL}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"✗ No se pudo conectar a {BASE_URL}")
        print("  ¿Está corriendo el servidor? (ej. uvicorn main:app --reload)")
        return False
    except requests.exceptions.RequestException:
        # El backend respondió algo (ej. 404 en "/"), igual está vivo
        print(f"✓ El backend responde en {BASE_URL}")
        return True


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    audio_path = Path(sys.argv[1])
    modelo = sys.argv[2]
    grado = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    if modelo not in MODELOS_VALIDOS:
        print(f"✗ Modelo inválido: '{modelo}'. Usá uno de: {MODELOS_VALIDOS}")
        sys.exit(1)

    if grado not in TEXTOS_LECTURA:
        print(f"✗ Grado inválido: {grado}. Usá 1, 2, 3 o 4.")
        sys.exit(1)

    if not audio_path.exists():
        print(f"✗ No existe el archivo: {audio_path}")
        sys.exit(1)

    texto = TEXTOS_LECTURA[grado]

    print("\n" + "=" * 70)
    print("PRUEBA RÁPIDA DE EVALUACIÓN")
    print("=" * 70)

    if not chequear_backend_activo():
        sys.exit(1)

    print(f"\nAudio:  {audio_path.name}")
    print(f"Modelo: {modelo}")
    print(f"Grado:  {grado}")
    print(f"Texto:  {texto[:70]}...")
    print("\nEnviando request al backend (puede tardar unos segundos)...\n")

    with open(audio_path, "rb") as f:
        files = {
            "audio": (audio_path.name, f, "audio/wav"),
            "text": (None, texto),
            "model": (None, modelo),
        }
        try:
            response = requests.post(ENDPOINT, files=files, timeout=60)
        except requests.exceptions.ConnectionError:
            print("✗ Conexión rechazada a mitad del request.")
            sys.exit(1)
        except requests.exceptions.Timeout:
            print("✗ Timeout (>60s). El modelo puede estar tardando demasiado.")
            sys.exit(1)

    print(f"Status code: {response.status_code}")
    print("-" * 70)

    if response.status_code == 200:
        try:
            data = response.json()
            print(json.dumps(data, ensure_ascii=False, indent=2))
            print("-" * 70)
            print("✓ Evaluación exitosa — la respuesta es JSON válido")
        except json.JSONDecodeError:
            print(response.text)
            print("-" * 70)
            print("⚠ El backend devolvió 200 pero el body no es JSON válido")
    else:
        # Mostramos TODO el body, sin truncar, para ver el traceback real
        print(response.text)
        print("-" * 70)
        print(f"✗ Error {response.status_code}")
        print("\nTip: si acá no ves detalle suficiente, mirá la terminal donde")
        print("corre 'uvicorn' — ahí aparece el traceback completo de Python")
        print("del lado del backend (la excepción real que tiró la estrategia).")


if __name__ == "__main__":
    main()