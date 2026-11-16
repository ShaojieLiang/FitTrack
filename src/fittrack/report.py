"""Static reports built from computed results; safe publication requires synthetic input."""
from pathlib import Path
import statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from .db import write_json

BG="#0c1220"
CARD="#151f30"
FG="#e7edf6"
MUTED="#96a8be"
TEAL="#5de4c7"
BLUE="#7da8ff"

def figures(data,evaluation,record,next_prediction,out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"text.color":FG,
        "axes.labelcolor":MUTED,"xtick.color":MUTED,"ytick.color":MUTED,
        "axes.facecolor":CARD,"figure.facecolor":BG,"axes.edgecolor":"#304057",
        "savefig.facecolor":BG})
    fig,axes=plt.subplots(2,2,figsize=(16,10))
    fig.subplots_adjust(top=.84,bottom=.08,left=.065,right=.97,hspace=.34,wspace=.22)
    fig.suptitle("FITTRACK  /  Train. Measure. Learn.",fontsize=26,fontweight="bold",ha="left",x=0.065,y=.975)
    fig.text(.065,.915,"SYNTHETIC DEMO  •  No personal records  •  No evidence of real fitness benefit",color=TEAL,fontsize=12)
    ax=axes[0,0]
    completed=[r for r in data["training"] if r["kind"]=="work" and r["done"]]
    counts={}
    for r in completed:
        counts[r["day"]]=counts.get(r["day"],0)+1
    ax.bar(range(len(counts)),list(counts.values()),color=TEAL,width=.65)
    ax.set(title="01  DAILY TRAINING / SYNTHETIC",xlabel="Recorded training sessions",ylabel="Completed work sets",ylim=(0,5.5))
    ax.text(.03,.84,f"{len(counts)} sessions  /  {len(completed)} completed work sets\nWarmup, unfinished and unlabelled sets excluded",transform=ax.transAxes,color=MUTED,fontsize=10)
    ax=axes[0,1]
    for metric,color in (("weight",TEAL),("bodyfat",BLUE)):
        rows=[r for r in data["body"] if r["metric"]==metric]
        vals=[100*r["value"]/rows[0]["value"] for r in rows]
        ax.plot([r["day"] for r in rows],vals,label=metric+" index",color=color,alpha=.8)
    ax.set(title="02  BODY TRENDS / SYNTHETIC",ylabel="Relative index (first observation = 100)")
    ax.set_xticks(ax.get_xticks()[::max(1,len(ax.get_xticks())//4)])
    ax.tick_params(axis="x",labelsize=8)
    ax.legend(frameon=False,labelcolor=MUTED,fontsize=9)
    ax=axes[1,0]
    rows=[r for r in evaluation["predictions"] if r["exercise"]=="Bench press"]
    ax.plot([r["actual"] for r in rows],color=TEAL,label="Actual reps")
    ax.plot([r["predictions"]["ridge_body"] for r in rows],color=BLUE,label="Ridge + body")
    ax.set(title="03  FORECAST / SYNTHETIC",xlabel="Chronological test sessions · Bench press / 50 kg",ylabel="First work-set reps")
    ax.legend(frameon=False,labelcolor=MUTED)
    ax=axes[1,1]
    ax.axis("off")
    mae=evaluation["mae_reps"]
    content=["04  FEEDBACK / SYNTHETIC", "",f"Walk-forward test samples       {evaluation['test_samples']}",
             f"Last-session MAE               {mae.get('last',0):.3f} reps",
             f"Training-only Ridge MAE         {mae.get('ridge_training',0):.3f} reps",
             f"Training + body Ridge MAE       {mae.get('ridge_body',0):.3f} reps","",
             f"Saved forecast                 {record['prediction']:.2f} reps",
             f"Later observed                 {record['actual']:.0f} reps",
             f"Absolute error                 {abs(record['actual']-record['prediction']):.2f} reps","",
             f"Next forecast                  {next_prediction['prediction']:.2f} reps",
             f"Selected method                {next_prediction['model']}","","Feedback does not prove a causal training benefit."]
    ax.text(.03,.98,"\n".join(content),va="top",fontfamily="monospace",fontsize=9.5,linespacing=1.5)
    for ax in axes.flat:
        if ax.axison:
            ax.spines[["top","right"]].set_visible(False)
            ax.grid(axis="y",alpha=.12)
    fig.savefig(out/"overview.png",dpi=120)
    # Four real report crops, assembled into an animated feature tour.
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    crop_paths=[]
    names=["training","body","prediction","feedback"]
    for ax,name in zip(axes.flat,names):
        bbox=ax.get_tightbbox(renderer).transformed(fig.dpi_scale_trans.inverted()).expanded(1.08,1.15)
        path=out/(name+".png")
        fig.savefig(path,dpi=135,bbox_inches=bbox)
        crop_paths.append(path)
    plt.close(fig)
    frames=[]
    for p in crop_paths:
        im=Image.open(p).convert("RGB")
        im.thumbnail((1000,620))
        frame=Image.new("RGB",(1040,660),BG)
        frame.paste(im,((1040-im.width)//2,(660-im.height)//2))
        frames.append(frame)
    frames[0].save(out/"feature-tour.gif",save_all=True,append_images=frames[1:],duration=2200,loop=0)

def summary(evaluation,record,next_prediction,path):
    scores="\n".join(f"| {k} | {v:.4f} |" for k,v in evaluation["mae_reps"].items())
    dates=[r["day"] for r in evaluation["predictions"]]
    text=f"""# FitTrack reproducible evaluation

**SYNTHETIC DATA ONLY. These results demonstrate the implementation, not real-world fitness efficacy.**

- Source: invented fixture; fixed seed 2027; no personal records.
- Target: next same-exercise, same-equipment, same-weight first work-set repetitions.
- Comparable sessions: {evaluation['comparable_sessions']}; chronological test predictions: {evaluation['test_samples']}.
- Test range: {min(dates) if dates else 'N/A'} to {max(dates) if dates else 'N/A'}.
- Method: expanding-window one-step evaluation; minimum {evaluation['minimum_training_samples']} labeled training samples per group.
- Fixed Ridge alpha=10. Median imputation and scaling are fitted only on each training window.
- Initial fixture: 120 calendar days, 60 training days, 109 body-measurement days; 11 days without body measurements. Non-training days are not assumed to be failed/missing workouts.
- Body inputs use measurements strictly before each target day; missing body readings remain missing until train-only imputation.
- Synthetic equipment and set labels are known. Real API data may lack these; unknown labels/equipment are excluded from forecasting.

| Method | MAE (reps; lower is better) |
| --- | ---: |
{scores}

## Feedback replay

A forecast is saved before the target day's synthetic record is imported. This is an offline chronological replay, not a real live user trial.

- Forecast created: {record['created_at']}; data cutoff: {record['cutoff']}.
- Target day: {record['target_day']}; predicted: {record['prediction']}; actual: {record['actual']} reps.
- Absolute error: {abs(record['prediction']-record['actual']):.2f} reps.
- Advice saved with the forecast: {record['suggestion']}
- Next target: {next_prediction['target_day']}; next prediction: {next_prediction['prediction']} reps.
- Method selected from prior-only validation: `{next_prediction['model']}`. Ridge is used only with at least five validation errors and lower MAE than the last-session baseline.
- Advice adoption is unknown unless supplied explicitly; no adherence is inferred.

## Interpretation and limitations

Compare all methods, including the training-only ablation; adding body data may fail to improve error. No claim of model superiority is made outside these synthetic records. Repetitions depend on effort, rest, technique and prescribed targets; a date and equipment match cannot fully control these. Sparse real data produces an explicit insufficient-data status. No muscle gain, fat loss, injury risk or causal benefit is predicted or established. Advice is a transparent rule layer, not an optimized or clinically validated prescription.

## Real-data validation

Not performed in this public project. A later private evaluation must report its dates, comparable sample counts, missingness and chronological errors separately. A prospective training-effect study would be needed to support claims that the advice improves outcomes.
"""
    Path(path).write_text(text,encoding="utf-8",newline="\n")
