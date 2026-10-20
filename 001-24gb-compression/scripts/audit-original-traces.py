#!/usr/bin/env python3
"""Summarize immutable Phase 1 traces without changing the original result set."""
import argparse
import collections
import json
import sqlite3
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.validate import json_equal, strict_json_loads


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace-dir", type=Path, required=True)
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    result = {"audit_version": "original-traces-readonly-v1", "models": {}}
    files = sorted(args.trace_dir.glob("*.json"))
    for model in ("nemotron", "qwen"):
        subset = [p for p in files if p.name.startswith(model + "_")]
        row = {"trace_files": len(subset), "categories": {}, "failure_classes": {},
               "tools": {"tasks": 0, "expected_calls": 0, "attempts": 0, "simulator_accepted_attempts": 0,
                         "exact_expected_sequences": 0, "all_structured_calls": 0,
                         "call_rounds": 0, "invalid_argument_json": 0,
                         "assistant_history_messages": 0, "assistant_history_with_reasoning": 0,
                         "task_details": {}}, "tool_use_decomposition": {
                           "trials": 0, "strict_task_success": 0,
                           "correct_tool_action_execution": 0,
                           "exact_expected_action_sequence": 0,
                           "all_attempts_accepted": 0,
                           "final_response_contract_compliance": 0,
                           "exact_actions_accepted_but_final_contract_failed": 0,
                           "final_contract_parse_failures": 0},
               "tokens": {"max_prompt": 0, "max_completion": 0},
               "trace_task_success": 0, "wall_seconds": 0.0}
        for path in subset:
            x = json.loads(path.read_text())
            task = x["task"]
            if task.get("category") == "tool_use":
                decomposition = row["tool_use_decomposition"]
                decomposition["trials"] += 1
                strict_success = bool(x.get("success"))
                decomposition["strict_task_success"] += int(strict_success)
                trace = x.get("tool_trace") or []
                exact_actions = [event.get("action") for event in trace] == task["expected_calls"]
                all_accepted = all(bool(event.get("ok")) for event in trace)
                correct_actions = exact_actions and all_accepted
                decomposition["exact_expected_action_sequence"] += int(exact_actions)
                decomposition["all_attempts_accepted"] += int(all_accepted)
                decomposition["correct_tool_action_execution"] += int(correct_actions)
                response_contract = False
                try:
                    response_value = strict_json_loads(x.get("content", ""))
                    response_contract = json_equal(response_value, task["reference_response"])
                except Exception:
                    decomposition["final_contract_parse_failures"] += 1
                decomposition["final_response_contract_compliance"] += int(response_contract)
                decomposition["exact_actions_accepted_but_final_contract_failed"] += int(
                    correct_actions and not response_contract)
            cat = row["categories"].setdefault(task["category"], {"n": 0, "success": 0})
            cat["n"] += 1
            cat["success"] += int(bool(x["success"]))
            row["trace_task_success"] += int(bool(x["success"]))
            for failure in (x.get("failure_class") or "").split(","):
                if failure:
                    row["failure_classes"][failure] = row["failure_classes"].get(failure, 0) + 1
            u = x.get("usage") or {}
            row["tokens"]["max_prompt"] = max(row["tokens"]["max_prompt"], u.get("prompt_tokens") or 0)
            row["tokens"]["max_completion"] = max(row["tokens"]["max_completion"], u.get("completion_tokens") or 0)
            interaction = x.get("interaction") or {}
            for response_round in interaction.get("responses", []):
                resp = response_round.get("response") or {}
                choice = (resp.get("choices") or [{}])[0] or {}
                message = choice.get("message") or {}
                calls = message.get("tool_calls") or []
                row["tools"]["all_structured_calls"] += len(calls)
                row["tools"]["call_rounds"] += int(bool(calls))
                for call in calls:
                    raw_args = (call.get("function") or {}).get("arguments")
                    try:
                        strict_json_loads(raw_args)
                    except Exception:
                        row["tools"]["invalid_argument_json"] += 1
                for message_in_history in response_round.get("request", {}).get("messages", []):
                    if message_in_history.get("role") == "assistant" and message_in_history.get("tool_calls"):
                        row["tools"]["assistant_history_messages"] += 1
                        row["tools"]["assistant_history_with_reasoning"] += int(bool(message_in_history.get("reasoning_content")))
            if task.get("expected_calls") is not None:
                row["tools"]["tasks"] += 1
                trace = x.get("tool_trace") or []
                actions = [event.get("action") for event in trace]
                row["tools"]["expected_calls"] += len(task["expected_calls"])
                row["tools"]["attempts"] += len(trace)
                row["tools"]["simulator_accepted_attempts"] += sum(bool(event.get("ok")) for event in trace)
                exact = actions == task["expected_calls"]
                row["tools"]["exact_expected_sequences"] += int(exact)
                detail = row["tools"]["task_details"].setdefault(task["id"], {"n": 0, "success": 0, "exact_sequence": 0, "accepted_attempts": 0, "attempts": 0})
                detail["n"] += 1
                detail["success"] += int(bool(x["success"]))
                detail["exact_sequence"] += int(exact)
                detail["accepted_attempts"] += sum(bool(event.get("ok")) for event in trace)
                detail["attempts"] += len(trace)
        con = sqlite3.connect(args.db)
        trials = con.execute("SELECT COUNT(*), SUM(success), SUM(wall_s), MAX(prompt_tokens), MAX(completion_tokens) FROM trials WHERE model=?", (model,)).fetchone()
        con.close()
        row["checkpoint_db"] = {"trials": trials[0], "success": trials[1], "wall_seconds": trials[2], "max_prompt_tokens": trials[3], "max_completion_tokens": trials[4]}
        result["models"][model] = row
    result["integrity"] = {"trace_files": len(files), "expected_trace_files": 240,
                           "all_trials_match_checkpoint": all(v["trace_files"] == 120 and v["checkpoint_db"]["trials"] == 120 and v["trace_task_success"] == v["checkpoint_db"]["success"] for v in result["models"].values())}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["integrity"], sort_keys=True))


if __name__ == "__main__":
    main()
