"""Serialize ORM objects to JSON-safe dicts (UUID -> str, Decimal -> float,
datetime/date -> ISO). Used by every router."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


def serialize(obj):
    if obj is None:
        return None
    out = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name, None)
        if isinstance(val, UUID):
            out[col.name] = str(val)
        elif isinstance(val, Decimal):
            out[col.name] = float(val)
        elif isinstance(val, (datetime, date)):
            out[col.name] = val.isoformat()
        else:
            out[col.name] = val
    return out


def serialize_list(objs):
    return [serialize(o) for o in objs]
