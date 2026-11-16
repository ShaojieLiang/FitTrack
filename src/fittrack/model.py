"""One-step walk-forward evaluation; no labels or body readings from the future."""
from collections import Counter, defaultdict
from datetime import date
import statistics
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .db import history

MIN_TRAIN = 12
BASE_FEATURES = ["last_reps","mean_last_3","change_last_3","gap_days","sessions_previous_7_days"]
FEATURES = BASE_FEATURES + ["weight_median_previous_7_days","bodyfat_median_previous_7_days"]

def groups(db, source):
    data = history(db, source=source)
    first = {}
    for row in data["training"]:
        if row["kind"] == "work":
            first.setdefault((row["session_id"],row["movement_pos"]),row)
    accepted = defaultdict(list)
    excluded = Counter()
    for r in first.values():
        if not r["equipment"] or not r["done"] or r["reps"] is None or r["weight_kg"] is None:
            excluded["incomplete_or_missing_comparability"] += 1
            continue
        key = (r["exercise"],r["equipment"],round(r["weight_kg"],5))
        accepted[key].append({"day":r["day"],"reps":r["reps"]})
    for key,rows in list(accepted.items()):
        counts = Counter(r["day"] for r in rows)
        accepted[key] = sorted((r for r in rows if counts[r["day"]]==1),key=lambda r:r["day"])
        excluded["ambiguous_multiple_sessions_same_day"] += sum(n for n in counts.values() if n>1)
    return accepted,data["body"],dict(excluded)

def features(past, target_day, body):
    """All observations must precede the target's local calendar date."""
    past = [r for r in past if r["day"] < target_day]
    if len(past) < 3:
        raise ValueError("need three prior comparable sessions")
    d = date.fromisoformat(target_day)
    recent = past[-3:]
    values = [past[-1]["reps"],statistics.mean(r["reps"] for r in recent),
              recent[-1]["reps"]-recent[0]["reps"],
              (d-date.fromisoformat(past[-1]["day"])).days,
              sum(0 < (d-date.fromisoformat(r["day"])).days <= 7 for r in past)]
    for metric in ("weight","bodyfat"):
        eligible = [r["value"] for r in body if r["metric"]==metric and
                    0 < (d-date.fromisoformat(r["day"])).days <= 7]
        values.append(statistics.median(eligible) if eligible else np.nan)
    return values

def pipeline():
    return make_pipeline(SimpleImputer(strategy="median",add_indicator=True,keep_empty_features=True),
                         StandardScaler(),Ridge(alpha=10.0))

def dataset(rows, body):
    return [(r["day"],features(rows[:i],r["day"],body),r["reps"])
            for i,r in enumerate(rows) if i>=3]

def evaluate(db, source):
    comparable,body,excluded = groups(db,source)
    predictions = []
    for key,rows in comparable.items():
        samples = dataset(rows,body)
        for i in range(MIN_TRAIN,len(samples)):
            train,test = samples[:i],samples[i]
            x,y = np.array([r[1] for r in train]),np.array([r[2] for r in train])
            estimates = {"last":test[1][0],"mean3":test[1][1]}
            for name,width in (("ridge_training",5),("ridge_body",7)):
                estimates[name] = max(0,float(pipeline().fit(x[:,:width],y).predict(np.array([test[1][:width]]))[0]))
            predictions.append({"exercise":key[0],"equipment":key[1],"weight_kg":key[2],
                                "day":test[0],"train_cutoff":train[-1][0],"train_samples":i,
                                "actual":test[2],"predictions":estimates})
    metrics = {}
    if predictions:
        metrics = {name:round(statistics.mean(abs(r["actual"]-r["predictions"][name]) for r in predictions),4)
                   for name in predictions[0]["predictions"]}
    return {"source":source,"synthetic":source=="synthetic","target":"next comparable first work-set reps",
            "method":"expanding-window, one session ahead; fixed Ridge alpha=10; train-only preprocessing",
            "minimum_training_samples":MIN_TRAIN,"feature_names":FEATURES,
            "comparable_sessions":sum(map(len,comparable.values())),"excluded":excluded,
            "test_samples":len(predictions),"mae_reps":metrics,"predictions":predictions,
            "limitation":"Synthetic results validate software only; effort, rest and equipment metadata may limit real comparability."}

def forecast(db,source,key,target_day):
    comparable,body,_ = groups(db,source)
    rows = [r for r in comparable.get(key,[]) if r["day"] < target_day]
    samples = dataset(rows,body)
    if len(samples)<MIN_TRAIN:
        return {"status":"insufficient_data","comparable_sessions":len(rows),"required_labeled_samples":MIN_TRAIN}
    # Gate the model using past-only walk-forward errors, never the new target outcome.
    local_errors = {"last":[],"ridge_body":[]}
    for i in range(MIN_TRAIN,len(samples)):
        train,test = samples[:i],samples[i]
        model = pipeline().fit([r[1] for r in train],[r[2] for r in train])
        local_errors["last"].append(abs(test[2]-test[1][0]))
        local_errors["ridge_body"].append(abs(test[2]-max(0,float(model.predict([test[1]])[0]))))
    use_ridge = len(local_errors["last"])>=5 and statistics.mean(local_errors["ridge_body"])<statistics.mean(local_errors["last"])
    next_x = features(rows,target_day,body)
    pred = float(pipeline().fit([r[1] for r in samples],[r[2] for r in samples]).predict([next_x])[0]) if use_ridge else next_x[0]
    return {"status":"ready","source":source,"exercise":key[0],"equipment":key[1],"weight_kg":key[2],
            "target_day":target_day,"cutoff":rows[-1]["day"],"prediction":round(max(0,pred),2),
            "last_reps":rows[-1]["reps"],"model":"ridge_body" if use_ridge else "last_validation_fallback",
            "validation_samples":len(local_errors["last"]),"comparable_sessions":len(rows),
            "validation_mae":{k:round(statistics.mean(v),3) if v else None for k,v in local_errors.items()}}
