"""Check the staged/unignored publication surface, without printing matched secrets."""
from pathlib import Path
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
TOKEN=re.compile(r"\b(?:xjllm|xjbody|xjfood|xjtpl|github_pat|gh[pousr])_[A-Za-z0-9_]{12,}\b")
LOCAL=re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\s\"']+",re.I)
PRIVATE={"private","data","imports","profile","reviews",".secrets",".venv"}
ALLOWED={"src","tests","scripts","docs","examples",".github"}
ROOT_FILES={"README.md","pyproject.toml",".gitignore",".gitattributes",".env.example","AGENTS.md","requirements-tested.txt"}

def check():
    paths=subprocess.check_output(["git","ls-files","--cached","--others","--exclude-standard","-z"],cwd=ROOT).decode().split("\0")
    errors=[]
    for name in filter(None,paths):
        path=Path(name)
        if set(path.parts)&PRIVATE or path.suffix in {".sqlite3",".db",".log"}:
            errors.append((name,"private path"))
        if path.parts[0] not in ALLOWED and name not in ROOT_FILES:
            errors.append((name,"outside publication allowlist"))
        if path.suffix.lower() in {".png",".gif"}:
            if path.parts[:2]!=("docs","assets"):
                errors.append((name,"image outside synthetic demo assets"))
            continue
        try:
            content=(ROOT/path).read_text(encoding="utf-8")
        except (UnicodeError,OSError):
            errors.append((name,"unexpected binary or unreadable file"))
            continue
        if TOKEN.search(content) or LOCAL.search(content):
            errors.append((name,"credential-like value or local user path"))
        if path.parts[0]=="src" and re.search(r"https?://",content):
            errors.append((name,"hardcoded service address in source"))
        if name==".env.example":
            for line in content.splitlines():
                if line.startswith("FITTRACK_") and line.partition("=")[2].strip():
                    errors.append((name,"configuration template must remain blank"))
    evaluation=ROOT/"docs/evaluation.json"
    if evaluation.exists():
        obj=json.loads(evaluation.read_text(encoding="utf-8"))
        if obj.get("source")!="synthetic" or obj.get("synthetic") is not True:
            errors.append(("docs/evaluation.json","non-synthetic public evaluation"))
    feedback=ROOT/"docs/feedback.json"
    if feedback.exists():
        for r in json.loads(feedback.read_text(encoding="utf-8")).values():
            if r.get("source")!="synthetic":
                errors.append(("docs/feedback.json","non-synthetic public feedback"))
    for name,reason in errors:
        print(f"FAIL {name}: {reason}")
    if not errors:
        print(f"PASS: {len(list(filter(None,paths)))} publication files checked; no matched secrets or private paths")
    return bool(errors)

if __name__=="__main__": sys.exit(check())
