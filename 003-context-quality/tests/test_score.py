import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from score import content_equal, parse


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
