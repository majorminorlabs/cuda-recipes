import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "code"))
from score import content_equal, parse


class DatasetIdentityTests(unittest.TestCase):
    def test_questions_and_planting_map_use_integrated_ids(self):
        root = Path(__file__).resolve().parents[2]
        questions = [json.loads(line) for line in (root / "DATA/code/questions.jsonl").read_text().splitlines()]
        self.assertEqual(len(questions), 180)
        self.assertTrue(all(q["question_id"].startswith("003-code-") for q in questions))
        map_path = root / "_internal/code/planting-map.json"
        if map_path.exists():
            planting = json.loads(map_path.read_text())
            linked = [event for event in planting["facts"] if event.get("question_id")]
            self.assertEqual(len(linked), 846)
            self.assertTrue(all(event["question_id"].startswith("003-code-") for event in linked))

    def test_single_retrieval_fractions_match_nominal_bands_and_do_not_collide(self):
        root = Path(__file__).resolve().parents[2]
        questions = [json.loads(line) for line in (root / "DATA/code/questions.jsonl").read_text().splitlines()]
        map_path = root / "_internal/code/planting-map.json"
        planting = json.loads(map_path.read_text())["facts"] if map_path.exists() else None
        positions = {"early": lambda f: f < 0.34,
                     "middle": lambda f: 0.33 <= f <= 0.67,
                     "late": lambda f: f > 0.66}
        rows = [q for q in questions if q["task_type"] == "single_retrieval"]
        self.assertEqual(len(rows), 45)
        for q in rows:
            self.assertEqual(len(q["fact_fractions"]), 1, q["question_id"])
            fraction = q["fact_fractions"][0]
            self.assertTrue(positions[q["position"]](fraction),
                            f"{q['question_id']} labeled {q['position']} at {fraction:.6f}")
            if planting is None:
                document = (root / "DATA/code/documents" / (q["doc_id"] + ".txt")).read_text()
                target, decoy = q["reference"]["value"], q["negative_control"]["value"]
                self.assertIn(target, document)
                self.assertIn(decoy, document)
                self.assertNotEqual(document.index(target), document.index(decoy))
                continue
            planted = [e for e in planting if e.get("question_id") == q["question_id"]
                       and e["role"] in ("single_target", "single_decoy")]
            self.assertEqual(len(planted), 2, q["question_id"])
            self.assertNotEqual(planted[0]["fraction"], planted[1]["fraction"],
                                f"same-question target/decoy collision: {q['question_id']}")


class ParseTests(unittest.TestCase):
    def test_bare_object(self): self.assertEqual(parse('{"answer":"a"}'), {"answer":"a"})
    def test_json_fence(self): self.assertEqual(parse('```json\n{"answer":"a"}\n```'), {"answer":"a"})
    def test_plain_fence(self): self.assertEqual(parse('```\n{"answer":"a"}\n```'), {"answer":"a"})
    def test_last_top_level_object(self): self.assertEqual(parse('analysis {"draft":1}\nfinal {"answer":"b"}'), {"answer":"b"})
    def test_nested_object_remains_with_its_top_level_parent(self): self.assertEqual(parse('prefix {"outer":{"inner":1}}'), {"outer":{"inner":1}})
    def test_no_json(self): self.assertIsNone(parse("no structured answer here"))


class MultiRetrievalContentTests(unittest.TestCase):
    ref = {"answers": ["alpha", "beta", "gamma", "delta"]}
    def test_string_list(self): self.assertTrue(content_equal({"answers": [" ALPHA ", "beta", "gamma", "delta"]}, self.ref, "multi_retrieval"))
    def test_object_list_excludes_entity(self): self.assertTrue(content_equal({"answers": [{"shoal":"A Name", "tide_phrase":"alpha"}, {"shoal":"B Name", "tide_phrase":"beta"}, {"shoal":"C Name", "tide_phrase":"gamma"}, {"shoal":"D Name", "tide_phrase":"delta"}]}, self.ref, "multi_retrieval"))
    def test_mixed(self): self.assertTrue(content_equal({"answers": ["alpha", {"shoal":"B", "tide_phrase":"beta"}, "gamma", {"name":"D", "value":"delta"}]}, self.ref, "multi_retrieval"))
    def test_wrong_value(self): self.assertFalse(content_equal({"answers": ["alpha", "beta", "gamma", "wrong"]}, self.ref, "multi_retrieval"))
    def test_missing_item(self): self.assertFalse(content_equal({"answers": ["alpha", "beta", "gamma"]}, self.ref, "multi_retrieval"))
    def test_extra_item(self): self.assertFalse(content_equal({"answers": ["alpha", "beta", "gamma", "delta", "extra"]}, self.ref, "multi_retrieval"))


if __name__ == "__main__": unittest.main()
