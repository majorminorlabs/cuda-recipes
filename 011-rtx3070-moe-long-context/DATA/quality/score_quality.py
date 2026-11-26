#!/usr/bin/env python3
"""Deterministic scorer for the fixed Edge0/Qwen 60-item set."""
import ast, json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ITEMS = json.loads((ROOT / "items.json").read_text())

ALLOWED_AST = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Expr,
    ast.Assign, ast.AugAssign, ast.For, ast.If, ast.Compare, ast.In, ast.NotIn,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Name, ast.Load,
    ast.Store, ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Set, ast.Subscript,
    ast.Slice, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
    ast.Mod, ast.Pow, ast.UnaryOp, ast.USub, ast.UAdd, ast.Not, ast.BoolOp,
    ast.And, ast.Or, ast.Call, ast.keyword, ast.ListComp, ast.GeneratorExp,
    ast.comprehension)
SAFE = {"sum":sum,"max":max,"min":min,"sorted":sorted,"set":set,"len":len,"range":range,"all":all}

def same(a,b):
    if isinstance(a,bool) or isinstance(b,bool): return type(a) is type(b) and a == b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)): return a == b
    if isinstance(a,dict) and isinstance(b,dict): return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list): return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return type(a) is type(b) and a == b

def score(item, output):
    if not isinstance(output,str): output=json.dumps(output,ensure_ascii=False)
    candidate=output.strip()
    # Content categories are scored for their answer/code; accept one outer
    # ```json fence. Instruction-following items keep strict JSON-only scoring.
    if item["category"] != "instruction_following" and candidate.startswith("```json") and candidate.endswith("```"):
        candidate=candidate[len("```json"):].strip()
        candidate=candidate[:-3].strip()
    try: parsed=json.loads(candidate)
    except Exception: return False,"invalid_json"
    if item["category"] != "coding": return same(parsed,item["reference_response"]),None
    try:
        source=parsed["code"]
        if not isinstance(source,str) or len(source)>20000: return False,"invalid_code"
        tree=ast.parse(source)
        nodes=list(ast.walk(tree))
        if len(nodes)>500 or any(not isinstance(n,ALLOWED_AST) for n in nodes): return False,"disallowed_syntax"
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        if len(funcs)!=1 or funcs[0].name!="solve": return False,"function_contract"
        bound={a.arg for a in nodes if isinstance(a,ast.arg)} | {n.id for n in nodes if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store)}
        for n in nodes:
            if isinstance(n,ast.Call) and not (isinstance(n.func,ast.Name) and n.func.id in SAFE): return False,"disallowed_call"
            if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load) and n.id not in SAFE and n.id not in bound: return False,"unbound_name"
            if isinstance(n,ast.Constant) and type(n.value) is int and abs(n.value)>1000000: return False,"integer_limit"
        scope={"__builtins__":{},**SAFE}
        exec(compile(tree,"<answer>","exec"),scope)
        for case in item["cases"]:
            if scope["solve"](*case["args"]) != case["expected"]: return False,"test_failed"
        return True,None
    except Exception as exc: return False,type(exc).__name__

def main():
    if len(sys.argv)!=3:
        raise SystemExit("usage: score_quality.py MODEL raw-output.jsonl")
    model,path=sys.argv[1:]
    raw={}
    for line in Path(path).read_text().splitlines():
        row=json.loads(line); raw[row["item_id"]]=row
    rows=[]; cats=Counter(); totals=Counter()
    for item in ITEMS:
        row=raw.get(item["id"],{})
        ok,reason=score(item,row.get("output"))
        cat=item["category"]; totals[cat]+=1; cats[cat]+=int(ok)
        rows.append({"item_id":item["id"],"category":cat,"score":int(ok),"reason":reason,"output":row.get("output"),"status":row.get("status","missing")})
    result={"model":model,"total":{"score":sum(cats.values()),"items":len(ITEMS)},"categories":{c:{"score":cats[c],"items":totals[c]} for c in totals},"rows":rows}
    out=Path(path).with_name(Path(path).stem.replace("raw","scores")+".json")
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"model":model,"total":result["total"],"categories":result["categories"],"scores_file":str(out)},indent=2))

if __name__=="__main__": main()
