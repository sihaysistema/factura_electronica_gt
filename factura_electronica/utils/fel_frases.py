# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""SAT phrase for a credit or debit note issued after two calendar months.

Catalogo de Frases 0.6.0, tipo 9 escenario 22: the note must carry
TipoFrase 9 / CodigoEscenario 22 when its emission date is after the
origin invoice date plus two calendar months.
"""

from __future__ import unicode_literals

import datetime

from dateutil.relativedelta import relativedelta

# America/Guatemala has no daylight-saving time. fel_datetime uses this
# same fixed offset when it formats FechaHoraEmision.
GUATEMALA_TZ = datetime.timezone(datetime.timedelta(hours=-6))

LATE_ORIGIN_TIPO = "9"
LATE_ORIGIN_CODIGO = "22"


def needs_late_origin_frase(emission, origin):
    """True when the note is issued after origin + 2 calendar months.

    The day that lands exactly on origin + 2 months does not qualify.
    Missing or unreadable dates do not qualify, so a note is not blocked.
    """

    emission_day = guatemala_calendar_date(emission)
    origin_day = calendar_date(origin)
    if emission_day is None or origin_day is None:
        return False
    return emission_day > (origin_day + relativedelta(months=2))


def ensure_late_origin_frase(frases, emission, origin):
    """Add phrase 9/22 when required and not already present.

    ``frases`` is the ``dte:Frases`` dict used by the XML builders, or None
    when the document has no phrase section yet (debit notes).
    """

    if not needs_late_origin_frase(emission, origin):
        return frases
    if _has_late_origin_frase(frases):
        return frases

    frase = {
        "@CodigoEscenario": LATE_ORIGIN_CODIGO,
        "@TipoFrase": LATE_ORIGIN_TIPO,
    }
    if not frases or not frases.get("dte:Frase"):
        return {"dte:Frase": frase}

    current = frases.get("dte:Frase")
    if isinstance(current, list):
        current.append(frase)
        return frases
    frases["dte:Frase"] = [current, frase]
    return frases


def guatemala_calendar_date(value):
    """Date of a FEL emission value in America/Guatemala."""

    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            return value.date()
        return value.astimezone(GUATEMALA_TZ).date()
    if isinstance(value, datetime.date):
        return value

    text = str(value).strip()
    if not text:
        return None
    if "T" not in text:
        return calendar_date(text)

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    compact = text[-5:]
    if len(text) > 5 and compact[0] in "+-" and compact[1:].isdigit() and ":" not in text[-6:]:
        text = text[:-5] + compact[0] + compact[1:3] + ":" + compact[3:5]
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.date()
    return parsed.astimezone(GUATEMALA_TZ).date()


def calendar_date(value):
    """A stored origin date (YYYY-MM-DD), without shifting timezone."""

    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = str(value).strip()
    if len(text) < 10:
        return None
    try:
        return datetime.datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _has_late_origin_frase(frases):
    for frase in _frase_list(frases):
        tipo = str(frase.get("@TipoFrase", "")).strip()
        codigo = str(frase.get("@CodigoEscenario", "")).strip()
        if tipo == LATE_ORIGIN_TIPO and codigo == LATE_ORIGIN_CODIGO:
            return True
    return False


def _frase_list(frases):
    if not frases:
        return []
    node = frases.get("dte:Frase")
    if not node:
        return []
    if isinstance(node, list):
        return node
    return [node]
