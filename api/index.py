from io import BytesIO
import os
from PIL import Image
from dotenv import load_dotenv
from typing import List, Dict
import json
import re

# De utils
from .utils.prompt import prompt_rag
from .utils.prompt import prompt_basic

# FastAPI
from pydantic import BaseModel
from fastapi import FastAPI, File, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

# LangChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

import google.generativeai as genai

# Cargar variables de entorno
load_dotenv(".env.local")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

class Request(BaseModel):
    messages: List[dict]

app = FastAPI()

# Configurar embeddings y conexión a Pinecone
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "vitalito"
index = pc.Index(index_name)
namespace = "recetas-medicas"
vector_store = PineconeVectorStore(index=index, embedding=embeddings, namespace=namespace)

# Configurar el modelo LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GOOGLE_API_KEY,
    streaming=True,
    temperature=0.3,
)

# Función para consultar recetas médicas por DNI
def query_recetas(question: str) -> str:
    """
    Consulta las recetas médicas asociadas a un DNI específico.

    Args:
        dni (str): El DNI del paciente.

    Returns:
        str: Las recetas encontradas o un mensaje indicando que no hay resultados.
    """
    # Expresión regular para buscar un número de 10 dígitos
    dni_match = re.search(r"\b\d{10}\b", question)

    # Verificar si se encontró un match y extraerlo
    dni = dni_match.group() if dni_match else None
    # Configurar el recuperador con un filtro específico para el campo DNI
    retriever = vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": 3,
            "score_threshold": 0.5,
            "filter": {"dni": dni},  # Filtrar por el campo DNI
        },
    )

    # Generar contexto basado únicamente en metadatos
    docs = retriever.invoke(question)
    context_items = [
        ", ".join(f"{key}: {value}" for key, value in doc.metadata.items())
        for doc in docs
    ]
    return "\n\n".join(context_items)



# Generar respuesta RAG (con conocimiento general o recetas)
def stream_rag_response(messages: List[dict]):
    question = messages[-1]['content']

    def format_messages(messages):
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
    
    messages.append({"role": "user", "content": question})
    # Detectar si la pregunta es sobre recetas
    
    if (re.search(r"\b\d{10}\b", question)):
        print("CAMINO A")
        context = query_recetas(question)
        input_data = {"context": context, "conversation": format_messages(messages)}
        prompt = ChatPromptTemplate.from_template(prompt_rag).format_prompt(**input_data)
    else:
        print("CAMINO B")
        context = str("Usa tu conocimiento general para responder")
        input_data = {"context": context, "conversation": format_messages(messages)}
        prompt = ChatPromptTemplate.from_template(prompt_basic).format_prompt(**input_data)
    
    prompt_messages = prompt.to_messages()

    # Generar el stream desde el LLM
    result_stream = llm.stream(prompt_messages)

    for chunk in result_stream:
        yield "0:{text}\n".format(text=json.dumps(chunk.content))

    yield 'e:{{"finishReason":"stop","usage":{{"promptTokens":0,"completionTokens":0}},"isContinued":false}}\n'


# API
@app.post("/api/chat")
async def handle_chat_data(request: Request, protocol: str = Query('data')):
    try:
        messages = request.messages
        response = StreamingResponse(stream_rag_response(messages))
        response.headers["x-vercel-ai-data-stream"] = "v1"
        return response
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

UPLOAD_DIR = "uploads"
from PIL import Image

@app.post("/api/chat/upload-image")
async def upload_image(image: UploadFile = File(...)):
    try:
        # Leer los bytes de la imagen en memoria
        image_bytes = await image.read()
        image_stream = BytesIO(image_bytes)

        genai.configure(api_key="AIzaSyBrSiKIktaufCWN6HqMukW94ymiw8Nbm8E")

        # Abrir la imagen usando PIL
        organ = Image.open(image_stream)

        # Crear el modelo de Gemini
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Generar contenido basado en la imagen y un texto de ejemplo
        response = model.generate_content(["Dime infomación importante sobre esta receta, no olvides que debes responder en español", organ])

        # Retornar la respuesta del modelo
        return {"response": response.text}

    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
