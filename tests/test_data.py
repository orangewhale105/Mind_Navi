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
        """バックアップ（4.5）：12種類。データフォルダとこの PC の両方に書く。PC ごとに分け、種類ごとに2つ（開閉は10、
        バージョンアップの前は消さない）。中身が同じなら書かない。期間が過ぎた種類だけ書く。4.4 までのものも一覧に出て消えない"""
        import datetime
        saved = app.BACKUP_DIR
        app.BACKUP_DIR = os.path.join(self.tmp, "bk")
        try:
            data_file = os.path.join(self.tmp, "drive", "my.json")
            os.makedirs(os.path.dirname(data_file))
            with open(data_file, "w", encoding="utf-8") as f:
                f.write('{"nodes": [], "view": {}}')
            kinds = [k for k, _n, _c, _p in app.RP_KINDS if k not in ("guard", "restore", "hourly", "daily", "monthly")]
            self.assertEqual(kinds, ["m5", "m30", "h1", "open", "close", "d1", "d2", "d3", "w1", "mo1", "mo3", "y1", "upgrade"])
            # 4.4 までの名前のバックアップ（消さずに一覧に出す）
            for d in app.rp_dirs(data_file):
                os.makedirs(d, exist_ok=True)
                import gzip
                with gzip.open(os.path.join(d, "daily_20261101-120000.json.gz"), "wb") as f:
                    f.write(b'{"nodes": [9], "view": {}}')
            t0 = datetime.datetime(2026, 11, 8, 9, 0, 0)
            periodic = ["m5", "m30", "h1", "d1", "d2", "d3", "w1", "mo1", "mo3", "y1"]
            self.assertEqual(app.rp_due(data_file, t0, pc="home"), periodic)
            for k in periodic:
                self.assertEqual(app.rp_write(data_file, k, b'{"nodes": [1]}', pc="home", now_=t0), 2)   # 両方の場所
            self.assertEqual(app.rp_due(data_file, t0 + datetime.timedelta(minutes=1), pc="home"), [])
            self.assertEqual(app.rp_due(data_file, t0 + datetime.timedelta(minutes=6), pc="home"), ["m5"])
            self.assertEqual(app.rp_due(data_file, t0 + datetime.timedelta(days=2, minutes=1), pc="home"),
                             ["m5", "m30", "h1", "d1", "d2"])
            self.assertEqual(app.rp_due(data_file, t0, pc="school"), periodic)   # PC ごとに別
            # 中身が同じなら書かない
            self.assertEqual(app.rp_write(data_file, "m5", b'{"nodes": [1]}', pc="home",
                                          now_=t0 + datetime.timedelta(minutes=6)), 0)
            # 種類ごとに2つだけ残す（ほかの PC のものは消さない）
            app.rp_write(data_file, "m5", b'{"nodes": [1]}', pc="school", now_=t0)
            for i in range(2, 6):
                app.rp_write(data_file, "m5", ('{"nodes": [%d]}' % i).encode(), pc="home",
                             now_=t0 + datetime.timedelta(minutes=5 * i))
            lst = app.rp_list(data_file)
            home_m5 = [x for x in lst if x[1] == "m5" and x[3] == "home"]
            self.assertEqual([app.read_data_file(x[2])["nodes"] for x in home_m5], [[5], [4]])
            self.assertEqual(len([x for x in lst if x[1] == "m5" and x[3] == "school"]), 1)
            self.assertEqual([x[1] for x in lst if x[0] == datetime.datetime(2026, 11, 1, 12)], ["daily"])
            for d in app.rp_dirs(data_file):   # 両方の場所に同じ数
                self.assertTrue(os.path.exists(os.path.join(d, "daily_20261101-120000.json.gz")))
                self.assertEqual(len([f for f in os.listdir(d) if "_home_" in f and f.startswith("m5_")]), 2)
            self.assertTrue(app.rp_dirs(data_file)[1].startswith(os.path.join(self.tmp, "drive", app.RP_SUBDIR)))
            # 開いたとき：前の版で保存したファイルは「バージョンアップの前」に残し、消さない
            old = json.dumps({"nodes": [7], "view": {"mn_guard": {"ver": "4.2"}}}).encode()
            app.rp_on_open(data_file, old)
            app.rp_on_open(data_file, old)
            up = [x for x in app.rp_list(data_file) if x[1] == "upgrade"]
            self.assertEqual([(x[4], app.read_data_file(x[2])["nodes"]) for x in up], [("4.2", [7])])
            app.rp_on_open(data_file, json.dumps({"nodes": [8], "view": {"mn_guard": {"ver": app.APP_VERSION}}}).encode())
            self.assertEqual(len([x for x in app.rp_list(data_file) if x[1] == "upgrade"]), 1)   # 今の版なら作らない
            for i in range(12):   # 開いたときは10回分
                app.rp_write(data_file, "open", ('{"n": %d}' % i).encode(), pc="home",
                             now_=t0 + datetime.timedelta(seconds=i))
            self.assertEqual(len([x for x in app.rp_list(data_file) if x[1] == "open" and x[3] == "home"]), 10)
            self.assertGreater(app.ver_tuple("4.10"), app.ver_tuple("4.9"))
            self.assertNotIn("_", app.rp_pc_name())
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
        self.assertEqual(m["tags"], ["p", "q", "r"])   # 4.8：ほかの側に無いことは消したとみなさない（足した方が勝つ）
        changed = {"items": [{"id": "x", "v": 1}, {"id": "y", "v": 5}]}   # 消した品をほかで変えていた → 残す
        self.assertEqual(app.merge3(base, {"items": [{"id": "x", "v": 1}]}, changed)["items"],
                         [{"id": "x", "v": 1}, {"id": "y", "v": 5}])
        self.assertEqual(app.merge3(base, base, base), base)

    def test_stale_file_never_deletes(self):
        """（4.8）同期の遅れ・古い版の PC が古い中身でファイルを書いても、この PC にあるコンパス・デイリーコンパス・
        振り返り・実施の記録・ノード・IN/OUT_Navi の品を消さない（以前は「ほかで消した」とみなして全 PC から消えた）"""
        base = {"nodes": [{"id": "t", "label": "毎日", "repeat": {"freq": "daily"}, "done_dates": ["2026-11-07", "2026-11-08"]},
                          {"id": "n", "label": "新しいタスク"}, {"id": "g", "label": "目標"}],
                "edges": [{"source": "g", "target": "n", "relation": app.REL_CHILD}],
                "view": {"compass": {"2026-11-02": {"goal": "週の目標"}}, "day_compass": {"2026-11-08": "方向"},
                         "reviews": {"D:2026-11-08": {"text": "振り返り"}},
                         "shopping": {"items": [{"id": "s1", "name": "本"}]}}}
        stale = {"nodes": [{"id": "t", "label": "毎日", "repeat": {"freq": "daily"}, "done_dates": ["2026-11-07"]},
                           {"id": "g", "label": "目標"}],
                 "edges": [], "view": {"compass": {}, "shopping": {"items": []}}}
        ours = json.loads(json.dumps(base))
        for o in (ours, base):   # この PC が何も変えていないときも、変えたときも
            m = app.merge_doc(base, o, stale)
            v = m["view"]
            self.assertEqual(v["compass"], base["view"]["compass"])
            self.assertEqual(v["day_compass"], base["view"]["day_compass"])
            self.assertEqual(v["reviews"], base["view"]["reviews"])
            self.assertEqual(v["shopping"]["items"], [{"id": "s1", "name": "本"}])
            t = next(n for n in m["nodes"] if n["id"] == "t")
            self.assertEqual(t["done_dates"], ["2026-11-07", "2026-11-08"])
            self.assertTrue(any(n["id"] == "n" for n in m["nodes"]))
            self.assertTrue(any(e["target"] == "n" for e in m["edges"]))   # 親のつながりも残る
        # この PC で消したもの・ほかの PC でゴミ箱に入れたもの・スマホで消した買い物リストの品は消える
        mine = json.loads(json.dumps(base))
        mine["view"]["reviews"] = {}
        mine["nodes"][0]["done_dates"] = ["2026-11-07"]
        theirs = json.loads(json.dumps(base))
        theirs["nodes"] = [x for x in theirs["nodes"] if x["id"] != "n"]
        theirs["view"]["trash"] = [{"id": "z", "kind": "node", "data": {"nodes": [{"id": "n"}]}}]
        g = {"items": [{"id": "g1"}, {"id": "g2"}]}
        base["view"]["groceries"], mine["view"]["groceries"] = g, json.loads(json.dumps(g))
        theirs["view"]["groceries"] = {"items": [{"id": "g1"}]}
        m = app.merge_doc(base, mine, theirs)
        self.assertEqual(m["view"]["reviews"], {})
        self.assertEqual(next(n for n in m["nodes"] if n["id"] == "t")["done_dates"], ["2026-11-07"])
        self.assertFalse(any(n["id"] == "n" for n in m["nodes"]))
        self.assertEqual(m["view"]["groceries"]["items"], [{"id": "g1"}])
        # 親の付けかえ（ほかの PC）は1つの親になる
        b2 = {"nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}], "edges": [{"source": "a", "target": "c", "relation": app.REL_CHILD}]}
        t2 = {"nodes": b2["nodes"], "edges": [{"source": "b", "target": "c", "relation": app.REL_CHILD}]}
        self.assertEqual(app.merge_doc(b2, json.loads(json.dumps(b2)), t2)["edges"],
                         [{"source": "b", "target": "c", "relation": app.REL_CHILD}])

    def test_fill_doc_recovers_everything(self):
        """（4.8）すべてのバックアップから集めて戻す：消えたコンパス・デイリーコンパス・振り返り・実施の記録・ノードを足す。
        今の入力は変えない。ゴミ箱に入れたものは戻さない。2回やっても同じ"""
        old = {"nodes": [{"id": "t", "label": "毎日", "done_dates": ["2026-11-01", "2026-11-02"]}, {"id": "x", "label": "消したノード"},
                         {"id": "y", "label": "消えたノード"}],
               "edges": [{"source": "t", "target": "y", "relation": app.REL_CHILD}],
               "view": {"compass": {"w1": "目標"}, "day_compass": {"d1": "方向"}, "reviews": {"D:1": {"text": "昔"}}, "mn_guard": {"ver": "1"}}}
        cur = {"nodes": [{"id": "t", "label": "今の名前", "done_dates": ["2026-11-03"]}], "edges": [],
               "view": {"reviews": {"D:1": {"text": "今"}}, "trash": [{"id": "z", "kind": "node", "data": {"nodes": [{"id": "x"}]}}]}}
        n = app.fill_doc(cur, old)
        self.assertGreater(n, 0)
        ids = {x["id"] for x in cur["nodes"]}
        self.assertEqual(ids, {"t", "y"})   # ゴミ箱に入れた x は戻さない
        t = next(x for x in cur["nodes"] if x["id"] == "t")
        self.assertEqual(t["label"], "今の名前")
        self.assertEqual(sorted(t["done_dates"]), ["2026-11-01", "2026-11-02", "2026-11-03"])
        self.assertEqual(cur["view"]["compass"], {"w1": "目標"})
        self.assertEqual(cur["view"]["day_compass"], {"d1": "方向"})
        self.assertEqual(cur["view"]["reviews"]["D:1"]["text"], "今")
        self.assertNotIn("mn_guard", cur["view"])
        self.assertEqual(len(cur["edges"]), 1)
        import copy
        snap = copy.deepcopy(cur)
        self.assertEqual(app.fill_doc(cur, old), 0)
        self.assertEqual(cur, snap)

    def test_fill_missing_only_adds(self):
        """足すだけの復元：今の入力は変えず、消えた・空になったものだけ戻す。2回やっても同じ"""
        cur = {"a": "今", "b": "", "items": [{"id": "x", "v": "今", "memo": ""}], "tags": ["p"], "new": 1}
        old = {"a": "昔", "b": "昔", "c": "昔", "items": [{"id": "x", "v": "昔", "memo": "メモ"}, {"id": "y", "v": 1}],
               "tags": ["p", "q"]}
        n = app.fill_missing(cur, old)
        self.assertGreater(n, 0)
        self.assertEqual(cur["a"], "今")            # 今の入力は変えない
        self.assertEqual(cur["b"], "昔")            # 空になったものは戻す
        self.assertEqual(cur["c"], "昔")            # 消えた項目は戻す
        self.assertEqual(cur["new"], 1)             # 今だけにある項目は消さない
        self.assertEqual(cur["items"][0], {"id": "x", "v": "今", "memo": "メモ"})
        self.assertEqual([x["id"] for x in cur["items"]], ["x", "y"])
        self.assertEqual(cur["tags"], ["p", "q"])
        import copy
        snap = copy.deepcopy(cur)
        self.assertEqual(app.fill_missing(cur, old), 0)
        self.assertEqual(cur, snap)

    def test_trash_keeps_and_restores_without_overwriting(self):
        """ゴミ箱：消したノード（下位も）・外したタスクの予定と実施の記録・品を戻せる。今の入力は変えない"""
        mm = app.MindNavi()
        g = mm.add_node("目標")
        t = mm.add_node("タスク", parent=g, sched="2026-11-01", done_dates=["2026-11-01"])
        c = mm.add_node("下位", parent=t)
        snap = app.subtree_snapshot(mm, t)
        self.assertEqual({n["id"] for n in snap["nodes"]}, {t, c})
        app.trash_add(mm.view, "node", "タスク", snap)
        for k in (t, c):
            del mm.nodes[k]
        mm.edges = [e for e in mm.edges if e["target"] not in (t, c) and e["source"] not in (t, c)]
        self.assertEqual(app.trash_restore(mm, mm.view["trash"][-1]), 2)
        self.assertEqual(mm.nodes[t]["done_dates"], ["2026-11-01"])
        self.assertTrue(any(e["source"] == g and e["target"] == t for e in mm.edges))
        self.assertEqual(app.trash_restore(mm, mm.view["trash"][-1]), 0)   # 2回目は何も変わらない
        # タスクの設定を外した → 戻すと予定・実施の記録だけ戻り、そのあと変えた名前は変わらない
        app.trash_add(mm.view, "task_setting", "タスク", {"node": dict(mm.nodes[t])})
        mm.nodes[t].pop("sched")
        mm.nodes[t]["done_dates"] = []
        mm.nodes[t]["label"] = "新しい名前"
        app.trash_restore(mm, mm.view["trash"][-1])
        self.assertEqual(mm.nodes[t]["sched"], "2026-11-01")
        self.assertEqual(mm.nodes[t]["done_dates"], ["2026-11-01"])
        self.assertEqual(mm.nodes[t]["label"], "新しい名前")
        # IN/OUT_Navi の品
        mm.view["shopping"] = {"items": []}
        app.trash_add(mm.view, "shop", "本", {"item": {"id": "s1", "name": "本"}})
        app.trash_restore(mm, mm.view["trash"][-1])
        app.trash_restore(mm, mm.view["trash"][-1])
        self.assertEqual(mm.view["shopping"]["items"], [{"id": "s1", "name": "本"}])
        # ゴミ箱はデータファイルに入って残る
        d = json.loads(json.dumps(mm.to_dict()))
        self.assertEqual(len(d["view"]["trash"]), 3)

    def test_cancel_new_node_does_not_replace_map(self):
        """（4.6）新しいノードの取り消しは、そのノードだけを消す。マップ全体を「元に戻す」の記録（振り返り・
        IN/OUT_Navi・買い物リストを入れていない）で置きかえない（置きかえると次の保存でそれらが全部消えた）"""
        with open(APP, encoding="utf-8") as f:
            src = f.read()
        body = src.split("def _drop_new(self, nid):", 1)[1].split("\n        def ", 1)[0]
        self.assertNotIn("from_dict", body)
        self.assertIn("remove_node", body)
        for k in ("reviews", "shopping", "groceries", "memo", "day_compass", "trash"):
            self.assertIn(k, app.UNDO_KEEP_VIEW)

    def test_list_history_undo_30_steps(self):
        """（4.6）リストの Ctrl+Z：保存のたびに前の中身を覚え、30回まで戻せる。同じ辞書の中身を入れかえる"""
        data = {"items": [{"id": "a", "price": 1}]}
        h = app.ListHistory(data)
        same = data
        for i in range(2, 40):
            data["items"][0]["price"] = i
            h.note(data)
        h.note(data)   # 変わっていなければ覚えない
        n = 0
        while h.undo(data):
            n += 1
        self.assertEqual(n, app.UNDO_MAX)
        self.assertIs(data, same)
        self.assertEqual(data["items"][0]["price"], 39 - app.UNDO_MAX)

    def test_inuse_notice(self):
        """（4.6）使用中の札：ほかの PC の新しい札だけを返す。自分の札・古い札・閉じた札は返さない"""
        import datetime
        saved = app.BACKUP_DIR
        app.BACKUP_DIR = os.path.join(self.tmp, "bk")
        try:
            f = os.path.join(self.tmp, "drive", "my.json")
            os.makedirs(os.path.dirname(f))
            now_ = datetime.datetime(2026, 11, 8, 12, 0, 0)
            app.inuse_write(f, pc="home", now_=now_)
            app.inuse_write(f, pc="school", now_=now_ - datetime.timedelta(minutes=5))
            app.inuse_write(f, pc="lab", now_=now_ - datetime.timedelta(hours=2))   # 止まったまま → 無視
            self.assertEqual([o["pc"] for o in app.inuse_others(f, pc="home", now_=now_)], ["school"])
            app.inuse_clear(f, pc="school")
            self.assertEqual(app.inuse_others(f, pc="home", now_=now_), [])
            self.assertTrue(os.path.dirname(app.inuse_path(f, "home")).startswith(os.path.join(self.tmp, "drive")))
        finally:
            app.BACKUP_DIR = saved

    def test_terms_and_done_never_hidden(self):
        """（4.6）アドホック → Adhoc に読み替え。以前の「完了済みの枝を隠す」印があっても完了したタスクを隠さない"""
        d = {"nodes": [{"id": "r", "label": "アドホック"}, {"id": "p", "label": "Activity", "hide_done_kids": True},
                       {"id": "t", "label": "Dorm port 発送", "kind": "task", "status": "done"}],
             "edges": [{"source": "p", "target": "t", "relation": app.REL_CHILD}], "view": {}}
        mm = app.MindNavi.from_dict(d)
        self.assertEqual(mm.nodes["r"]["label"], "Adhoc")
        self.assertNotIn("t", mm.hidden_nodes())
        self.assertTrue(mm.nodes["p"].get("hide_done_kids"))   # 印は消さない（データはそのまま）
        self.assertLess(app.ver_tuple("4.5"), app.ver_tuple(app.APP_VERSION))
        self.assertEqual(app.LANE_ORDER, ("fold", "shrink", "expand", "all"))
        self.assertNotEqual(app.trial_red(1), app.trial_red(3))

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
