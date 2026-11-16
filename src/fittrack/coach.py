"""Rule-based assistance, immutable forecast snapshots, explicitly supplied feedback."""
from datetime import datetime
import hashlib
import json
from .ingest import day,number

def suggest(prediction):
    if prediction["status"]!="ready":
        return "可比记录不足：继续记录同动作、器械、重量和正式组；暂不调整训练。"
    delta = prediction["prediction"]-prediction["last_reps"]
    if delta>=1:
        return "维持当前重量；在动作质量与原定强度允许时尝试增加1次，完成后记录实际表现。"
    if delta<=-1:
        return "预计表现可能回落：先核对休息与恢复情况，可维持重量并减少目标次数，训练后复核。"
    return "维持当前重量与目标次数；记录实际完成次数和主观强度，再判断是否调整。"

def save_forecast(db,prediction,created_at):
    if prediction["status"]!="ready":
        raise ValueError("cannot save an insufficient-data forecast")
    stamp = datetime.fromisoformat(created_at)
    if stamp.utcoffset() is None or str(stamp.date())>=prediction["target_day"]:
        raise ValueError("forecast must be recorded before target calendar day with timezone")
    if prediction["cutoff"]>str(stamp.date()):
        raise ValueError("training cutoff is after forecast creation")
    identity = {k:prediction[k] for k in ("source","exercise","equipment","weight_kg","target_day")}
    ident = hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:20]
    with db:
        db.execute("""INSERT INTO forecasts(id,source,created_at,target_day,exercise,equipment,weight_kg,
         cutoff,prediction,model,suggestion) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING""",
         (ident,prediction["source"],created_at,prediction["target_day"],prediction["exercise"],prediction["equipment"],
          prediction["weight_kg"],prediction["cutoff"],prediction["prediction"],prediction["model"],suggest(prediction)))
    return dict(db.execute("SELECT * FROM forecasts WHERE id=?",(ident,)).fetchone())

def feedback(db,ident,actual,actual_day,adopted=None,note=None):
    record = db.execute("SELECT * FROM forecasts WHERE id=?",(ident,)).fetchone()
    if record is None:
        raise ValueError("unknown forecast")
    if day(actual_day)!=record["target_day"]:
        raise ValueError("feedback must match forecast target day")
    value = number(actual)
    if value is None:
        raise ValueError("actual reps required")
    if adopted is not None and type(adopted) is not bool:
        raise ValueError("adopted must be true, false or null")
    if record["actual"] is not None:
        if record["actual"]!=value or record["adopted"]!=adopted or record["feedback_note"]!=note:
            raise ValueError("feedback already recorded; refusing silent overwrite")
        return dict(record)
    with db:
        db.execute("UPDATE forecasts SET actual=?,actual_day=?,adopted=?,feedback_note=? WHERE id=?",
                   (value,actual_day,adopted,note,ident))
    return dict(db.execute("SELECT * FROM forecasts WHERE id=?",(ident,)).fetchone())
