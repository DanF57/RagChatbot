import os
import json
import re
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnablePassthrough

# Importaciones de Langchain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Cargar variables de entorno
load_dotenv(".env.local") 
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

app = FastAPI()

# Modelo de Embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

# Conexión a Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "vitalito"
index = pc.Index(index_name) 

# VECTOR STORE
namespace = "recetas-medicas"
vector_store = PineconeVectorStore(index=index, embedding=embeddings, namespace=namespace)

# Configurar el modelo de Gemini usando Langchain
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GOOGLE_API_KEY,
    streaming=True,
    temperature=0.3,
)

class ChatMessage(BaseModel):
    role: str
    content: str
    metadata: dict = {}

class Request(BaseModel):
    messages: List[dict]

def convert_messages_to_langchain(messages: List[dict]):
    """Convierte los mensajes al formato de Langchain."""
    langchain_messages = [SystemMessage(content=system_prompt)]

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
    return langchain_messages

system_prompt = """
Eres Vitalito, un asistente médico virtual amigable y profesional. Tu objetivo es ayudar a los usuarios con información médica clara y precisa.

Directrices para tu comportamiento:
- Usa un tono cordial y cercano, pero manteniendo la profesionalidad médica
- Evita decir frases como "basándome en la información proporcionada", "según la información", "según el contexto", o "según los documentos"
- Saluda solo cuando te saludan
- Mantén un tono empático y comprensivo

Reglas para tus respuestas:
- Responde ÚNICAMENTE preguntas relacionadas con medicina
- Para preguntas sobre conocimientos médicos generales (como "¿Qué es la diabetes?"), usa tu conocimiento base sin consultar la base de datos
- SOLO usa la información de la base de datos cuando:
  * Te pregunten por un paciente específico (por DNI o nombre)
  * Te pidan información sobre recetas médicas específicas
- Cuando realices explicaciones utiliza un lenguaje sencillo con ejemplos y analogías.
- Si te preguntan sobre temas no médicos, indica amablemente que solo puedes ayudar con temas de salud
"""

question_prompt = ChatPromptTemplate.from_template("""
Has recibido la siguiente pregunta: {question}

Si la pregunta es sobre un paciente específico o una receta médica específica, aquí está el contexto relevante de la base de datos:
{context}

Instrucciones para responder:
1. Si la pregunta es sobre conocimiento médico general (ejemplo: "¿Qué es la hipertensión?"), ignora el contexto proporcionado y responde usando tu conocimiento médico general.

2. Si la pregunta es sobre un paciente o receta específica:
   - Usa la información del contexto proporcionado
   - Solamente usa tu conocimiento para complementar la información (ejemplo: explicar un medicamento de la receta consultada)
   - Incluye detalles relevantes como diagnóstico, medicamentos, fecha de la cita o recomendaciones
   - Si no encuentras la información solicitada, indícalo claramente

3. Mantén un tono profesional pero amigable, como un asistente médico que se preocupa por ayudar.
Responde la pregunta siguiendo estas instrucciones:
""")

def extract_search_params(message: str) -> tuple[Optional[str], Optional[str], bool]:
    """Extrae DNI, nombre y determina si la consulta es específica."""
    message_lower = message.lower()
    dni = None
    nombre = None
    
    # Buscar DNI
    dni_match = re.search(r'\b\d{8}\b', message)
    if dni_match:
        dni = dni_match.group(0)
    
    # Buscar nombre
    nombre_matches = re.findall(r'(?:paciente|del|de|para)\s+([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+?)(?:\s+con|\s+tiene|\s+es|\s*\?|$)', message)
    if nombre_matches:
        nombre = nombre_matches[0].strip()
    
    # Determinar si es una consulta específica
    specific_keywords = [
        'receta', 'paciente', 'cita', 'tratamiento', 'dni', 
        'diagnóstico', 'medicamento', 'próxima', 'dosis'
    ]
    is_specific_query = any(keyword in message_lower for keyword in specific_keywords) or dni or nombre
    
    return dni, nombre, is_specific_query

def format_context(docs):
    """Formatea los documentos en un string legible."""
    if not docs:
        return "No hay información específica disponible en la base de datos."
    context_texts = []
    for doc in docs:
        if hasattr(doc, 'page_content'):
            context_texts.append(doc.page_content)
        elif isinstance(doc, dict) and 'metadata' in doc:
            context_texts.append(str(doc['metadata']))
    return "\n".join(context_texts)

def stream_text(messages: List[dict]):
    try:
        chat_history = convert_messages_to_langchain(messages)
        user_message = messages[-1].get("content", "")

        # Extraer parámetros y determinar tipo de consulta
        dni, nombre, is_specific_query = extract_search_params(user_message)
        
        # Configurar retriever
        retriever = vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 6, "score_threshold": 0.6},
        )

        # Crear chain que maneja tanto consultas específicas como generales
        def get_context(query):
            if is_specific_query:
                search_kwargs = {"k": 6, "score_threshold": 0.6}
                if dni or nombre:
                    filter_dict = {}
                    if dni:
                        filter_dict["dni"] = dni
                    if nombre:
                        filter_dict["paciente_nombre"] = nombre
                    search_kwargs["filter"] = filter_dict
                docs = retriever.invoke(query)
                return format_context(docs)
            return "Esta es una consulta general. Usa tu conocimiento médico para responder."

        chain = (
            {"context": lambda x: get_context(x), "question": RunnablePassthrough()}
            | question_prompt
            | llm
            | StrOutputParser()
        )

        # Generar stream de respuesta
        for chunk in chain.stream(user_message):
            yield "0:{text}\n".format(text=json.dumps(chunk))

        yield 'e:{{"finishReason":"stop","usage":{{"promptTokens":0,"completionTokens":0}},"isContinued":false}}\n'

    except Exception as e:
        import traceback
        print(f"Error en stream_text: {str(e)}")
        print(traceback.format_exc())
        yield "0:{text}\n".format(text=json.dumps(f"Error interno: {str(e)}"))

@app.post("/api/chat")
async def handle_chat_data(request: Request, protocol: str = Query("data")):
    try:
        messages = request.messages
        response = StreamingResponse(stream_text(messages))
        response.headers["x-vercel-ai-data-stream"] = "v1"
        return response
    except Exception as e:
        import traceback
        print(f"Error en handle_chat_data: {str(e)}")
        print(traceback.format_exc())
        return {"error": str(e), "traceback": traceback.format_exc()}