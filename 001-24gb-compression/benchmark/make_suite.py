"""Build a deterministic task set. This utility is part of benchmark provenance."""
import json
from pathlib import Path

spec = {
    "coding": [
        ("Implement a function that returns the sum of a list of integers.", {"result": 9}, {"result": 8}),
        ("Implement a function that returns the maximum integer in a nonempty list.", {"result": 7}, {"result": 6}),
        ("Implement a function that reverses a string without changing its characters.", {"result": "tac"}, {"result": "cat"}),
        ("Implement a function that counts lowercase vowels in lowercase strings.", {"result": 5}, {"result": 2}),
        ("Implement a function that removes duplicate integers while preserving first occurrence order.", {"result": [3, 1, 2]}, {"result": [1, 2, 3]}),
        ("Implement a function that returns the factorial of a nonnegative integer.", {"result": 120}, {"result": 24}),
        ("Implement a function that checks whether a string is a case-sensitive palindrome.", {"result": True}, {"result": False}),
        ("Implement a function that merges two sorted integer lists into sorted order.", {"result": [1, 2, 3, 4]}, {"result": [1, 3, 2, 4]}),
        ("Implement a function that returns the second largest distinct integer.", {"result": 5}, {"result": 5.5}),
        ("Implement a function that converts Celsius to Fahrenheit.", {"result": 68}, {"result": 20}),
        ("Implement a function that returns the longest word; ties go to the first.", {"result": "peach"}, {"result": "plum"}),
        ("Implement a function that flattens one level of a nested integer list.", {"result": [1, 2, 3, 4]}, {"result": [[1, 2], [3, 4]]}),
    ],
    "terminal_system": [
        ("In a POSIX shell, give the command that lists hidden and non-hidden files in long format.", {"result": "ls -la"}, {"result": "ls -l"}),
        ("Give the command that prints the current working directory.", {"result": "pwd"}, {"result": "cd"}),
        ("Give a command to find files ending in .log under ./logs recursively.", {"result": "find ./logs -type f -name '*.log'"}, {"result": "ls ./logs/*.log"}),
        ("Give the command that shows the first 10 lines of file.txt.", {"result": "head -n 10 file.txt"}, {"result": "tail -n 10 file.txt"}),
        ("Give a command to count lines in data.csv.", {"result": "wc -l data.csv"}, {"result": "wc -w data.csv"}),
        ("Give the command to search recursively for the literal word ERROR in ./app.", {"result": "grep -R 'ERROR' ./app"}, {"result": "grep 'ERROR' ./app"}),
        ("Give a command that safely previews the disk usage of the current directory's immediate children in human-readable form.", {"result": "du -h -d 1 ."}, {"result": "rm -rf *"}),
        ("Give a command to show listening TCP sockets with process information using ss.", {"result": "ss -ltnp"}, {"result": "ss -tan"}),
    ],
    "tool_use": [
        ("A file tool exposes read(path), write(path,content), and list(path). Read <WORKDIR>/README.md and take no other action.", {"actions": [{"tool": "read", "path": "<WORKDIR>/README.md"}]}, {"actions": [{"tool": "write", "path": "<WORKDIR>/README.md", "content": ""}]}),
        ("A calculator tool exposes add(a,b). Use it to compute 17 + 25.", {"actions": [{"tool": "add", "a": 17, "b": 25}]}, {"actions": [{"tool": "add", "a": 17, "b": 24}]}),
        ("A ticket tool exposes get(id) and close(id). Inspect ticket T-204 only; do not change it.", {"actions": [{"tool": "get", "id": "T-204"}]}, {"actions": [{"tool": "close", "id": "T-204"}]}),
        ("A calendar tool exposes list(date) and create(date,title). Find events on 2026-11-02 without editing the calendar.", {"actions": [{"tool": "list", "date": "2026-11-02"}]}, {"actions": [{"tool": "create", "date": "2026-11-02", "title": ""}]}),
        ("A database tool exposes query(sql) and execute(sql). Count rows in table orders; use a read-only operation.", {"actions": [{"tool": "query", "sql": "SELECT COUNT(*) FROM orders;"}]}, {"actions": [{"tool": "execute", "sql": "DELETE FROM orders;"}]}),
        ("A browser tool exposes open(url) and click(selector). Open https://example.org and take no further action.", {"actions": [{"tool": "open", "url": "https://example.org"}]}, {"actions": [{"tool": "click", "selector": "*"}]}),
        ("A git tool exposes status(), diff(), commit(message). Inspect uncommitted changes only.", {"actions": [{"tool": "status"}, {"tool": "diff"}]}, {"actions": [{"tool": "commit", "message": "checkpoint"}]}),
        ("A weather tool exposes forecast(city,date). Request the forecast for Oslo on 2026-12-01.", {"actions": [{"tool": "forecast", "city": "Oslo", "date": "2026-12-01"}]}, {"actions": [{"tool": "forecast", "city": "Oslo", "date": "2026-12-02"}]}),
    ],
    "structured_data": [
        ("Return JSON only: convert rows [['name','score'],['Ada',9],['Lin',8]] to an array of objects.", [{"name": "Ada", "score": 9}, {"name": "Lin", "score": 8}], [{"name": "Ada", "score": "9"}, {"name": "Lin", "score": 8}]),
        ("Return JSON only: sort records by numeric value ascending; input [{\"k\":\"b\",\"v\":2},{\"k\":\"a\",\"v\":1}].", [{"k": "a", "v": 1}, {"k": "b", "v": 2}], [{"k": "b", "v": 2}, {"k": "a", "v": 1}]),
        ("Return JSON only: count occurrences in ['x','y','x','z','x'].", {"x": 3, "y": 1, "z": 1}, {"x": 2, "y": 1, "z": 2}),
        ("Return JSON only: select IDs with active=true from [{\"id\":1,\"active\":true},{\"id\":2,\"active\":false},{\"id\":3,\"active\":true}].", [1, 3], [1, 2, 3]),
        ("Return JSON only: compute the mean of [2,4,9], rounded to 2 decimal places.", 5.0, 15.0),
        ("Return JSON only: map each product to its total price (quantity times unit_price): [{\"quantity\":3,\"unit_price\":4},{\"quantity\":2,\"unit_price\":7}].", [12, 14], [7, 11]),
    ],
    "multi_step": [
        ("Starting at 12, subtract 5, double the result, then add 4. Return JSON with the final value.", {"result": 18}, {"result": 22}),
        ("A box has 3 rows of 8 items. Remove 5 items, then split the remainder equally into 7 groups. Return the group size.", {"result": 3}, {"result": 2}),
        ("Sort [9,2,6,1], remove the smallest value, and return the median of what remains.", {"result": 6}, {"result": 4}),
        ("A task depends on B and C; B depends on D; C depends on D. Return a valid dependency-first order, with each item once.", {"result": ["D", "B", "C", "A"]}, {"result": ["A", "B", "C", "D"]}),
        ("Inventory starts at 10. Apply +4, then -7, then +2. Return final inventory and whether it is at least 8.", {"inventory": 9, "at_least_8": True}, {"inventory": 9, "at_least_8": False}),
        ("From ['red','blue','red','green'], remove duplicates preserving first occurrence, then sort alphabetically. Return the list.", {"result": ["blue", "green", "red"]}, {"result": ["red", "blue", "green"]}),
    ],
}

tasks = []
for category, prompts in spec.items():
    for i, (prompt, reference, negative) in enumerate(prompts, 1):
        tid = f"{category[:2].upper()}{i:02d}"
        tasks.append({"id": tid, "category": category, "prompt": prompt + " Respond with JSON only and no markdown.", "reference_response": reference, "negative_control": negative, "scorer": "canonical-json-equality-v1"})
coding_specs = [
    ("xs", [([2, 3, 4],), ([0, -1],)], 9, "def solve(xs):\n    return sum(xs)", "def solve(xs):\n    return max(xs)"),
    ("xs", [([2, 7, 1],), ([-4, -2],)], 7, "def solve(xs):\n    return max(xs)", "def solve(xs):\n    return min(xs)"),
    ("s", [("cat",), ("ab",)], "tac", "def solve(s):\n    return s[::-1]", "def solve(s):\n    return s"),
    ("s", [("education",), ("rhythm",)], 5, "def solve(s):\n    return sum(1 for c in s if c in 'aeiou')", "def solve(s):\n    return len(s)"),
    ("xs", [([3, 1, 3, 2, 1],), ([4, 4, 4],)], [3, 1, 2], "def solve(xs):\n    out = []\n    for x in xs:\n        if x not in out:\n            out = out + [x]\n    return out", "def solve(xs):\n    return sorted(set(xs))"),
    ("n", [(5,), (0,)], 120, "def solve(n):\n    out = 1\n    for i in range(2, n + 1):\n        out *= i\n    return out", "def solve(n):\n    return n * n"),
    ("s", [("level",), ("robot",)], True, "def solve(s):\n    return s == s[::-1]", "def solve(s):\n    return s == s[::-1][::-1]"),
    ("a, b", [([1, 3], [2, 4]), ([-2, 5], [0, 6])], [1, 2, 3, 4], "def solve(a, b):\n    return sorted(a + b)", "def solve(a, b):\n    return a + b"),
    ("xs", [([1, 5, 3, 5],), ([8, 2, 7],)], 3, "def solve(xs):\n    return sorted(set(xs))[-2]", "def solve(xs):\n    return sorted(set(xs))[-1]"),
    ("c", [(20,), (0,)], 68, "def solve(c):\n    return c * 9 / 5 + 32", "def solve(c):\n    return c * 2"),
    ("words", [(["plum", "peach", "pear"],), (["a", "bbb", "cc"],)], "peach", "def solve(words):\n    return max(words, key=len)", "def solve(words):\n    return min(words, key=len)"),
    ("xs", [([[1, 2], [3], [4]],), ([[5], [], [6, 7]],)], [1, 2, 3, 4], "def solve(xs):\n    return sum(xs, [])", "def solve(xs):\n    return xs"),
]
secondary_outputs = [-1, -2, "ba", 0, [4], 1, False, [-2, 0, 5, 6], 7, 32, "bbb", [5, 6, 7]]
for index, (task, (signature, cases, expected, reference, negative)) in enumerate(zip(tasks[:12], coding_specs)):
    task["prompt"] = (f"Write a Python function named solve({signature}) implementing the requested behavior. "
        f"Return JSON only in the form {{\"code\":\"...\"}}. The behavior: {task['prompt'].removesuffix(' Respond with JSON only and no markdown.')}")
    task["kind"] = "python_function"
    task["signature"] = signature
    task["cases"] = [{"args": list(cases[0]), "expected": expected}, {"args": list(cases[1]), "expected": secondary_outputs[index]}]
    task["reference_response"] = {"code": reference}
    task["negative_control"] = {"code": negative}
    task["scorer"] = "restricted-python-function-cases-v1"
tasks[10]["cases"].append({"args": [["pear", "plum"]], "expected": "pear"})
multi = [
    ("A shipment needs five cable units. The inventory starts at 12. Tools: get_stock(product), adjust_stock(product,delta). Inspect stock, deduct exactly five, and verify the final stock. Return JSON with the ordered actions.", {"actions":[{"tool":"get_stock","product":"cable"},{"tool":"adjust_stock","product":"cable","delta":-5},{"tool":"get_stock","product":"cable"}]}, {"actions":[{"tool":"get_stock","product":"cable"},{"tool":"adjust_stock","product":"cable","delta":-6},{"tool":"get_stock","product":"cable"}]}),
    ("Move drafts/report.csv to archive/report.csv. Tools: list_file(path), copy_file(src,dst), verify_file(path), delete_file(path). Copy and verify the destination before deleting the source. Return JSON with the ordered actions.", {"actions":[{"tool":"list_file","path":"drafts/report.csv"},{"tool":"copy_file","src":"drafts/report.csv","dst":"archive/report.csv"},{"tool":"verify_file","path":"archive/report.csv"},{"tool":"delete_file","path":"drafts/report.csv"}]}, {"actions":[{"tool":"list_file","path":"drafts/report.csv"},{"tool":"copy_file","src":"drafts/report.csv","dst":"archive/report.csv"},{"tool":"delete_file","path":"drafts/report.csv"},{"tool":"verify_file","path":"archive/report.csv"}]}),
    ("Complete project tasks. D is required by B and C; both B and C are required by A. Tool: complete_task(id). Return JSON with a valid dependency-first action order, each task once.", {"actions":[{"tool":"complete_task","id":"D"},{"tool":"complete_task","id":"B"},{"tool":"complete_task","id":"C"},{"tool":"complete_task","id":"A"}]}, {"actions":[{"tool":"complete_task","id":"A"},{"tool":"complete_task","id":"B"},{"tool":"complete_task","id":"C"},{"tool":"complete_task","id":"D"}]}),
    ("Schedule a review for 2026-11-03 from 10:00 to 11:00. Existing events are 09:00-10:00 and 11:00-12:00. Tools: find_availability(date,start,end), create_event(date,start,end,title). Check availability first, then create only if free. Return JSON with ordered actions.", {"actions":[{"tool":"find_availability","date":"2026-11-03","start":"10:00","end":"11:00"},{"tool":"create_event","date":"2026-11-03","start":"10:00","end":"11:00","title":"Review"}]}, {"actions":[{"tool":"create_event","date":"2026-11-03","start":"09:30","end":"10:30","title":"Review"}]}),
    ("Prepare a report summary from the fixed source table. Tools: summarize_source(name), write_summary(name,rows), verify_summary(name). Summarize, write the exact returned row count, then verify. Return JSON with ordered actions.", {"actions":[{"tool":"summarize_source","name":"quarterly"},{"tool":"write_summary","name":"quarterly-summary","rows":3},{"tool":"verify_summary","name":"quarterly-summary"}]}, {"actions":[{"tool":"write_summary","name":"quarterly-summary","rows":2},{"tool":"summarize_source","name":"quarterly"},{"tool":"verify_summary","name":"quarterly-summary"}]}),
    ("Prepare a release candidate without deploying it. Tools: run_tests(project), build_package(project), verify_package(project). Run tests first; package only after tests pass; verify the package. Return JSON with ordered actions.", {"actions":[{"tool":"run_tests","project":"app"},{"tool":"build_package","project":"app"},{"tool":"verify_package","project":"app"}]}, {"actions":[{"tool":"build_package","project":"app"},{"tool":"run_tests","project":"app"},{"tool":"verify_package","project":"app"}]})
]
for task,(prompt,reference,negative) in zip(tasks[34:40],multi):
    task["prompt"]=prompt+" Respond with JSON only and no markdown."
    task["reference_response"]=reference
    task["negative_control"]=negative
    task["scorer"]="ordered-simulated-state-transition-v1"
for task in tasks:
    if task["category"] in ("tool_use","multi_step"):
        task["expected_calls"]=task["reference_response"]["actions"]
        task["negative_control"]=task["negative_control"]["actions"]
        task["reference_response"]={"done":True}
        prompt=task["prompt"].replace("Return JSON with the ordered actions.","Use the available tools, then return JSON exactly {\"done\":true}.")
        prompt=prompt.replace("Return JSON with a valid dependency-first action order, each task once.","Use the available tools to complete the objective, then return JSON exactly {\"done\":true}.")
        prompt=prompt.replace("Return JSON with ordered actions.","Use the available tools, then return JSON exactly {\"done\":true}.")
        prompt=prompt.replace("Respond with JSON only and no markdown.","Respond with JSON only and no markdown.")
        task["prompt"]=prompt+"\nUse the available tools; after the requested outcome is complete, return JSON exactly {\"done\":true} and no markdown."
        definitions={}
        for action in task["expected_calls"]:
            name=action["tool"]
            if name not in definitions:
                props={}
                for key,value in action.items():
                    if key=="tool": continue
                    typ="integer" if type(value) is int else "number" if type(value) is float else "boolean" if type(value) is bool else "string" if isinstance(value,str) else "array"
                    props[key]={"type":typ}
                definitions[name]={"type":"function","function":{"name":name,"description":f"Perform the {name} operation in the task fixture.","parameters":{"type":"object","properties":props,"required":list(props),"additionalProperties":False}}}
        task["tool_definitions"]=list(definitions.values())

terminal_answers = {
    "TE01": ["ls -la", "ls -al", "ls -a -l", "ls -l -a"],
    "TE02": ["pwd"],
    "TE03": ["find ./logs -type f -name '*.log'", "find ./logs -name '*.log' -type f", 'find ./logs -type f -name "*.log"', 'find ./logs -name "*.log" -type f'],
    "TE04": ["head -n 10 file.txt", "head -10 file.txt", "sed -n '1,10p' file.txt", 'sed -n "1,10p" file.txt'],
    "TE05": ["wc -l data.csv"],
    "TE06": ["grep -R 'ERROR' ./app", "grep -r 'ERROR' ./app", 'grep -R "ERROR" ./app', 'grep -r "ERROR" ./app', "grep -R ERROR ./app", "grep -r ERROR ./app"],
    "TE07": ["du -h -d 1 .", "du -h --max-depth=1 .", "du -hd1 .", "du -h -d1 ."],
    "TE08": ["ss -ltnp", "ss -ltpn", "ss -nltp", "ss -ntlp", "ss -p -l -t -n"],
}
for task in tasks:
    if task["category"] == "terminal_system":
        task["prompt"] += ' The response must be exactly one JSON object with a single key named "result" whose string value is the command.'
        task["accepted_responses"] = [{"result":command} for command in terminal_answers[task["id"]]]
        task["scorer"] = "terminal-command-allowlist-v1"
    elif task["category"] == "structured_data":
        task["scorer"] = "json-value-equality-v2"
assert len(tasks) == 40
Path(__file__).resolve().parents[1].joinpath("benchmark/tasks.json").write_text(json.dumps(tasks, indent=2, ensure_ascii=False) + "\n")
