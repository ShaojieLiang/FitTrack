"""Validate complete batches before atomic upserts; missing values stay NULL."""
from datetime import date, datetime
import math

def day(value):
    return date.fromisoformat(value).isoformat()

def number(value, minimum=0, maximum=None):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a measurement")
    value = float(value)
    if not math.isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        raise ValueError("measurement outside supported range")
    return value

def timestamp(value, expected_day):
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None or str(parsed.date()) != expected_day:
        raise ValueError("measurement timestamp needs timezone and matching local date")
    return parsed.isoformat()

def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing {field}")
    return value.strip()

BODY_UNITS = {"weight":"kg", "bodyfat":"%", "waist":"cm", "muscle_mass":"kg",
              "systolic":"mmHg", "diastolic":"mmHg", "pulse":"bpm"}

def ingest(db, payload, source):
    if source not in {"synthetic", "server", "manual"}:
        raise ValueError("unsupported data source")
    sessions, groups, bodies = [], [], []
    seen = set()
    for s in payload.get("sessions", []):
        ident = text(str(s["id"]), "session id")
        if ident in seen:
            raise ValueError("duplicate session id within batch")
        seen.add(ident)
        sessions.append((source, ident, day(s["day"]), str(s.get("title", "Training"))))
        for mi, move in enumerate(s.get("movements", [])):
            exercise = text(move["exercise"], "exercise")
            equipment = move.get("equipment") or None
            for si, g in enumerate(move.get("sets", [])):
                done = g.get("done")
                if done is not None and type(done) is not bool:
                    raise ValueError("done must be true, false or null")
                kind = g.get("kind")
                if kind not in {None, "warmup", "work", "cardio", "unknown"}:
                    raise ValueError("unsupported set kind")
                weight = number(g.get("weight"))
                unit = g.get("unit")
                if weight is not None:
                    if unit not in {"kg", "lb"}:
                        raise ValueError("weight requires explicit kg or lb")
                    weight *= 0.45359237 if unit == "lb" else 1
                groups.append((source, ident, mi, si, exercise, equipment, kind, done,
                               weight, number(g.get("reps")), number(g.get("rpe"), 0, 10),number(g.get("duration_s"))))
    seen_body = set()
    for b in payload.get("body", []):
        d, metric = day(b["day"]), b["metric"]
        if metric not in BODY_UNITS or b["unit"] != BODY_UNITS[metric]:
            raise ValueError("unsupported body metric or unit")
        if (d,metric) in seen_body:
            raise ValueError("duplicate body metric within day; resolve conflict before import")
        seen_body.add((d,metric))
        value = number(b.get("value"), maximum=100 if metric=="bodyfat" else None)
        if value is None:
            continue
        bodies.append((source,d,metric,value,b["unit"],timestamp(b.get("measured_at"),d)))
    with db:
        for s in sessions:
            db.execute("INSERT INTO sessions VALUES(?,?,?,?) ON CONFLICT(source,external_id) DO UPDATE SET day=excluded.day,title=excluded.title",s)
            db.execute("DELETE FROM sets WHERE source=? AND session_id=?",s[:2])
        db.executemany("INSERT INTO sets VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",groups)
        db.executemany("""INSERT INTO body VALUES(?,?,?,?,?,?) ON CONFLICT(source,day,metric)
            DO UPDATE SET value=excluded.value,unit=excluded.unit,measured_at=excluded.measured_at""",bodies)
    return {"sessions":len(sessions),"sets":len(groups),"body":len(bodies),"source":source}
