"""Ejercicio exploratorio: enviar un PDF de factura a Claude y ver qué entiende."""

import base64
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

LAB_DIR = Path(__file__).resolve().parents[2]
PDF_DIR = LAB_DIR / "data" / "pdfs"
MODEL = "claude-sonnet-5-5"


def main() -> None:
    load_dotenv()

    # Permite elegir la factura desde la línea de comandos; por defecto, la 003
    pdf_name = sys.argv[1] if len(sys.argv) > 1 else "invoice_003.pdf"
    pdf_bytes = (PDF_DIR / pdf_name).read_bytes()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Describe brevemente esta factura: quién la emite, "
                        "a quién va dirigida, qué conceptos incluye y el total a pagar.",
                    },
                ],
            }
        ],
    )

    print(f"Factura: {pdf_name}\n")
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


if __name__ == "__main__":
    main()