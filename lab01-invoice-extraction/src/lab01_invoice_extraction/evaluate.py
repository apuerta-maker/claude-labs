"""Evalúa la extracción sobre todo el dataset, campo por campo."""

import json
import sys

import anthropic
from dotenv import load_dotenv

import re
from collections import defaultdict

from lab01_invoice_extraction.extract import LAB_DIR, PDF_DIR, extract_invoice
from lab01_invoice_extraction.extract import GROUND_TRUTH_DIR, LAB_DIR, PDF_DIR, extract_invoice
from lab01_invoice_extraction.schema import Invoice

EXTRACTIONS_DIR = LAB_DIR / "data" / "extractions"
TOLERANCE = 0.01  # un céntimo
MISSING = "<ausente>"

def run_extractions(force: bool) -> None:
    """Extrae todas las facturas y guarda cada resultado (con sus tokens) en disco."""
    client = anthropic.Anthropic()
    EXTRACTIONS_DIR.mkdir(parents=True, exist_ok=True)

    for pdf_path in sorted(PDF_DIR.glob("invoice_*.pdf")):
        out_path = EXTRACTIONS_DIR / f"{pdf_path.stem}.json"

        # Caché: si ya existe y no se pide --force, no se vuelve a pagar la llamada
        if out_path.exists() and not force:
            print(f"{pdf_path.stem}: ya extraída, se reutiliza")
            continue

        try:
            invoice, response = extract_invoice(client, pdf_path)
        except Exception as error:
            # Un fallo no detiene el lote: se informa y se sigue con la siguiente
            print(f"{pdf_path.stem}: ERROR -> {error}")
            continue

        record = {
            "invoice": invoice.model_dump(mode="json"),
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }
        out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        print(
            f"{pdf_path.stem}: extraída "
            f"({response.usage.input_tokens} in / {response.usage.output_tokens} out)"
        )

def flatten(invoice: Invoice) -> dict:
    """Convierte la factura en un diccionario plano: 'issuer.name', 'line_items[0].quantity'..."""
    flat = {}

    def walk(prefix, value):
        if isinstance(value, dict):
            for key, item in value.items():
                walk(f"{prefix}.{key}" if prefix else key, item)
        elif isinstance(value, list):
            flat[f"{prefix}.count"] = len(value)  # el número de líneas también se evalúa
            for i, item in enumerate(value):
                walk(f"{prefix}[{i}]", item)
        else:
            flat[prefix] = value

    walk("", invoice.model_dump())
    return flat


def normalize_text(text: str) -> str:
    """Ignora diferencias de espacios; mayúsculas, tildes y puntuación sí cuentan."""
    return " ".join(text.split())


def values_match(expected, actual) -> bool:
    """Reglas de comparación: tolerancia en importes, espacios normalizados en textos."""
    if expected is None or actual is None:
        return expected is actual  # null solo coincide con null
    if isinstance(expected, float):
        return isinstance(actual, (int, float)) and abs(expected - actual) <= TOLERANCE
    if isinstance(expected, str) and isinstance(actual, str):
        return normalize_text(expected) == normalize_text(actual)
    return expected == actual  # fechas, número de líneas...


def compare_invoice(name: str) -> list:
    """Compara una extracción con su ground truth. Devuelve (campo, esperado, extraído, acierto)."""
    truth = flatten(Invoice.model_validate_json(
        (GROUND_TRUTH_DIR / f"{name}.json").read_text(encoding="utf-8")
    ))

    record_path = EXTRACTIONS_DIR / f"{name}.json"
    if record_path.exists():
        record = json.loads(record_path.read_text(encoding="utf-8"))
        predicted = flatten(Invoice.model_validate(record["invoice"]))
    else:
        predicted = {}  # extracción fallida: todos los campos contarán como error

    results = []
    for key in sorted(truth.keys() | predicted.keys()):
        expected = truth.get(key, MISSING)
        actual = predicted.get(key, MISSING)
        results.append((key, expected, actual, values_match(expected, actual)))
    return results

def evaluate() -> None:
    """Puntúa todas las facturas e imprime el informe completo."""
    field_stats = defaultdict(lambda: [0, 0])  # campo genérico -> [aciertos, total]
    errors = []
    perfect = 0
    tokens_in, tokens_out = [], []

    names = sorted(path.stem for path in GROUND_TRUTH_DIR.glob("invoice_*.json"))
    for name in names:
        results = compare_invoice(name)

        for key, expected, actual, ok in results:
            # 'line_items[2].unit_price' -> 'line_items[].unit_price': agrupa todas las líneas
            generic = re.sub(r"\[\d+\]", "[]", key)
            field_stats[generic][1] += 1
            if ok:
                field_stats[generic][0] += 1
            else:
                errors.append((name, key, expected, actual))

        if all(result[3] for result in results):
            perfect += 1

        record_path = EXTRACTIONS_DIR / f"{name}.json"
        if record_path.exists():
            usage = json.loads(record_path.read_text(encoding="utf-8"))["usage"]
            tokens_in.append(usage["input_tokens"])
            tokens_out.append(usage["output_tokens"])

    # 1. Precisión por campo, de peor a mejor
    print("\n=== Precisión por campo (de peor a mejor) ===")
    for field, (ok, total) in sorted(field_stats.items(), key=lambda item: item[1][0] / item[1][1]):
        print(f"{ok / total:7.1%}  {ok:>3}/{total:<3}  {field}")

    # 2. Resumen global
    total_ok = sum(ok for ok, _ in field_stats.values())
    total = sum(count for _, count in field_stats.values())
    print("\n=== Resumen ===")
    print(f"Campos correctos:   {total_ok}/{total} ({total_ok / total:.1%})")
    print(f"Facturas perfectas: {perfect}/{len(names)}")
    if tokens_in:
        print(f"Tokens de entrada por factura: media {sum(tokens_in) / len(tokens_in):.0f}, "
              f"mín {min(tokens_in)}, máx {max(tokens_in)}")
        print(f"Tokens de salida por factura:  media {sum(tokens_out) / len(tokens_out):.0f}, "
              f"mín {min(tokens_out)}, máx {max(tokens_out)}")

    # 3. Errores concretos
    if errors:
        print(f"\n=== Errores ({len(errors)}) ===")
        for name, key, expected, actual in errors:
            print(f"{name} · {key}\n    esperado: {expected!r}\n    extraído: {actual!r}")
    else:
        print("\nSin errores.")

def main() -> None:
    load_dotenv()
    run_extractions(force="--force" in sys.argv)
    evaluate()

    # --- Prueba temporal del paso 2 ---
    print("\nPruebas de las reglas de comparación:")
    print(values_match(4357.2, 4357.205), "<- diferencia de medio céntimo")
    print(values_match(4357.2, 4357.22), "<- diferencia de 2 céntimos")
    print(values_match("Calle  Mayor 1", "Calle Mayor 1"), "<- espacio doble")
    print(values_match("Cáceres", "Caceres"), "<- tilde omitida")
    print(values_match(None, None), "<- ambos nulos")
    print(values_match(None, 0.0), "<- nulo frente a cero")

    print("\nComparación de invoice_003:")
    for key, expected, actual, ok in compare_invoice("invoice_003"):
        print(f"{'✓' if ok else '✗'}  {key}: {actual!r}")

if __name__ == "__main__":
    main()