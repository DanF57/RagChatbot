import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
import csv

# Cargar variables de entorno
load_dotenv("../.env.local") 
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Modelo de Embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

# Conexión a Pinecone
pinecone_api_key = PINECONE_API_KEY
pc = Pinecone(api_key=pinecone_api_key) 
index_name = "vitalito"  
existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
index = pc.Index(index_name)

# VECTOR STORE
namespace = "recetas=medicas"
vector_store = PineconeVectorStore(index=index, embedding=embeddings, namespace=namespace)

def populate_pinecone_from_csv(csv_file):
    # Leer el archivo CSV e insertar datos en Pinecone
    with open(csv_file, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Extraer y limpiar datos
            receta = row.get("RECETA", "").strip()
            dni = row.get("DNI", "").strip()
            fecha = row.get("FECHA", "").strip()
            proxima_cita = row.get("PRÓXIMA CITA", "").strip()
            paciente_nombre = row.get("PACIENTE", "").strip()
            paciente_edad = row.get("EDAD", "").strip()
            diagnostico = row.get("DIAGNÓSTICO", "").strip()
            descripcion = row.get("DESCRIPCIÓN", "").strip()
            cant = row.get("CANT", "").strip()
            indicaciones = row.get("INDICACIONES", "").strip()
            alergias = row.get("ALERGIAS", "").strip()
            recomendaciones = row.get("RECOMENDACIONES", "").strip()

            # Reemplazar valores nulos por un texto genérico o vacío
            receta = receta or "Sin receta"
            dni = dni or "Sin DNI"
            fecha = fecha or "Sin fecha"
            proxima_cita = proxima_cita or "Sin próxima cita"
            paciente_nombre = paciente_nombre or "Desconocido"
            paciente_edad = paciente_edad or "Sin edad"
            diagnostico = diagnostico or "Sin diagnóstico"
            descripcion = descripcion or "Sin descripción"
            cant = cant or "Sin cantidad"
            indicaciones = indicaciones or "Sin indicaciones"
            alergias = alergias or "Sin información de alergias"
            recomendaciones = recomendaciones or "Sin recomendaciones"

            # Concatenar textos relevantes para generar embeddings
            text_to_embed = f"{diagnostico} {descripcion}"
            
            # Generar embeddings usando embed_query
            try:
                embedding = embeddings.embed_query(text_to_embed)
            except Exception as e:
                print(f"Error al generar embeddings para {receta}: {e}")
                continue

            # Metadata adicional con todos los campos
            metadata = {
                "text": text_to_embed,
                "dni": dni,
                "fecha": fecha,
                "proxima_cita": proxima_cita,
                "paciente_nombre": paciente_nombre,
                "paciente_edad": paciente_edad,
                "diagnostico": diagnostico,
                "descripcion": descripcion,
                "cant": cant,
                "indicaciones": indicaciones,
                "alergias": alergias,
                "recomendaciones": recomendaciones,
            }

            # Insertar en Pinecone
            try:
                index.upsert([(receta, embedding, metadata)], namespace="recetas-medicas")
            except Exception as e:
                print(f"Error al insertar receta {receta} en Pinecone: {e}")

    print("Datos insertados con éxito en Pinecone.")


# Poblar Pinecone desde un archivo CSV
if __name__ == "__main__":
    # Poblar el índice desde el CSV
    populate_pinecone_from_csv("output.csv")

