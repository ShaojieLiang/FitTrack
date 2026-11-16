"""Entirely invented fixture. No personal records, images or response IDs are used."""
from datetime import date,timedelta
import math
import random

def generate(days=120,seed=2027):
    rng = random.Random(seed)
    start = date(2025,1,1)
    body,sessions = [],[]
    for i in range(days):
        d = str(start+timedelta(days=i))
        if i%11!=4:  # Deliberate missing measurements, never zero-filled.
            for metric,value,unit in (("weight",74-i*0.008+rng.gauss(0,0.35),"kg"),
                                      ("bodyfat",21-i*0.006+rng.gauss(0,0.4),"%")):
                body.append({"day":d,"metric":metric,"value":round(value,2),"unit":unit,"measured_at":d+"T07:30:00+08:00"})
        if i%2==0:
            moves = []
            for exercise,equipment,weight,offset in (("Bench press","demo-flat-bench-A",50,0),("Seated row","demo-cable-A",40,1)):
                reps = max(3,min(15,round(7+0.035*i+math.sin(i/11)+rng.gauss(0,0.9)+offset)))
                moves.append({"exercise":exercise,"equipment":equipment,"sets":[
                    {"kind":"warmup","done":True,"weight":weight/2,"unit":"kg","reps":12},
                    {"kind":"work","done":True,"weight":weight,"unit":"kg","reps":reps,"rpe":8},
                    {"kind":"work","done":True,"weight":weight,"unit":"kg","reps":max(1,reps-1),"rpe":8.5},
                    {"kind":"work","done":False,"weight":weight,"unit":"kg","reps":8},
                    {"kind":None,"done":True,"weight":weight,"unit":"kg","reps":6}]})
            moves.append({"exercise":"Stationary bike","equipment":"demo-bike-A","sets":[{"kind":"cardio","done":True,"duration_s":600}]})
            sessions.append({"id":f"synthetic-session-{i:03}","day":d,"title":"Synthetic strength session","movements":moves})
    return {"provenance":"SYNTHETIC — invented fixture; not personal data or evidence of fitness benefit",
            "seed":seed,"sessions":sessions,"body":body}
