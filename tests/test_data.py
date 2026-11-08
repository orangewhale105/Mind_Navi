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

    def test_shopping_upgrade_keeps_current_data(self):
        """IN/OUT_Navi：今の形式（v4）のデータを読み替えても、状態・★・売却価格・履歴が消えない（3.8 の不具合の再発防止）"""
        import copy
        d = {"v": 4, "categories": ["衣類"], "hold_limits": {"衣類": 3}, "order": ["a"], "items": [
            {"id": "a", "name": "コート", "cat": "衣類", "life": 6, "value": 2, "price": 20000, "sell": 8000,
             "daily": False, "added": "2026-01-02", "bought": "2026-01-05", "status": "sold", "status_date": "2026-10-01",
             "status_log": [{"s": "wants", "d": "2026-01-02"}, {"s": "buy", "d": "2026-01-05"}, {"s": "sold", "d": "2026-10-01"}],
             "future_field": {"x": 1}}]}
        before = copy.deepcopy(d)
        for _ in range(3):   # 何度読み替えても同じ
            app.shopping_upgrade(d)
        self.assertEqual(d, before)

    def test_shopping_upgrade_old_formats(self):
        """最初の形式（v なし）・v3 から読み替えて、何度読み替えても同じになる"""
        import copy
        old = {"items": [{"id": "x", "name": "本", "need": "1", "imp": "3", "price": "1500", "memo_extra": "残す"}],
               "bought": [{"id": "y", "name": "洗剤", "need": "2", "imp": "2", "price": 400, "date": "2026-02-01"}]}
        app.shopping_upgrade(old)
        self.assertEqual(old["v"], 4)
        x = next(i for i in old["items"] if i["id"] == "x")
        y = next(i for i in old["items"] if i["id"] == "y")
        self.assertEqual((x["life"], x["value"], x["status"], x["memo_extra"]), (6, 1, "wants", "残す"))
        self.assertEqual((y["status"], y["bought"]), ("buy", "2026-02-01"))
        once = copy.deepcopy(old)
        app.shopping_upgrade(old)
        self.assertEqual(old, once)
        v3 = {"v": 3, "items": [{"id": "p", "name": "a", "life": 5, "value": 6, "price": 1, "plan": True, "added": "2026-03-01"},
                                {"id": "q", "name": "b", "life": 2, "value": 3, "price": 1, "skip": True, "added": "2026-03-01"}]}
        app.shopping_upgrade(v3)
        self.assertEqual([i["status"] for i in v3["items"]], ["buy", "hold"])
        self.assertEqual([(i["life"], i["value"]) for i in v3["items"]], [(5, 6), (2, 3)])

    def test_groceries_keep_qty(self):
        """買い物リスト：開くたびに個数が1に戻っていた不具合の再発防止"""
        import copy
        d = {"items": [{"id": "a", "name": "卵", "qty": 3, "price": 250, "need": 1, "bought": False, "x_unknown": 1}],
             "staples": [], "history": []}
        app.groceries_normalize(d)
        once = copy.deepcopy(d)
        app.groceries_normalize(d)
        self.assertEqual(d, once)
        self.assertEqual(d["items"][0]["qty"], 3)
        self.assertEqual(d["items"][0]["x_unknown"], 1)

    def test_background_writer_keeps_order(self):
        """バックアップなどの書き込みは別の処理で、頼んだ順に行い、flush で書き終わりを待てる"""
        w = app.BgWriter()
        p = os.path.join(self.tmp, "b.json")
        for i in range(50):
            def write(i=i):
                with open(p, "w", encoding="utf-8") as f:
                    f.write(str(i))
            w.put(write)
        w.put(lambda: 1 / 0)   # 失敗しても後の書き込みは続く
        w.put(lambda: open(p + ".done", "w").close())
        w.flush()
        with open(p, encoding="utf-8") as f:
            self.assertEqual(f.read(), "49")
        self.assertTrue(os.path.exists(p + ".done"))


if __name__ == "__main__":
    unittest.main()
