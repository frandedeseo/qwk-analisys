import csv
import json

# Leer CSV
with open(r"c:\Users\frand\Downloads\Evaluación realizada por expertos(Hoja1).csv", 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=';')
    lines = list(reader)

# Headers: fila 3 (índice 2), solo primeras 7 columnas
headers = [h.strip() for h in lines[2][:7]]

# Procesar datos desde fila 4 (índice 3)
data = []
for row in lines[3:]:
    if not any(row) or not row[0].strip():  # Saltar vacías
        continue
    
    record = {}
    for i, header in enumerate(headers):
        val = row[i].strip() if i < len(row) else ""
        # Intentar conversión a número
        if val:
            try:
                record[header] = float(val) if '.' in val else int(val)
            except:
                record[header] = val
        else:
            record[header] = None
    data.append(record)

# Guardar JSON
with open(r"c:\Users\frand\Downloads\datos_lectura.json", 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✓ Conversion exitosa")
print(f"✓ Total de registros: {len(data)}")
print(f"✓ Headers: {headers}")
print(f"✓ JSON guardado en: c:\\Users\\frand\\Downloads\\datos_lectura.json")
