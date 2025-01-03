import sqlite3
import csv

def create_database():
    # Conexión a la base de datos SQLite
    conn = sqlite3.connect("database.db")

    # Crear la tabla de recetas médicas
    conn.execute("""
    CREATE TABLE IF NOT EXISTS recetas (
        receta TEXT PRIMARY KEY, 
        dni TEXT,
        fecha TEXT,
        proxima_cita TEXT,
        paciente_nombre TEXT,
        paciente_edad TEXT,
        diagnostico TEXT,
        descripcion TEXT,
        cant TEXT,
        indicaciones TEXT,
        alergias TEXT,
        recomendaciones TEXT
    );
    """)

    print("Base de datos y tabla creadas con éxito.")
    conn.close()


def populate_database_from_csv(csv_file):
    # Conexión a la base de datos SQLite
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Leer el archivo CSV e insertar datos en la tabla
    with open(csv_file, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            
            # Renombrar las claves del diccionario para que coincidan con los nombres en la base de datos
            row = { 
                'dni': row.get('DNI'), #dni de paciente
                'fecha': row.get('FECHA'), #fecha y hora de generación de la receta
                'receta': row.get('RECETA'), #código único de la receta
                'proxima_cita': row.get('PRÓXIMA CITA'), #fecha de próxima cita
                'paciente_nombre': row.get('PACIENTE'), #nombre del paciente
                'paciente_edad': row.get('EDAD'), #edad del paciente
                'diagnostico': row.get('DIAGNÓSTICO'), #diagnostico 
                'descripcion': row.get('DESCRIPCIÓN'), #lista de medicamentos a tomar
                'cant': row.get('CANT'), #cantidades
                'indicaciones': row.get('INDICACIONES'), #indicaciones de como tomar los medicamentos incluye precauciones
                'alergias': row.get('ALERGIAS'), #si posee o no alergias 
                'recomendaciones': row.get('RECOMENDACIONES')
            }

            # Reemplazar valores vacíos por None (NULL en SQLite)
            for key in row:
                if row[key] == "":
                    row[key] = None

            # Asumir que la columna "RECETA" del CSV contiene el código único de receta
            # Limpiar espacios extra y verificar que la columna 'receta' no esté vacía
            receta_code = row.get('RECETA', '').strip()

            # Asegurarse de que el código de receta no esté vacío
            if receta_code is None:
                print(f"Error: falta el código de receta en la fila {row}")
                continue

            try:
                cursor.execute("""
                INSERT INTO recetas (receta, dni, fecha, proxima_cita, paciente_nombre, paciente_edad, diagnostico, descripcion, cant, indicaciones, alergias, recomendaciones)
                VALUES (:receta, :dni, :fecha, :proxima_cita, :paciente_nombre, :paciente_edad, :diagnostico, :descripcion, :cant, :indicaciones, :alergias, :recomendaciones)
                """, row)
            except sqlite3.IntegrityError as e:
                print(f"Error al insertar fila: {row}. Error: {e}")

    conn.commit()
    print("Datos insertados con éxito desde el archivo CSV.")
    conn.close()

# Crear la base de datos y la tabla
if __name__ == "__main__":
    create_database()
    # Poblar la base de datos desde un archivo CSV (reemplaza 'recetas.csv' con la ruta de tu archivo)
    populate_database_from_csv("output.csv")