"""Extrae datos estructurados de una factura PDF con salidas estructuradas."""

import base64
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from lab01_invoice_extraction.schema import Invoice

LAB_DIR = Path(__file__).resolve().parents[2]
PDF_DIR = LAB_DIR / "data" / "pdfs"
GROUND_TRUTH_DIR = LAB_DIR / "data" / "ground_truth"
MODEL = "claude-sonnet-5-5"

SYSTEM_PROMPT = (
    "Eres un sistema de extracción de datos de facturas españolas. "
    "Copia los textos (nombres, NIF, direcciones, conceptos) exactamente como aparecen "
    "impresos, sin corregirlos, completarlos ni reformatearlos. "
    "Convierte los importes a números (4.357,20 € -> 4357.2) "
    "y las fechas a formato ISO (15/03/2026 -> 2026-03-15). "
    "Si un dato opcional no aparece en la factura, devuélvelo como null."
)


def load_pdf_b64(path: Path) -> str:
    return base64.standard_b64encode(path.read_bytes()).decode("utf-8")


def extract_invoice_bytes(client: anthropic.Anthropic, pdf_bytes: bytes):
    """Envía los bytes de un PDF a Claude y devuelve la factura validada y la respuesta completa."""
    response = client.messages.parse(
        model=MODEL,
        max_tokens=2000,
        thinking={"type": "between_tools"},  # sin razonamiento previo: más barato y rápido
        system=SYSTEM_PROMPT,
        output_format=Invoice,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": base64.standard_b64encode(pdf_bytes).decode("utf-8"),
                        },
                    },
                    {"type": "text", "text": "Extrae los datos de esta factura."},
                ],
            }
        ],
    )

    # La salida solo está garantizada si Claude terminó de forma normal
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"Extracción incompleta: stop_reason={response.stop_reason}")

    return response.parsed_output, response


def extract_invoice(client: anthropic.Anthropic, pdf_path: Path):
    """Lee el PDF del disco y delega en extract_invoice_bytes."""
    return extract_invoice_bytes(client, pdf_path.read_bytes())


def main() -> None:
    load_dotenv()
    name = sys.argv[1] if len(sys.argv) > 1 else "invoice_003"

    client = anthropic.Anthropic()
    invoice, response = extract_invoice(client, PDF_DIR / f"{name}.pdf")

    print(invoice.model_dump_json(indent=2))

    truth = Invoice.model_validate_json(
        (GROUND_TRUTH_DIR / f"{name}.json").read_text(encoding="utf-8")
    )
    print("\n¿Coincide exactamente con el ground truth?", invoice == truth)

    print("\n--- Metadata ---")
    print("🧠Model:", response.model)
    print("🛑stop_reason:", response.stop_reason)
    print("📥Input tokens:", response.usage.input_tokens)
    print("📤Output tokens:", response.usage.output_tokens)
    

if __name__ == "__main__":
    main()
