"""データの読み書き・バックアップ・CLI出力のテスト（GUI不要・tkinter なしで動く）

実行: python -m unittest discover tests
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "desktop", "mind_navi.py")
SAMPLE = os.path.join(ROOT, "samples", "mind_navi_sample.json")
sys.path.insert(0, os.path.join(ROOT, "desktop"))

import mind_navi as app  # noqa: E402


class DataFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sample_loads(self):
        mm = app.MindNavi.load(SAMPLE)
        with open(SAMPLE, encoding="utf-8") as f:
            raw = json.load(f)
        self.assertEqual(len(mm.nodes), len(raw["nodes"]))
        self.assertEqual(len(mm.edges), len(raw["edges"]))

    def test_roundtrip_keeps_everything(self):
        """保存→読込で、未知の属性・view の全データ（買い物リストなど）が消えない"""
        with open(SAMPLE, encoding="utf-8") as f:
            raw = json.load(f)
        raw["nodes"][0]["future_field"] = {"a": 1}
        raw["view"]["future_view"] = [1, 2, 3]
        src = os.path.join(self.tmp, "in.json")
        with open(src, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
        out = os.path.join(self.tmp, "out.json")
        app.MindNavi.load(src).save_json(out)
        with open(out, encoding="utf-8") as f:
            back = json.load(f)
        node0 = next(n for n in back["nodes"] if n["id"] == raw["nodes"][0]["id"])
        self.assertEqual(node0["future_field"], {"a": 1})
        self.assertEqual(back["view"]["future_view"], [1, 2, 3])
        for key in ("groceries", "shopping", "memo", "lifeplan", "compass"):
            self.assertEqual(back["view"][key], raw["view"][key], key)
        self.assertEqual(back["app"], "Mind_Navi")
        self.assertEqual(back["version"], app.FORMAT_VERSION)

    def test_old_name_data_loads(self):
        """旧名（TaskMap）のころのデータファイルもそのまま開ける"""
        with open(SAMPLE, encoding="utf-8") as f:
            raw = json.load(f)
        raw["app"] = "TaskMap"
        src = os.path.join(self.tmp, "old.json")
        with open(src, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
        self.assertEqual(len(app.MindNavi.load(src).nodes), len(raw["nodes"]))
        self.assertIs(app.TaskMap, app.MindNavi)

    def test_backup_file_name(self):
        self.assertEqual(app.mirror_path("x/mind_navi.json"), "x/mind_navi.backup.json")
        self.assertIsNone(app.mirror_path("x/mind_navi.backup.json"))
        self.assertIsNone(app.mirror_path("x/plan_nodes.csv"))

    def test_quadrant_rule(self):
        """指標は 1 が最も高い（1〜3 が高）"""
        q = app.task_quad
        self.assertEqual(q({"imp": 1, "need": 1}), "core")
        self.assertEqual(q({"imp": 6, "need": 2}), "infra")      # Operational
        self.assertEqual(q({"imp": 2, "need": 6}), "ambition")   # Strategic
        self.assertEqual(q({"imp": 5, "need": 5}), "bull")       # Divest
        self.assertIsNone(q({"imp": 1}))

    def test_cli_export(self):
        base = os.path.join(self.tmp, "plan")
        r = subprocess.run([sys.executable, APP, "--export", SAMPLE, base],
                           capture_output=True, text=True, timeout=120,
                           env={**os.environ, "HOME": self.tmp, "USERPROFILE": self.tmp})
        self.assertEqual(r.returncode, 0, r.stderr)
        for suffix in ("_nodes.csv", "_edges.csv", ".graphml"):
            self.assertTrue(os.path.exists(base + suffix), suffix)

    def test_source_markers(self):
        with open(APP, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("VERSION", text.splitlines()[2])
        self.assertTrue(text.rstrip().endswith("# END OF FILE"))


if __name__ == "__main__":
    unittest.main()
