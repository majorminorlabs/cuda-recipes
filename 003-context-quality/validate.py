#!/usr/bin/env python3
"""Validate the public prose/code package, and private response coverage when present."""
import collections
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COLS = {
    "fit-results.csv": ["model", "ctx_size", "loaded_full_gpu", "layers_on_cuda", "layers_total", "kv_buffer_mib", "rs_buffer_mib", "peak_vram_mib", "error"],
    "prefill-results.csv": ["model", "length_label", "doc_id", "prompt_tokens", "prefill_s", "prefill_tps", "peak_vram_mib"],
    "answer-results.csv": ["model", "length_label", "doc_id", "question_id", "task_type", "position", "prompt_tokens", "cached_prompt_tokens", "generated_tokens", "answer_s", "correct", "format_strict_correct", "failure_class"],
}
FAILS = {"", "wrong_answer", "invalid_json", "truncated", "error"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def rows(folder, name, columns=None):
    with (folder / name).open(newline="") as source:
        reader = csv.DictReader(source)
        require(reader.fieldnames == (columns or COLS[name]), f"{folder.name}/{name}: header mismatch")
        result = list(reader)
    require(all(None not in row and None not in row.values() for row in result), f"{name}: malformed CSV row")
    return result


def check_dataset(folder):
    manifest = json.loads((folder / "documents/manifest.json").read_text())
    question_info = manifest["questions"]
    question_file = folder / question_info["path"]
    require(digest(question_file) == question_info["sha256"], f"{folder.name}: question hash mismatch")
    questions = jsonl(question_file)
    require(len(questions) == question_info["count"], f"{folder.name}: question count mismatch")
    by_id = {question["question_id"]: question for question in questions}
    require(len(by_id) == len(questions), f"{folder.name}: duplicate question IDs")
    documents = {document["doc_id"]: document for document in manifest["documents"]}
    require(len(documents) == len(manifest["documents"]), "duplicate document IDs")
    for document in documents.values():
        path = folder / document["path"]
        require(digest(path) == document["sha256"], f"{path.name}: document hash mismatch")
        require(path.stat().st_size == document["bytes"], f"{path.name}: document byte count mismatch")
        if "insertions_path" in document:
            require(digest(folder / document["insertions_path"]) == document["insertions_sha256"], "insertion hash mismatch")
    counts = collections.Counter((question["length_label"], question["task_type"]) for question in questions)
    for length, tasks in question_info["count_by_length_and_task"].items():
        for task, count in tasks.items():
            require(counts.pop((length, task), 0) == count, f"{length}/{task}: question grid mismatch")
    require(not counts, "unexpected question length/task")
    for question in questions:
        document = documents.get(question["doc_id"])
        require(document is not None and question["length_label"] == document["length_label"], "question/document mismatch")
    return by_id, documents


def check_raw_coverage(raw_dir, answers, models, arm):
    # An absent private capture is expected in the public release. Once any
    # capture exists, require complete coverage across every expected model.
    if not any(raw_dir.glob("primary-*.jsonl")):
        print(f"{arm} arm: raw responses not published; coverage check skipped.")
        return
    for model in sorted(models):
        path = raw_dir / f"primary-{model}.jsonl"
        require(path.is_file(), f"{arm}/{model}: missing raw response file")
        records = jsonl(path)
        ids = {record.get("question_id") for record in records
               if record.get("model") == model and record.get("arm") == "primary"}
        expected = {row["question_id"] for row in answers if row["model"] == model}
        require(expected <= ids, f"{arm}/{model}: missing raw response coverage")
    print(f"PASS: {arm} raw response coverage for all {len(models)} models.")


def validate_arm(folder, config, raw_dir, arm):
    questions, documents = check_dataset(folder)
    answers = rows(folder, "answer-results.csv")
    fit = rows(folder, "fit-results.csv")
    prefill = rows(folder, "prefill-results.csv")
    models = set(config["models"])
    require(answers, f"{arm}: answer CSV is empty")
    require({row["model"] for row in answers} == models, f"{arm}: expected all configured models")
    require({row["model"] for row in fit} == models, f"{arm}: fit model coverage mismatch")
    counts = collections.Counter((row["model"], row["question_id"]) for row in answers)
    require(set(counts) == {(model, qid) for model in models for qid in questions}, f"{arm}: incomplete question coverage")
    require(all(count == 1 for count in counts.values()), f"{arm}: duplicate answer rows")
    require(set(documents) == {question["doc_id"] for question in questions.values()}, f"{arm}: document coverage mismatch")
    prefill_keys = collections.Counter((row["model"], row["doc_id"]) for row in prefill)
    require(set(prefill_keys) == {(model, doc) for model in models for doc in documents}, f"{arm}: prefill coverage mismatch")
    require(all(count == 1 for count in prefill_keys.values()), f"{arm}: duplicate prefill rows")
    for row in answers:
        question = questions[row["question_id"]]
        for key in ("doc_id", "length_label", "task_type", "position"):
            require(row[key] == question[key], f"{arm}/{row['question_id']}: {key} mismatch")
        require(row["correct"] in {"0", "1"} and row["format_strict_correct"] in {"0", "1"}, "invalid score fields")
        require(row["failure_class"] in FAILS, "invalid failure class")
        require((row["correct"] == "1") == (row["failure_class"] == ""), "score/failure mismatch")
        for key in ("prompt_tokens", "cached_prompt_tokens", "generated_tokens"):
            require(int(row[key]) >= 0, f"invalid {key}")
        require(math.isfinite(float(row["answer_s"])) and float(row["answer_s"]) >= 0, "invalid answer duration")
    for row in prefill:
        require(row["length_label"] == documents[row["doc_id"]]["length_label"], "prefill/document mismatch")
        for key in ("prefill_s", "prefill_tps", "peak_vram_mib"):
            require(math.isfinite(float(row[key])) and float(row[key]) >= 0, f"invalid {key}")
    check_raw_coverage(raw_dir, answers, models, arm)
    print(f"PASS: {arm} arm ({len(answers)} answers, {len(fit)} fit rows, {len(prefill)} prefill rows); question/document hashes verified.")


def check_checksums(root):
    count = 0
    for line in (root / "SHA256SUMS").read_text().splitlines():
        if not line.strip():
            continue
        checksum, name = line.split(maxsplit=1)
        path = (root / name.lstrip("*")).resolve()
        require(path.is_relative_to(root.resolve()), "checksum path escapes package")
        require(path.is_file() and digest(path) == checksum, f"SHA256SUMS mismatch: {name}")
        count += 1
    require(count > 0, "empty checksum manifest")
    print(f"PASS: SHA256SUMS ({count} files).")


def validate_package(root=ROOT):
    data = root / "DATA"
    config = json.loads((data / "study-config.json").read_text())
    validate_arm(data, config, root / "_internal/responses", "prose")
    validate_arm(data / "code", config["arms"]["code"], root / "_internal/code/responses", "code")
    exploratory = data / "exploratory-thinking-on"
    old_columns = COLS["answer-results.csv"][:11] + ["failure_class"]
    answers = rows(exploratory, "answer-results.csv", old_columns)
    require(answers and {row["model"] for row in answers} == {"qwen36_35b_a3b"}, "exploratory arm malformed")
    rows(exploratory, "fit-results.csv")
    rows(exploratory, "prefill-results.csv")
    print(f"PASS: exploratory arm separately validated ({len(answers)} answers).")
    check_checksums(root)


def main():
    try:
        validate_package()
        return 0
    except (AssertionError, KeyError, OSError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
