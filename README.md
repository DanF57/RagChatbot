# Chatbot Médico para Inteligecia Artifical
## Séptimo Ciclo de Ciencias de la Computación

### Integrantes:
- Daniel Flores
- Jean Panamito
- Mateo Martínez

## Cómo utilizar

Clonar el repositorio con `git clone`

Para ejecutarlo localmente se necesita:

1. Crear el archivo de variables de entorno `.env.local` y colocar el API Key en la variable: `GEMINI_API_KEY=****`
2. Tener node.js y python instalados
3. Tener instalado el manejador de paquetes `pnpm`, si no se lo tiene usa el comando `npm install -g pnpm` 
4. `pnpm install` Para instalar las dependencias de Node.
5. `python -m venv venv` para crear el entorno virtual.
7. `venv\Scripts\activate` para activar el entorno virtual.
8. `pip install -r requirements.txt` para instalar las librerías necesarias de python.
9. `pnpm dev` para ejecutar el servidor de desarrollo.
10. Por defecto se ejecutará en [LocalHost:300](http://localhost:3000/)
