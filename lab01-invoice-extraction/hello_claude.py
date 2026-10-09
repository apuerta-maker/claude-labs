from dotenv import load_dotenv
import anthropic

load_dotenv()  # busca por archivo.env empezando aquí y yendo a la root

client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY desde el .env

response = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=300,
    messages=[
        {
            "role": "user",
            "content": "En dos frases: ¿qué campos clave debe tener una factura española?",
        }
    ],
)

num_bloques = len(response.content)
print(str(num_bloques)+" Bloques recibidos:", [block.type for block in response.content]) #Primero imprime los tipos de bloque recibidos, para ver la estructura real de la respuesta. Esperamos algo como ['thinking', 'text'].

for block in response.content: #Después recorre los bloques y trata cada uno según su type
    if block.type == "thinking":
        print("\n[Razonamiento de Claude (primeros 800 caracteres)]")
        print(block.thinking[:800])
    elif block.type == "text":
        print("\n[Respuesta]")
        print(block.text)
        
print("\n--- Metadata ---")
print("🧠Model:", response.model)
print("🛑stop_reason:", response.stop_reason)
print("📥Input tokens:", response.usage.input_tokens)
print("📤Output tokens:", response.usage.output_tokens)