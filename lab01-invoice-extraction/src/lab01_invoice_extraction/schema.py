"""Modelo de datos para facturas españolas extraídas por Claude."""

import json
from datetime import date

from pydantic import BaseModel, Field


class Party(BaseModel):
    """Emisor o destinatario de la factura."""

    name: str = Field(description="Nombre completo o razón social")
    tax_id: str = Field(description="NIF o CIF, por ejemplo B12345678")
    address: str = Field(description="Domicilio completo en una sola línea")


class LineItem(BaseModel):
    """Una línea de detalle de la factura."""

    description: str = Field(description="Concepto: descripción del producto o servicio")
    quantity: float = Field(description="Número de unidades")
    unit_price: float = Field(description="Precio unitario sin impuestos, en euros")
    vat_rate: float = Field(
        description="Tipo de IVA en porcentaje, por ejemplo 21 para el 21 %"
    )


class Invoice(BaseModel):
    """Datos estructurados extraídos de una factura española."""

    invoice_number: str = Field(
        description="Número de factura, incluida la serie si existe, por ejemplo 2026-A-0042"
    )
    issue_date: date = Field(description="Fecha de expedición en formato ISO AAAA-MM-DD")
    issuer: Party = Field(description="Emisor de la factura (quien la expide y cobra)")
    recipient: Party = Field(description="Destinatario de la factura (cliente que paga)")
    line_items: list[LineItem] = Field(description="Líneas de detalle de la factura")
    tax_base: float = Field(description="Base imponible: suma de las líneas sin impuestos")
    vat_amount: float = Field(description="Cuota total de IVA")
    irpf_amount: float | None = Field(
        default=None,
        description=(
            "Importe de la retención de IRPF como número POSITIVO (por ejemplo 913.74), "
            "aunque en la factura aparezca con signo negativo. "
            "Si la factura no tiene retención, null"
        ),
    )
    total: float = Field(
        description="Total a pagar: base imponible + cuota de IVA - retención de IRPF"
    )


if __name__ == "__main__":
    # Imprime el JSON Schema que Claude recibe a través de las salidas estructuradas
    print(json.dumps(Invoice.model_json_schema(), indent=2, ensure_ascii=False))