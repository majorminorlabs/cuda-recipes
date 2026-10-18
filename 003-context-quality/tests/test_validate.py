"""Public-package checks and strict optional private-response coverage."""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_validator", ROOT / "validate.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
CONFIG = json.loads((ROOT / "DATA/study-config.json").read_text())


class PublicValidationTests(unittest.TestCase):
    def test_both_public_arms_skip_absent_private_capture(self):
        for arm, folder, config in [("prose", ROOT / "DATA", CONFIG), ("code", ROOT / "DATA/code", CONFIG["arms"]["code"])]:
            with self.subTest(arm=arm), tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as output:
                validator.validate_arm(folder, config, Path(tmp), arm)
                self.assertIn("raw responses not published; coverage check skipped.", output.getvalue())

    def test_partial_private_capture_fails(self):
        answers = validator.rows(ROOT / "DATA", "answer-results.csv")
        models = set(CONFIG["models"])
        with tempfile.TemporaryDirectory() as tmp:
            model = sorted(models)[0]
            (Path(tmp) / f"primary-{model}.jsonl").write_text(json.dumps({"question_id": "missing", "model": model, "arm": "primary"}) + "\n")
            with self.assertRaisesRegex(ValueError, "missing raw response"):
                validator.check_raw_coverage(Path(tmp), answers, models, "prose")

    def test_complete_private_capture_passes(self):
        answers = validator.rows(ROOT / "DATA/code", "answer-results.csv")
        models = set(CONFIG["arms"]["code"]["models"])
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as output:
            for model in models:
                records = [{"question_id": row["question_id"], "model": model, "arm": "primary"} for row in answers if row["model"] == model]
                (Path(tmp) / f"primary-{model}.jsonl").write_text("\n".join(map(json.dumps, records)))
            validator.check_raw_coverage(Path(tmp), answers, models, "code")
            self.assertIn("PASS: code raw response coverage", output.getvalue())

    def test_tampered_dataset_hashes_fail(self):
        for relative, message in [("questions.jsonl", "question hash mismatch"), ("documents/control.txt", "document hash mismatch")]:
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / "DATA"
                shutil.copytree(ROOT / "DATA", folder)
                with (folder / relative).open("a") as target:
                    target.write("\n")
                with self.assertRaisesRegex(ValueError, message):
                    validator.check_dataset(folder)

    def test_duplicate_answer_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "DATA"
            shutil.copytree(ROOT / "DATA", folder)
            path = folder / "answer-results.csv"
            with path.open(newline="") as source:
                rows = list(csv.reader(source))
            with path.open("a", newline="") as target:
                csv.writer(target).writerow(rows[1])
            with self.assertRaisesRegex(ValueError, "duplicate answer"):
                validator.validate_arm(folder, CONFIG, Path(tmp) / "absent", "prose")

    def test_checksum_tampering_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "file.txt").write_bytes(b"original")
            (root / "SHA256SUMS").write_text(hashlib.sha256(b"original").hexdigest() + "  file.txt\n")
            with contextlib.redirect_stdout(io.StringIO()):
                validator.check_checksums(root)
            (root / "file.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "SHA256SUMS mismatch"):
                validator.check_checksums(root)


if __name__ == "__main__":
    unittest.main()
