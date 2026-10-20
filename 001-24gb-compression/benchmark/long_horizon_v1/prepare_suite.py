#!/usr/bin/env python3
"""Materialize pinned public OSS workspaces and hidden regression controls."""
import argparse
import difflib
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPOS = {
    "more-itertools": ("more-itertools/more-itertools", "MIT", "more-itertools"),
    "requests": ("psf/requests", "Apache-2.0", "requests"),
    "packaging": ("pypa/packaging", "Apache-2.0 OR BSD-2-Clause", "packaging"),
    "click": ("pallets/click", "BSD-3-Clause", "click"),
    "attrs": ("python-attrs/attrs", "MIT", "attrs"),
}
PINNED_REVISIONS = {
    "more-itertools": "4aeb4338ae1407d8da9723e86da99efeb446f719",
    "requests": "611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60",
    "packaging": "ef837aad3127167671eb37b9f6bd8a94ec7ce26e",
    "click": "2247b35ea1c47c727d7a06e51fa280e12a863ff6",
    "attrs": "ee66e7274852438cc23d4240a1a9cd632fda8b52",
}

TASKS = [
    {"id":"MI01","repo":"more-itertools","path":"more_itertools/more.py","test_path":"tests/test_more.py","test_name":"test_long_horizon_mi01","match":"if len(chunk) != n:","broken":"if len(chunk) > n:","test":"""import pytest
from more_itertools import chunked

def test_long_horizon_mi01():
    chunks = iter(chunked([1, 2, 3, 4, 5], 2, strict=True))
    assert next(chunks) == [1, 2]
    assert next(chunks) == [3, 4]
    with pytest.raises(ValueError, match="not divisible"):
        next(chunks)
""","upstream_test":"tests/test_more.py -k chunked","prompt":"Fix the strict chunking regression in `more_itertools.chunked`. With strict=True, complete chunks should remain available lazily, but the incomplete final chunk must raise ValueError instead of being yielded. Preserve non-strict behavior and add a regression test in the project's existing style."},
    {"id":"MI02","repo":"more-itertools","path":"more_itertools/more.py","test_path":"tests/test_more.py","test_name":"test_long_horizon_mi02","match":"if maxsplit == 1:\n                yield [item, *it]\n                return\n            buf = []\n            maxsplit -= 1","broken":"if maxsplit == 1:\n                yield [item, *it]\n                return\n            buf = []\n            maxsplit += 1","test":"""from more_itertools import split_before

def test_long_horizon_mi02():
    assert list(split_before("a,b,c,d", lambda ch: ch == ",", maxsplit=2)) == [
        ["a"], [",", "b"], [",", "c", ",", "d"]
    ]
""","upstream_test":"tests/test_more.py -k max_split","prompt":"Fix `split_before` so maxsplit counts completed boundaries down to zero and leaves the remaining input together. Preserve the unlimited (-1), zero, and positive split cases, and add a regression test following the repository's conventions."},
    {"id":"RE01","repo":"requests","path":"src/requests/sessions.py","test_path":"tests/test_requests.py","test_name":"test_long_horizon_re01","match":"for key in none_keys:","broken":"for key in []:","test":"""from requests.sessions import merge_setting

def test_long_horizon_re01():
    assert merge_setting({"verify": None}, {"verify": "/ca.pem", "timeout": 3}) == {"timeout": 3}
""","upstream_test":"tests/test_requests.py -k merged","prompt":"Fix the mapping merge behavior in `requests.sessions.merge_setting`: an explicit None in the request-level mapping means remove that inherited key. Request values must still override session values, and unrelated session entries must remain. Add a regression test in the existing Requests test suite."},
    {"id":"RE02","repo":"requests","path":"src/requests/sessions.py","test_path":"tests/test_hooks.py","test_name":"test_long_horizon_re02","match":"if request_hooks is None or request_hooks.get(\"response\") == []:","broken":"if request_hooks is None:","test":"""from requests.sessions import merge_hooks

def test_long_horizon_re02():
    seen = []
    callback = lambda response, **kwargs: seen.append(response)
    assert merge_hooks({"response": []}, {"response": [callback]}) == {"response": [callback]}
""","upstream_test":"tests/test_hooks.py -k hooks","prompt":"Fix session/request hook merging so an empty request-level response hook list does not accidentally erase the session-level callbacks. Preserve the existing special handling for None and non-empty request hooks. Add a regression test using the project's style."},
    {"id":"PK01","repo":"packaging","path":"src/packaging/utils.py","test_path":"tests/test_utils.py","test_name":"test_long_horizon_pk01","match":"while \"--\" in value:","broken":"if False:","test":"""from packaging.utils import canonicalize_name

def test_long_horizon_pk01():
    assert canonicalize_name("Acme._--Tools") == "acme-tools"
    assert canonicalize_name("acme....tools") == "acme-tools"
""","upstream_test":"tests/test_utils.py -k canonicalize_name","prompt":"Restore PEP 503 name normalization: lowercase the distribution name, map dot and underscore separators to hyphens, and collapse repeated hyphens. Keep validation semantics unchanged. Add regression coverage for mixed and repeated separators."},
    {"id":"PK02","repo":"packaging","path":"src/packaging/utils.py","test_path":"tests/test_utils.py","test_name":"test_long_horizon_pk02","match":"return str(_TrimmedRelease(version) if strip_trailing_zero else version)","broken":"return str(_TrimmedRelease(version))","test":"""from packaging.utils import canonicalize_version

def test_long_horizon_pk02():
    assert canonicalize_version("1.4.0.0", strip_trailing_zero=False) == "1.4.0.0"
    assert canonicalize_version("1.4.0.0", strip_trailing_zero=True) == "1.4"
""","upstream_test":"tests/test_utils.py -k canonicalize_version","prompt":"Fix `canonicalize_version` so `strip_trailing_zero=False` preserves the complete release segment, while the default continues stripping trailing zero components. Preserve invalid-version behavior and add a regression test."},
    {"id":"CL01","repo":"click","path":"src/click/termui.py","test_path":"tests/test_termui.py","test_name":"test_long_horizon_cl01","match":"result = value_proc(value)","broken":"result = value","test":"""import click

def test_long_horizon_cl01(monkeypatch):
    monkeypatch.setattr(click.termui, "_readline_prompt", lambda *args, **kwargs: "")
    assert click.prompt("Count", default="7", type=int) == 7
    assert type(click.prompt("Count", default="7", type=int)) is int
""","upstream_test":"tests/test_termui.py -k prompt","prompt":"Fix `click.prompt` so a provided default value passes through the same conversion path as typed input. Keep the returned value typed (for example, an integer for type=int), and add a regression test using Click's existing test conventions."},
    {"id":"CL02","repo":"click","path":"src/click/termui.py","test_path":"tests/test_termui.py","test_name":"test_long_horizon_cl02","match":"value = _readline_prompt(visible_prompt_func, prompt, err).lower().strip()","broken":"value = _readline_prompt(visible_prompt_func, prompt, err).lower()","test":"""import click

def test_long_horizon_cl02(monkeypatch):
    values = iter(["  YES  "])
    monkeypatch.setattr(click.termui, "_readline_prompt", lambda *args, **kwargs: next(values))
    assert click.confirm("Continue?") is True
""","upstream_test":"tests/test_termui.py -k confirm","prompt":"Improve `click.confirm` input normalization so surrounding whitespace around yes/no answers is ignored, while invalid answers still follow the normal retry behavior. Add a regression test in the project's established test style."},
    {"id":"AT01","repo":"attrs","path":"src/attr/_funcs.py","test_path":"tests/test_funcs.py","test_name":"test_long_horizon_at01","match":"if value_serializer is not None:\n            v = value_serializer(inst, a, v)\n\n        if recurse is True:","broken":"if value_serializer is not None:\n            v = value_serializer(inst, a, v)\n\n        if False:","test":"""import attr

def test_long_horizon_at01():
    @attr.define
    class Child:
        value: int
    @attr.define
    class Parent:
        child: Child
    assert attr.asdict(Parent(Child(8))) == {"child": {"value": 8}}
""","upstream_test":"tests/test_funcs.py -k asdict","prompt":"Restore recursive conversion in `attrs.asdict` for nested attrs instances and supported collections, without changing shallow mode or filter behavior. Add a focused regression test in the existing attrs test suite."},
    {"id":"AT02","repo":"attrs","path":"src/attr/converters.py","test_path":"tests/test_converters.py","test_name":"test_long_horizon_at02","match":"val = val.lower()","broken":"val = val.strip().lower()","reference":"val = val.strip().lower()","test":"""import pytest
from attr.converters import to_bool

@pytest.mark.parametrize(("value", "expected"), [(" true ", True), (" OFF ", False), (" 1 ", True), (" 0 ", False)])
def test_long_horizon_at02(value, expected):
    assert to_bool(value) is expected
""","upstream_test":"tests/test_converters.py -k TestToBool","prompt":"Extend `attrs.converters.to_bool` to tolerate leading/trailing whitespace in environment-style string values, while preserving case-insensitive recognized tokens and rejecting unknown values. Add parameterized regression coverage."},
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def unified_patch(before, after, relpath):
    lines = difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                 fromfile="a/" + relpath, tofile="b/" + relpath, n=3)
    return "".join(lines)


def run(args, cwd=None, check=True):
    return subprocess.run(args, cwd=cwd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-cache", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=Path(__file__).parent)
    args = ap.parse_args()
    output = args.output.resolve()
    cases = output / "cases"
    cases.mkdir(parents=True, exist_ok=True)
    repo_meta = {}
    for key, (origin, license_name, dirname) in REPOS.items():
        repo = args.repo_cache / dirname
        revision = run(["git", "rev-parse", "HEAD"], cwd=repo).strip()
        if revision != PINNED_REVISIONS[key]:
            raise SystemExit(f"{key} must be checked out at frozen revision {PINNED_REVISIONS[key]}, got {revision}")
        if run(["git", "status", "--porcelain"], cwd=repo).strip():
            raise SystemExit(f"Refusing dirty upstream cache: {repo}")
        repo_meta[key] = {"origin": f"https://github.com/{origin}.git", "revision": revision, "license": license_name}
    catalog = []
    for task in TASKS:
        repo_name = task["repo"]
        repo = args.repo_cache / REPOS[repo_name][2]
        file = repo / task["path"]
        test_file = repo / task["test_path"]
        original = file.read_text()
        original_tests = test_file.read_text()
        if original.count(task["match"]) != 1:
            raise SystemExit(f"Expected one source anchor for {task['id']}")
        case = cases / task["id"]
        case.mkdir(parents=True, exist_ok=True)
        (case / "challenge_test.py").write_text(task["test"])
        (case / "upstream_test.txt").write_text(task["upstream_test"] + "\n")
        if task.get("reference"):
            file.write_text(original)
            starter_diff = ""
            reference_text = original.replace(task["match"], task["reference"], 1)
            if task["match"] == task["reference"]:
                raise SystemExit(f"No-op feature reference for {task['id']}")
            file.write_text(reference_text)
            test_text = original_tests.rstrip() + "\n\n\n" + task["test"].rstrip() + "\n"
            test_file.write_text(test_text)
            reference_diff = (unified_patch(original, reference_text, task["path"])
                              + unified_patch(original_tests, test_text, task["test_path"]))
        else:
            starter_text = original.replace(task["match"], task["broken"], 1)
            file.write_text(starter_text)
            starter_diff = run(["git", "diff", "--", task["path"]], cwd=repo)
            test_text = original_tests.rstrip() + "\n\n\n" + task["test"].rstrip() + "\n"
            reference_diff = (unified_patch(starter_text, original, task["path"])
                              + unified_patch(original_tests, test_text, task["test_path"]))
        file.write_text(original)
        test_file.write_text(original_tests)
        (case / "starter.patch").write_text(starter_diff)
        (case / "reference.patch").write_text(reference_diff)
        case_record = {"id":task["id"],"repo":repo_name,"repository":repo_meta[repo_name],"source_file":task["path"],"test_file":task["test_path"],"required_test_name":task["test_name"],
                       "prompt":task["prompt"],"upstream_targeted_tests":task["upstream_test"],
                       "scoring":"hidden regression suite and the repository's targeted upstream tests pass; runtime/patch telemetry retained",
                       "challenge_test":"challenge_test.py","starter_patch_sha256":sha256(starter_diff.encode()),
                       "reference_patch_sha256":sha256(reference_diff.encode()),"negative_control":"upstream buggy starter; must fail challenge test"}
        (case / "task.json").write_text(json.dumps(case_record, indent=2, sort_keys=True) + "\n")
        catalog.append(case_record)
    manifest = {"suite":"long_horizon_v1","status":"frozen pre-score task definitions; no scored trials executed","tasks":catalog}
    (output / "tasks.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {len(catalog)} task definitions across {len(repo_meta)} pinned real repositories.")


if __name__ == "__main__":
    main()
