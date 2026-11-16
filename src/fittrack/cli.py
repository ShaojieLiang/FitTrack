"""Reproducible offline demo and opt-in private data commands."""
import argparse
from contextlib import closing
from datetime import date,datetime,timedelta,timezone
import json
from pathlib import Path
import shutil
import sqlite3
from . import __version__
from .db import connect,history,write_json
from .ingest import ingest,day
from .model import evaluate,forecast
from .coach import save_forecast,feedback,suggest
from .synthetic import generate

def demo(output,publish=None):
    from .report import figures,summary
    out=Path(output); out.mkdir(parents=True,exist_ok=True)
    with closing(connect(out/"fittrack.sqlite3")) as db:
        sources={r[0] for r in db.execute("SELECT source FROM sessions UNION SELECT source FROM body UNION SELECT source FROM forecasts")}
        if sources-{"synthetic"}:
            raise ValueError("demo database contains non-synthetic records; choose a clean output directory")
        # Reset only this dedicated, synthetic demo projection for reproducible replay.
        with db:
            for table in ("forecasts","sets","sessions","body"):
                db.execute("DELETE FROM "+table)
        fixture=generate()
        imported=ingest(db,fixture,"synthetic")
        evaluation=evaluate(db,"synthetic")
        key=("Bench press","demo-flat-bench-A",50.0)
        target="2025-05-01"
        pred=forecast(db,"synthetic",key,target)
        record=save_forecast(db,pred,"2025-04-30T20:00:00+08:00")
        future=generate(days=122)
        later={"sessions":[r for r in future["sessions"] if r["day"]>=target],
               "body":[r for r in future["body"] if r["day"]>=target]}
        ingest(db,later,"synthetic")
        actual=later["sessions"][0]["movements"][0]["sets"][1]["reps"]
        record=feedback(db,record["id"],actual,target,note="Synthetic chronological replay; adoption unknown")
        next_prediction=forecast(db,"synthetic",key,"2025-05-03")
        next_record=save_forecast(db,next_prediction,"2025-05-02T20:00:00+08:00")
        data=history(db,source="synthetic")
        write_json(out/"fixture.json",fixture)
        write_json(out/"evaluation.json",evaluation)
        write_json(out/"feedback.json",{"replay":record,"next":next_record})
        write_json(out/"history.json",data)
        summary(evaluation,record,next_prediction,out/"evaluation.md")
        figures(data,evaluation,record,next_prediction,out)
    if publish:
        dest=Path(publish); (dest/"assets").mkdir(parents=True,exist_ok=True)
        for name in ("overview.png","training.png","body.png","prediction.png","feedback.png","feature-tour.gif"):
            shutil.copyfile(out/name,dest/"assets"/name)
        for name in ("evaluation.json","evaluation.md","feedback.json"):
            shutil.copyfile(out/name,dest/name)
    return {"synthetic":True,"imported_initial":imported,"test_samples":evaluation["test_samples"],
            "mae_reps":evaluation["mae_reps"],"feedback_error_reps":abs(record["prediction"]-record["actual"]),
            "next_prediction":next_prediction,"output":str(out)}

def parser():
    p=argparse.ArgumentParser(prog="fittrack",description="FitTrack: private data, reproducible public demo")
    p.add_argument("--version",action="version",version=__version__)
    p.add_argument("--db",default="private/fittrack.sqlite3",help="private SQLite database path")
    sub=p.add_subparsers(dest="command",required=True)
    d=sub.add_parser("demo",help="run offline synthetic workflow, plots and chronological replay")
    d.add_argument("--output",default="outputs/demo")
    d.add_argument("--publish",help="copy ONLY synthetic demo artifacts to a documentation directory")
    i=sub.add_parser("import",help="import the normalized JSON contract")
    i.add_argument("file",type=Path)
    i.add_argument("--source",choices=["manual","synthetic"],default="manual")
    h=sub.add_parser("history")
    h.add_argument("--start",default="0001-01-01",type=day)
    h.add_argument("--end",default="9999-12-31",type=day)
    for name in ("history","evaluate","forecast"):
        s=h if name=="history" else sub.add_parser(name)
        s.add_argument("--source",required=True,choices=["manual","synthetic","server"])
        if name=="forecast":
            s.add_argument("--exercise",required=True)
            s.add_argument("--equipment",required=True)
            s.add_argument("--weight",required=True,type=float)
            s.add_argument("--date",required=True,type=day)
    f=sub.add_parser("feedback")
    f.add_argument("id")
    f.add_argument("--actual",required=True,type=float)
    f.add_argument("--date",required=True,type=day)
    f.add_argument("--adopted",choices=["yes","no","unknown"],default="unknown")
    f.add_argument("--note")
    s=sub.add_parser("sync",help="explicit read-only training + body sync for one date")
    s.add_argument("--date",required=True,type=day)
    return p

def main(argv=None):
    args=parser().parse_args(argv)
    try:
        if args.command=="demo":
            result=demo(args.output,args.publish)
        else:
            with closing(connect(args.db)) as db:
                if args.command=="import":
                    result=ingest(db,json.loads(args.file.read_text(encoding="utf-8-sig")),args.source)
                elif args.command=="history":
                    result=history(db,args.start,args.end,args.source)
                elif args.command=="evaluate":
                    result=evaluate(db,args.source)
                elif args.command=="forecast":
                    now=datetime.now(timezone(timedelta(hours=8)))
                    if args.date<=str(now.date()):
                        raise ValueError("live forecast target must be after today; use demo for historical replay")
                    result=forecast(db,args.source,(args.exercise,args.equipment,round(args.weight,5)),args.date)
                    result["suggestion"]=suggest(result)
                    if result["status"]=="ready":
                        result=save_forecast(db,result,now.isoformat())
                elif args.command=="feedback":
                    if args.date>str(datetime.now(timezone(timedelta(hours=8))).date()):
                        raise ValueError("cannot record future actual outcomes")
                    result=feedback(db,args.id,args.actual,args.date,{"yes":True,"no":False,"unknown":None}[args.adopted],args.note)
                else:
                    from .server import sync
                    result=sync(db,args.date)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        return 0
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error) as exc:
        print(json.dumps({"status":"error","message":str(exc)},ensure_ascii=False))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
