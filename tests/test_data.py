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

    def test_fill_lost_shopping_entries(self):
        """消えた IN/OUT_Navi の入力を古いデータから補う。あとで入力し直した品はそのまま"""
        old = {"v": 4, "items": [
            {"id": "a", "name": "コート", "life": 6, "value": 2, "price": 1, "status": "sold", "sell": 500,
             "status_log": [{"s": "buy", "d": "2026-01-01"}, {"s": "sold", "d": "2026-02-01"}]},
            {"id": "b", "name": "本", "life": 5, "value": 5, "price": 1, "status": "buy"},
            {"id": "c", "name": "靴", "life": 1, "value": 1, "price": 1, "status": "hold"}]}
        broken = {"v": 4, "items": [
            {"id": "a", "name": "コート", "life": 4, "value": 4, "price": 1, "status": "wants",
             "status_log": [{"s": "wants", "d": "2026-11-08"}]},
            {"id": "b", "name": "本", "life": 3, "value": 4, "price": 1, "status": "wants"},   # 入力し直した品
            {"id": "c", "name": "靴", "life": 4, "value": 4, "price": 1, "status": "wants"},
            {"id": "d", "name": "新しい品", "life": 4, "value": 4, "price": 1, "status": "wants"}]}
        n = app.shopping_fill_lost(broken, old)
        self.assertEqual(n, 2)
        by = {x["id"]: x for x in broken["items"]}
        self.assertEqual((by["a"]["status"], by["a"]["life"], by["a"]["sell"]), ("sold", 6, 500))
        self.assertEqual((by["b"]["status"], by["b"]["life"]), ("wants", 3))
        self.assertEqual((by["c"]["status"], by["d"]["status"]), ("hold", "wants"))

    def test_restore_points(self):
        """復元ポイント：このPCとデータフォルダの両方に書き、種類ごとに数を保つ。保存の時期の判定"""
        import datetime
        saved = app.BACKUP_DIR
        app.BACKUP_DIR = os.path.join(self.tmp, "bk")
        try:
            data_file = os.path.join(self.tmp, "drive", "my.json")
            os.makedirs(os.path.dirname(data_file))
            with open(data_file, "w", encoding="utf-8") as f:
                f.write('{"nodes": [], "view": {}}')
            self.assertEqual(set(app.rp_due(data_file)), {"hourly", "daily", "monthly"})
            app.rp_write(data_file, "hourly", b'{"nodes": [1], "view": {}}')
            app.rp_write(data_file, "daily", b'{"nodes": [1], "view": {}}')
            app.rp_write(data_file, "monthly", b'{"nodes": [1], "view": {}}')
            self.assertEqual(app.rp_due(data_file), [])
            later = datetime.datetime.now() + datetime.timedelta(hours=2)
            self.assertIn("hourly", app.rp_due(data_file, later))
            for d in app.rp_dirs(data_file):
                self.assertEqual(len([f for f in os.listdir(d) if f.endswith(".json.gz")]), 3)
            self.assertTrue(app.rp_dirs(data_file)[1].startswith(os.path.join(self.tmp, "drive", app.RP_SUBDIR)))
            lst = app.rp_list(data_file)
            self.assertEqual(len(lst), 3)   # 両方の場所にあっても1つに
            self.assertEqual(app.read_data_file(lst[0][2])["nodes"], [1])
        finally:
            app.BACKUP_DIR = saved

    def test_data_score_detects_wiped_entries(self):
        d = {"nodes": [{}] * 3, "view": {"shopping": {"items": [{"status": "buy"}, {"status": "hold"}, {"life": 6}]},
                                         "groceries": {"items": [{}, {}]}}}
        self.assertEqual(app.data_score(d), {"nodes": 3, "shop": 3, "shop_info": 3, "groc": 2})

    def test_app_version_matches_header(self):
        with open(APP, encoding="utf-8") as f:
            head = f.readline() + f.readline() + f.readline()
        self.assertIn(f"VERSION {app.APP_VERSION} ", head)

    def test_merge3_two_pcs_keep_both(self):
        """2台の PC：学校で書いた振り返り・完了・IN/OUT_Navi と、家で変えた内容がどちらも残る（上書きで消えない）"""
        base = {"nodes": [{"id": "t1", "label": "論文", "status": "todo", "done_dates": []},
                          {"id": "t2", "label": "運動", "status": "todo"}],
                "edges": [{"source": "r", "target": "t1"}],
                "view": {"reviews": {"D:2026-11-06": "6日の振り返り"},
                         "shopping": {"v": 4, "items": [{"id": "a", "name": "本", "status": "wants", "life": 4}]}}}
        import copy
        school = copy.deepcopy(base)   # ほかの PC（ファイルに保存済み）
        school["view"]["reviews"]["D:2026-11-07"] = "7日の振り返り（学校で書いた）"
        school["nodes"][0]["status"] = "done"
        school["view"]["shopping"]["items"][0].update(status="hold", life=6)
        school["view"]["shopping"]["items"].append({"id": "b", "name": "靴", "status": "buy"})
        home = copy.deepcopy(base)     # 開いたままの PC
        home["view"]["reviews"]["D:2026-11-08"] = "8日の振り返り（家で書いた）"
        home["nodes"][1]["label"] = "運動（30分）"
        home["nodes"].append({"id": "t3", "label": "新しいタスク", "status": "todo"})
        m = app.merge3(base, home, school)
        self.assertEqual(set(m["view"]["reviews"]), {"D:2026-11-06", "D:2026-11-07", "D:2026-11-08"})
        nodes = {n["id"]: n for n in m["nodes"]}
        self.assertEqual(nodes["t1"]["status"], "done")
        self.assertEqual(nodes["t2"]["label"], "運動（30分）")
        self.assertIn("t3", nodes)
        items = {x["id"]: x for x in m["view"]["shopping"]["items"]}
        self.assertEqual((items["a"]["status"], items["a"]["life"]), ("hold", 6))
        self.assertIn("b", items)
        self.assertEqual(m["edges"], base["edges"])

    def test_merge3_deletions_and_conflicts(self):
        base = {"items": [{"id": "x", "v": 1}, {"id": "y", "v": 1}], "s": "a", "tags": ["p", "q"]}
        ours = {"items": [{"id": "x", "v": 1}], "s": "b", "tags": ["p", "q", "r"]}          # y を消した
        theirs = {"items": [{"id": "x", "v": 2}, {"id": "y", "v": 1}], "s": "c", "tags": ["q"]}  # p を外した
        m = app.merge3(base, ours, theirs)
        self.assertEqual(m["items"], [{"id": "x", "v": 2}])   # y はこの PC で消した。x はほかの変更を使う
        self.assertEqual(m["s"], "b")                          # 両方が変えた → この PC
        self.assertEqual(m["tags"], ["q", "r"])
        changed = {"items": [{"id": "x", "v": 1}, {"id": "y", "v": 5}]}   # 消した品をほかで変えていた → 残す
        self.assertEqual(app.merge3(base, {"items": [{"id": "x", "v": 1}]}, changed)["items"],
                         [{"id": "x", "v": 1}, {"id": "y", "v": 5}])
        self.assertEqual(app.merge3(base, base, base), base)

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
