"""Genera facturas españolas sintéticas con datos de referencia (ground truth)."""

import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

from lab01_invoice_extraction.schema import Invoice, LineItem, Party

SEED = 42
NUM_INVOICES = 10
# parents[2] sube de src/lab01_invoice_extraction/ a la carpeta del lab
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "ground_truth"

VAT_RATES = [21.0, 10.0, 4.0]
VAT_WEIGHTS = [0.7, 0.2, 0.1]  # el 21 % es el tipo más habitual
IRPF_RATE = 15.0

# (concepto, precio mínimo, precio máximo)
SERVICES = [
    ("Consultoría de procesos (horas)", 60, 120),
    ("Desarrollo de automatización (horas)", 50, 90),
    ("Formación en IA generativa", 400, 1200),
    ("Licencia de software anual", 200, 2500),
    ("Soporte técnico mensual", 150, 600),
    ("Material de oficina", 5, 60),
    ("Servicio de catering (por persona)", 10, 35),
]


def one_line(address: str) -> str:
    """Faker devuelve direcciones en varias líneas; las unimos en una, sin espacios sobrantes."""
    return ", ".join(part.strip() for part in address.split("\n"))


def make_party(fake: Faker, freelancer: bool) -> Party:
    """Crea un autónomo (persona con NIF) o una empresa (con CIF)."""
    if freelancer:
        return Party(name=fake.name(), tax_id=fake.nif(), address=one_line(fake.address()))
    return Party(name=fake.company(), tax_id=fake.cif(), address=one_line(fake.address()))


def make_invoice(fake: Faker, rng: random.Random, index: int) -> Invoice:
    # Un 40 % de las facturas las emite un autónomo, que aplica retención de IRPF
    freelancer = rng.random() < 0.4
    issuer = make_party(fake, freelancer=freelancer)
    recipient = make_party(fake, freelancer=False)

    line_items = []
    for _ in range(rng.randint(1, 5)):
        concept, low, high = rng.choice(SERVICES)
        line_items.append(
            LineItem(
                description=concept,
                quantity=float(rng.randint(1, 10)),
                unit_price=round(rng.uniform(low, high), 2),
                vat_rate=rng.choices(VAT_RATES, weights=VAT_WEIGHTS)[0],
            )
        )

    # Los importes se CALCULAN a partir de las líneas: siempre son coherentes
    tax_base = round(sum(li.quantity * li.unit_price for li in line_items), 2)
    vat_amount = round(
        sum(li.quantity * li.unit_price * li.vat_rate / 100 for li in line_items), 2
    )
    irpf_amount = round(tax_base * IRPF_RATE / 100, 2) if freelancer else None
    total = round(tax_base + vat_amount - (irpf_amount or 0), 2)

    issue_date = date(2026, 1, 1) + timedelta(days=rng.randint(0, 250))

    return Invoice(
        invoice_number=f"{issue_date.year}-{rng.choice('ABC')}-{index:04d}",
        issue_date=issue_date,
        issuer=issuer,
        recipient=recipient,
        line_items=line_items,
        tax_base=tax_base,
        vat_amount=vat_amount,
        irpf_amount=irpf_amount,
        total=total,
    )


def main() -> None:
    Faker.seed(SEED)
    fake = Faker("es_ES")
    rng = random.Random(SEED)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for i in range(1, NUM_INVOICES + 1):
        invoice = make_invoice(fake, rng, i)
        path = OUTPUT_DIR / f"invoice_{i:03d}.json"
        path.write_text(invoice.model_dump_json(indent=2), encoding="utf-8")
        irpf = "con IRPF" if invoice.irpf_amount else "sin IRPF"
        print(f"{path.name}: {len(invoice.line_items)} líneas, total {invoice.total} €, {irpf}")


if __name__ == "__main__":
    main()