import csv
import json
import os

# Ruta del archivo CSV
csv_file = r"c:\Users\frand\Downloads\Evaluación realizada por expertos(Hoja1).csv"
output_file = csv_file.replace('.csv', '.json')

# Leer el archivo CSV manualmente
with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=';')
    lines = list(reader)

# La fila 3 (índice 2) contiene todos los headers
# Pero solo usamos las primeras 7 columnas (los datos reales, sin la rúbrica)
all_headers = [h.strip() for h in lines[2]]
headers = all_headers[:7]  # Solo las 7 primeras columnas
print(f"Headers utilizados: {headers}")

# Parsear los datos desde la fila 4 (índice 3) en adelante
# Pero solo tomar las primeras 7 columnas (ignorar la rúbrica)
data = []
for row in lines[3:]:
    # Saltar filas completamente vacías
    if not any(row):
        continue
    
    # Tomar solo las primeras 7 columnas (los datos reales, sin la rúbrica)
    row_data = row[:7]
    
    # Si la primera columna (ID LECTURA) está vacía, saltar esta fila
    if not row_data[0].strip():
        continue
    
    # Crear un diccionario con los datos
    record = {}
    for j, header in enumerate(headers):
        if j < len(row_data):
            value = row_data[j].strip()
            # Intentar convertir a número si es posible
            if value:
                try:
                    # Intentar como float
                    if '.' in value:
                        record[header] = float(value)
                    else:
                        record[header] = int(value)
                except ValueError:
                    record[header] = value
            else:
                record[header] = None
        else:
            record[header] = None
    
    data.append(record)

# Guardar el JSON
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✓ Conversión completada exitosamente!")
print(f"✓ Archivo JSON guardado en: {output_file}")
print(f"✓ Total de registros: {len(data)}")
print(f"✓ Primeros 3 registros como ejemplo:")
for i, record in enumerate(data[:3]):
    print(f"\n  Registro {i+1}: {record}")
