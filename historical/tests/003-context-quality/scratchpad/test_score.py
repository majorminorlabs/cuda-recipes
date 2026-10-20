import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"/"scratchpad"))
sys.path.insert(0,str(ROOT/"scripts"))
import run as scratchrun
import importlib.util
from collections import defaultdict
spec=importlib.util.spec_from_file_location("scratchpad_score",ROOT/"scripts"/"scratchpad"/"score.py")
score=importlib.util.module_from_spec(spec); spec.loader.exec_module(score)

class ScratchpadScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q=json.loads(next(x for x in (ROOT/"DATA/questions.jsonl").read_text().splitlines() if '"task_type": "aggregation"' in x))
        cls.events=score.load_events("prose")
        cls.targets,cls.decoys=score.events_for("prose",cls.q,cls.events)
        cls.doc=(ROOT/"DATA/documents"/f"{cls.q['doc_id']}.txt").read_text()

    def response(self,lines,count=None):
        tally="\n".join(f"found {i}: {line}" for i,line in enumerate(lines,1))
        return tally+"\n{"+f'"count": {self.q["reference"]["count"] if count is None else count}'+'}'

    def score_text(self,text,finish="stop"):
        return score.score_one("prose","test",self.q,text,finish,self.doc,self.events)[0]

    def target_lines(self): return [e["text"] for e in self.targets]

    def test_all_planted_lines_perfect(self):
        row=self.score_text(self.response(self.target_lines()))
        self.assertEqual(row["failure_class"],"correct")
        self.assertEqual(row["matched_planted"],len(self.targets))
        self.assertEqual(row["missed_planted"],0)

    def test_one_item_removed_is_missed_items(self):
        row=self.score_text(self.response(self.target_lines()[1:]))
        self.assertEqual(row["failure_class"],"missed_items")

    def test_decoy_added_is_decoy_included(self):
        decoy=next(e["text"] for e in self.decoys)
        row=self.score_text(self.response(self.target_lines()[1:]+[decoy]))
        self.assertEqual(row["failure_class"],"decoy_included")
        self.assertGreater(row["matched_decoy"],0)
        self.assertGreater(row["missed_planted"],0)

    def test_wrong_final_count_on_correct_list_is_miscount(self):
        row=self.score_text(self.response(self.target_lines(),count=self.q["reference"]["count"]+1))
        self.assertEqual(row["failure_class"],"miscount_of_list")

    def test_name_only_repeated_four_times_gets_no_planted_credit(self):
        name=self.q["entity_key"][0]
        row,items,_,_=score.score_one("prose","test",self.q,self.response([name]*4),"stop",self.doc,self.events)
        self.assertEqual(row["matched_planted"],0)
        self.assertEqual(row["extra_items"],4)
        self.assertTrue(all(x["match_class"]=="extra_item" for x in items))

    def test_full_sentence_quote_matches_exactly_one_target(self):
        row,items,_,_=score.score_one("prose","test",self.q,self.response([self.target_lines()[0]]),"stop",self.doc,self.events)
        self.assertEqual(row["matched_planted"],1)
        self.assertEqual(sum(x["match_class"]=="planted" for x in items),1)

    def test_paragraph_containing_sentence_matches_target(self):
        paragraph="A paragraph opening. "+self.target_lines()[0]+" A paragraph ending."
        row,items,_,_=score.score_one("prose","test",self.q,self.response([paragraph]),"stop",self.doc,self.events)
        self.assertEqual(row["matched_planted"],1)
        self.assertEqual(items[0]["match_class"],"planted")

    def test_markdown_bullets_numbering_quotes_and_backticks_parse(self):
        line=self.target_lines()[0]
        content=f"- **found 1:** `'{line}'`\n{{\"count\": {self.q['reference']['count']}}}"
        row,items,_,_=score.score_one("prose","test",self.q,content,"stop",self.doc,self.events)
        self.assertEqual(row["listed_items"],1)
        self.assertEqual(row["matched_planted"],1)
        self.assertEqual(items[0]["listed_text"],line)

    def test_label_free_exact_source_lines_are_parsed_as_tally(self):
        text="\n".join(self.target_lines())+f'\n{{"count": {self.q["reference"]["count"]}}}'
        row,items,_,_=score.score_one("prose","test",self.q,text,"stop",self.doc,self.events)
        self.assertEqual(row["matched_planted"],len(self.targets))
        self.assertEqual(row["failure_class"],"correct")
        self.assertEqual(row["followed_format"],0)

    def test_found_code_snippet_includes_following_call_line(self):
        q=dict(self.q); q["reference"]={"count":1}; q["entity_key"]=["lookup_xyz"]
        events=[{"doc_id":q["doc_id"],"role":"aggregation_call","key":"lookup_xyz","question_id":q["question_id"],"event_id":"call-1","source_snippet":"def call_abc():\n    return lookup_xyz()"}]
        content='found 1: def call_abc():\n    return lookup_xyz()\n{"count": 1}'
        row,items,_,_=score.score_one("code","test",q,content,"stop",content,events)
        self.assertEqual(row["matched_planted"],1)
        self.assertEqual(items[0]["match_class"],"planted")
        self.assertEqual(row["followed_format"],1)

    def test_literal_found_n_prefix_is_extracted_and_followed_flagged(self):
        line=self.target_lines()[0]
        content=f"found N: {line}\n{{\"count\": {self.q['reference']['count']}}}"
        row,items,_,_=score.score_one("prose","test",self.q,content,"stop",self.doc,self.events)
        self.assertEqual(row["listed_items"],1)
        self.assertEqual(row["followed_format"],1)

    def test_flags_repetition_loop_at_three_repeated_lines(self):
        line=self.target_lines()[0]
        row=self.score_text(self.response([line,line,line]))
        self.assertEqual(row["repetition_loop"],1)
        self.assertEqual(row["followed_format"],1)

    def test_partial_matching_multiple_remaining_targets_is_ambiguous(self):
        q=dict(self.q); key=q["entity_key"][0]
        first=f"The purser mentioned {key} while the ship's stores were being tallied."
        second=f"The purser mentioned {key} while the ship's stores were being counted."
        events=[{"doc_id":q["doc_id"],"role":"aggregation_target","key":key,"text":first},
                {"doc_id":q["doc_id"],"role":"aggregation_target","key":key,"text":second}]
        q["reference"]={"count":2}
        partial=f"The purser mentioned {key} while the ship's stores were being"
        row,items,_,_=score.score_one("prose","test",q,self.response([partial]),"stop",partial,events)
        self.assertEqual(row["ambiguous"],1)
        self.assertEqual(row["matched_planted"],0)
        self.assertEqual(items[0]["match_class"],"ambiguous")

    def test_identical_planted_lines_are_consumed_one_to_one(self):
        q=dict(self.q); q["reference"]={"count":3}
        repeated="return lookup_x()"
        events=[{"doc_id":q["doc_id"],"role":"aggregation_target","key":q["entity_key"][0],"text":repeated,"event_id":str(i)} for i in range(3)]
        text="\n".join(f"found {i}: {repeated}" for i in range(1,4))+ '\n{"count": 3}'
        row,items,_,_=score.score_one("prose","test",q,text,"stop",repeated,events)
        self.assertEqual((row["matched_planted"],row["ambiguous"],row["extra_items"]),(3,0,0))
        self.assertEqual([x["match_class"] for x in items],["planted"]*3)
        self.assertEqual(row["repetition_loop"],0)

    def test_identical_planted_lines_listed_six_times_is_loop(self):
        q=dict(self.q); q["reference"]={"count":3}
        repeated="return lookup_x()"
        events=[{"doc_id":q["doc_id"],"role":"aggregation_target","key":q["entity_key"][0],"text":repeated,"event_id":str(i)} for i in range(3)]
        text="\n".join(f"found {i}: {repeated}" for i in range(1,7))+ '\n{"count": 3}'
        row,items,_,_=score.score_one("prose","test",q,text,"stop",repeated,events)
        self.assertEqual(row["matched_planted"],3)
        self.assertEqual(row["repetition_loop"],1)

    def test_fourth_duplicate_line_is_extra_after_three_targets_consumed(self):
        q=dict(self.q); q["reference"]={"count":3}
        repeated="return lookup_x()"
        events=[{"doc_id":q["doc_id"],"role":"aggregation_target","key":q["entity_key"][0],"text":repeated,"event_id":str(i)} for i in range(3)]
        text="\n".join(f"found {i}: {repeated}" for i in range(1,5))+ '\n{"count": 3}'
        row,items,_,_=score.score_one("prose","test",q,text,"stop",repeated,events)
        self.assertEqual((row["matched_planted"],row["ambiguous"],row["extra_items"]),(3,0,1))
        self.assertEqual(items[-1]["match_class"],"extra_item")

    def test_document_search_ignores_indentation_and_newlines(self):
        self.assertTrue(score.is_in_document("def call_hrtwbjsd():", "\n    def   call_hrtwbjsd ( ):\n        pass\n"))

    def test_document_check_finds_source_quote_with_appended_commentary(self):
        quote=self.target_lines()[0]
        self.assertTrue(score.is_in_document(quote+" (my note)", self.doc, self.targets))

    def test_scratchpad_request_preserves_003_base_fields(self):
        doc="document bytes\n"
        model="qwen36_35b_a3b"
        params=json.loads((ROOT/"DATA/sampling.json").read_text())["models"][model]
        payload=scratchrun.build_payload(doc,self.q,model,params,max_tokens=1024)
        seed=int(__import__("hashlib").sha256(self.q["question_id"].encode()).hexdigest()[:8],16)
        self.assertEqual(payload["messages"][0]["content"].encode(),doc.encode())
        user=payload["messages"][1]["content"].encode()
        original=self.q["prompt"].encode()
        self.assertTrue(user.startswith(original+b"\n\n"+scratchrun.APPEND.encode()))
        self.assertEqual(payload["seed"],seed)
        self.assertEqual(payload["temperature"],params["temperature"])
        self.assertEqual(payload["top_p"],params["top_p"])
        self.assertEqual(payload["max_tokens"],1024)
        for source,target in (("top_k","top_k"),("min_p","min_p"),("presence_penalty","presence_penalty"),("repetition_penalty","repeat_penalty")):
            if source in params: self.assertEqual(payload[target],params[source])

    def test_preflight_accepts_valid_response_over_128_tokens(self):
        choice={"finish_reason":"stop","message":{"content":"x "*200+'{"count": 2}'}}
        self.assertTrue(scratchrun.preflight_pass(choice))
        choice["finish_reason"]="length"
        self.assertFalse(scratchrun.preflight_pass(choice))

    def test_checkpoint_projection_replays_qwen36_actual_timings(self):
        rows=[json.loads(x) for x in (ROOT/"_internal/scratchpad/progress.jsonl").read_text().splitlines() if x.strip()]
        estimate=json.loads((ROOT/"DATA/code/phase0-estimate.json").read_text())
        totals=defaultdict(float)
        for r in rows: totals[r["length_label"]]+=float(r["answer_s"])
        remaining,by_model=scratchrun.project_remaining(rows,"qwen36_35b_a3b",["qwen36_35b_a3b"],estimate,safety_factor=1,startup_seconds=0)
        self.assertAlmostEqual(remaining,sum(totals.values()),places=6)
        self.assertAlmostEqual(by_model["qwen36_35b_a3b"],sum(totals.values()),places=6)

if __name__=="__main__": unittest.main()
