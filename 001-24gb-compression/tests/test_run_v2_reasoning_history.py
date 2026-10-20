import json

from src import run_v2


def test_reasoning_content_is_preserved_in_tool_followup(monkeypatch):
    tasks = json.loads((run_v2.ROOT / "benchmark/tasks.json").read_text())
    task = next(item for item in tasks if item["id"] == "TO01")
    requests = []

    def fake_request(api, payload):
        requests.append(payload)
        if len(requests) == 1:
            message = {
                "role": "assistant",
                "content": "",
                "reasoning_content": "I should read the requested file, then stop.",
                "tool_calls": [{
                    "id": "call-read-1",
                    "type": "function",
                    "function": {"name": "read", "arguments": json.dumps({"path": "<WORKDIR>/README.md"})},
                }],
            }
            finish_reason = "tool_calls"
        else:
            message = {"role": "assistant", "content": '{"done":true}'}
            finish_reason = "stop"
        return {
            "choices": [{"index": 0, "finish_reason": finish_reason, "message": message}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "timings": {"prompt_ms": 20, "predicted_ms": 30},
        }

    monkeypatch.setattr(run_v2, "request", fake_request)
    result = run_v2.interact("http://local/v1", "test-model", "qwen", task, seed=123)

    assert len(requests) == 2
    replayed = requests[1]["messages"][1]
    assert replayed["role"] == "assistant"
    assert replayed["reasoning_content"] == "I should read the requested file, then stop."
    assert result["tool_trace"][0]["ok"] is True
    assert run_v2.score(task, result["content"], result["tool_trace"])
