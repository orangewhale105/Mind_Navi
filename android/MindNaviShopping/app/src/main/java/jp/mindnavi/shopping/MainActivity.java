// Mind_Navi 買い物リスト（Android）  VERSION 1.2（versionCode 3）  最終更新日 2026-11-08
package jp.mindnavi.shopping;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ContentResolver;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Mind_Navi（PC版）と同じデータファイルを使う、スマホ用の買い物リスト。
 * ・データファイル（Googleドライブにある Mind_Navi の .json）を「ファイルを選ぶ」で一度選ぶと、次からはそのファイルを開く
 * ・ファイルは分けずに一つのまま。書きかえるのは中の「買い物リスト」（view → groceries）だけで、ほかの部分は読んだとおりに書き戻す
 * ・リストに直接入力（品名・価格はその場で、必要度は一覧から、☐ で購入。購入回数は 週・月・年）
 * ・定番（いつも買う物）から ＋ で買い物リストへ
 */
public class MainActivity extends Activity {

    private static final int REQ_OPEN = 1;
    private static final String PREF = "mind_navi_shopping";
    private static final String[] NEED = {"高", "中", "低"};   // 1・2・3（PC版と同じ）

    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private final Handler ui = new Handler(Looper.getMainLooper());

    private Uri fileUri;
    private Map<String, Object> groceries;   // view → groceries（items・staples・history）
    private boolean showStaples = false;
    private boolean pendingSave = false;

    private LinearLayout listBox;
    private TextView titleView, totalView, countView, statusView;
    private Button tabList, tabStaples, clearDoneBtn;

    private final Runnable saveTask = new Runnable() {
        @Override
        public void run() {
            saveNow();
        }
    };

    // ================= 画面 =================
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.WHITE);

        LinearLayout bar = row();
        bar.setBackgroundColor(Color.rgb(24, 100, 171));
        bar.setPadding(dp(12), dp(8), dp(8), dp(8));
        titleView = text("買い物リスト", 18, true);
        titleView.setTextColor(Color.WHITE);
        bar.addView(titleView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        Button reload = smallButton("再読込");
        reload.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                load();
            }
        });
        bar.addView(reload);
        Button pick = smallButton("ファイル");
        pick.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                pickFile();
            }
        });
        bar.addView(pick);
        root.addView(bar);

        LinearLayout tabs = row();
        tabList = tabButton("買い物リスト");
        tabStaples = tabButton("定番");
        tabList.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
            showStaples = false;
            render();
        }
        });
        tabStaples.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
            showStaples = true;
            render();
        }
        });
        tabs.addView(tabList, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        tabs.addView(tabStaples, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        root.addView(tabs);

        ScrollView sv = new ScrollView(this);
        listBox = new LinearLayout(this);
        listBox.setOrientation(LinearLayout.VERTICAL);
        listBox.setPadding(dp(6), dp(4), dp(6), dp(4));
        sv.addView(listBox);
        root.addView(sv, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));

        LinearLayout foot = new LinearLayout(this);
        foot.setOrientation(LinearLayout.VERTICAL);
        foot.setBackgroundColor(Color.rgb(248, 249, 250));
        foot.setPadding(dp(10), dp(6), dp(10), dp(6));
        totalView = text("", 15, true);
        totalView.setTextColor(Color.rgb(24, 100, 171));
        countView = text("", 13, false);
        statusView = text("", 12, false);
        statusView.setTextColor(Color.GRAY);
        clearDoneBtn = smallButton("購入済みを片付ける");
        clearDoneBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                clearDone();
            }
        });
        foot.addView(totalView);
        foot.addView(countView);
        LinearLayout fr = row();
        fr.addView(statusView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        fr.addView(clearDoneBtn);
        foot.addView(fr);
        root.addView(foot);
        setContentView(root);

        String u = getSharedPreferences(PREF, MODE_PRIVATE).getString("uri", null);
        if (u != null) {
            fileUri = Uri.parse(u);
            load();
        } else {
            render();
            pickFile();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (fileUri != null && groceries != null && !pendingSave) {
            load();   // PC で変えた分を読み直す
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (pendingSave) {   // 画面を離れるときは、待たずに保存
            ui.removeCallbacks(saveTask);
            saveNow();
        }
    }

    // ================= ファイル（Googleドライブ上の Mind_Navi のデータ） =================
    private void pickFile() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("*/*");
        i.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"application/json", "application/octet-stream", "text/plain"});
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        startActivityForResult(i, REQ_OPEN);
        toast("Googleドライブの Mind_Navi のデータファイル（.json）を選んでください");
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);
        if (req == REQ_OPEN && res == RESULT_OK && data != null && data.getData() != null) {
            fileUri = data.getData();
            try {
                getContentResolver().takePersistableUriPermission(fileUri,
                        Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
            } catch (SecurityException e) {
                toast("このファイルは書きかえの許可が取れませんでした");
            }
            getSharedPreferences(PREF, MODE_PRIVATE).edit().putString("uri", fileUri.toString()).apply();
            load();
        }
    }

    private String readText() throws Exception {
        ContentResolver cr = getContentResolver();
        try (InputStream in = cr.openInputStream(fileUri)) {
            if (in == null) {
                throw new Exception("ファイルを開けません");
            }
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[65536];
            int k;
            while ((k = in.read(buf)) > 0) {
                bo.write(buf, 0, k);
            }
            return new String(bo.toByteArray(), StandardCharsets.UTF_8);
        }
    }

    private void writeText(String txt) throws Exception {
        ContentResolver cr = getContentResolver();
        OutputStream out;
        try {
            out = cr.openOutputStream(fileUri, "wt");   // 書きかえ（前の内容は消す）
        } catch (Exception e) {
            out = cr.openOutputStream(fileUri, "w");
        }
        if (out == null) {
            throw new Exception("ファイルに書けません");
        }
        try (OutputStream o = out) {
            o.write(txt.getBytes(StandardCharsets.UTF_8));
            o.flush();
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> groceriesOf(Object rootObj) throws Exception {
        if (!(rootObj instanceof Map)) {
            throw new Exception("Mind_Navi のデータファイルではありません");
        }
        Map<String, Object> root = (Map<String, Object>) rootObj;
        if (!root.containsKey("nodes")) {
            throw new Exception("Mind_Navi のデータファイルではありません（nodes がありません）");
        }
        Map<String, Object> g = Json.obj(Json.obj(root, "view"), "groceries");
        Json.arr(g, "items");
        Json.arr(g, "staples");
        Json.arr(g, "history");
        return g;
    }

    private void load() {
        if (fileUri == null) {
            return;
        }
        status("読み込み中…");
        io.execute(new Runnable() {
            @Override
            public void run() {
            try {
                Map<String, Object> g = groceriesOf(Json.parse(readText()));
                ui.post(new Runnable() {
            @Override
            public void run() {
                    groceries = g;
                    status("読み込みました");
                    render();
                }
        });
            } catch (Exception e) {
                ui.post(new Runnable() {
                    @Override
                    public void run() {
                        status("読めませんでした：" + e.getMessage());
                    }
                });
            }
        }
        });
    }

    /** 変えたら少し待って保存（続けて入力している間はまとめて1回） */
    private void scheduleSave() {
        pendingSave = true;
        ui.removeCallbacks(saveTask);
        ui.postDelayed(saveTask, 1500);
        status("保存待ち…");
    }

    /** 保存：直前にファイルを読み直し、買い物リストの部分だけを差しかえて書く（PC で変えたほかの部分を消さない） */
    private void saveNow() {
        if (fileUri == null || groceries == null) {
            return;
        }
        pendingSave = false;
        final String mine = Json.dump(groceries);
        io.execute(new Runnable() {
            @Override
            public void run() {
            try {
                Object root = Json.parse(readText());
                Map<String, Object> view = Json.obj(castMap(root), "view");
                view.put("groceries", Json.parse(mine));
                writeText(Json.dump(root));
                ui.post(new Runnable() {
                    @Override
                    public void run() {
                        status("保存しました " + LocalDateTime.now().withNano(0).toLocalTime());
                    }
                });
            } catch (Exception e) {
                ui.post(new Runnable() {
            @Override
            public void run() {
                    pendingSave = true;
                    status("保存できませんでした：" + e.getMessage());
                }
        });
            }
        }
        });
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> castMap(Object o) throws Exception {
        if (!(o instanceof Map)) {
            throw new Exception("Mind_Navi のデータファイルではありません");
        }
        return (Map<String, Object>) o;
    }

    // ================= データ =================
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> list(String key) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (groceries == null) {
            return out;
        }
        for (Object o : Json.arr(groceries, key)) {
            if (o instanceof Map) {
                out.add((Map<String, Object>) o);
            }
        }
        return out;
    }

    private static String newId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 8);
    }

    private static String nowText() {
        return LocalDateTime.now().withNano(0).toString();
    }

    /** 品の購入回数：今週（月曜から）・今月・今年 */
    private long[] counts(String name) {
        long wk = 0, mo = 0, yr = 0;
        LocalDate today = LocalDate.now();
        LocalDate mon = today.minusDays(today.getDayOfWeek().getValue() - 1);
        for (Map<String, Object> h : list("history")) {
            if (!name.equals(Json.s(h, "name"))) {
                continue;
            }
            LocalDate d;
            try {
                d = LocalDate.parse(Json.s(h, "date").substring(0, 10));
            } catch (Exception e) {
                continue;
            }
            if (d.getYear() == today.getYear()) {
                yr++;
                if (d.getMonthValue() == today.getMonthValue()) {
                    mo++;
                }
            }
            if (!d.isBefore(mon) && !d.isAfter(today)) {
                wk++;
            }
        }
        return new long[]{wk, mo, yr};
    }

    private void toggleBought(Map<String, Object> x, boolean on) {
        String today = LocalDate.now().toString();
        x.put("bought", on);
        List<Object> hist = Json.arr(groceries, "history");
        if (on) {   // 購入：回数を記録（PC版と同じ形）
            Map<String, Object> h = new LinkedHashMap<>();
            h.put("name", Json.s(x, "name"));
            h.put("date", today);
            h.put("price", Json.RawNum.of(sub(x)));
            h.put("qty", Json.RawNum.of(qty(x)));
            hist.add(h);
        } else {   // 取り消し：今日の記録を1つ消す
            for (int i = hist.size() - 1; i >= 0; i--) {
                Object o = hist.get(i);
                if (o instanceof Map) {
                    @SuppressWarnings("unchecked") Map<String, Object> h = (Map<String, Object>) o;
                    if (Json.s(h, "name").equals(Json.s(x, "name")) && Json.s(h, "date").startsWith(today)) {
                        hist.remove(i);
                        break;
                    }
                }
            }
        }
        scheduleSave();
        render();
    }

    private void clearDone() {
        if (groceries == null) {
            return;
        }
        List<Object> items = Json.arr(groceries, "items");
        for (int i = items.size() - 1; i >= 0; i--) {
            Object o = items.get(i);
            if (o instanceof Map && Json.b(castOrEmpty(o), "bought")) {
                items.remove(i);
            }
        }
        scheduleSave();
        render();
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> castOrEmpty(Object o) {
        return o instanceof Map ? (Map<String, Object>) o : new LinkedHashMap<>();
    }

    private void addItem(String name, long need, long price) {
        for (Map<String, Object> x : list("items")) {   // 同じ品が未購入であれば足さない
            if (name.equals(Json.s(x, "name")) && !Json.b(x, "bought")) {
                toast("「" + name + "」はもうリストにあります");
                return;
            }
        }
        Map<String, Object> rec = new LinkedHashMap<>();
        rec.put("id", newId());
        rec.put("name", name);
        rec.put("need", Json.RawNum.of(need));
        rec.put("qty", Json.RawNum.of(1));
        rec.put("price", Json.RawNum.of(price));
        rec.put("bought", false);
        rec.put("added", nowText());
        Json.arr(groceries, "items").add(rec);
        scheduleSave();
    }

    private void toStaples(Map<String, Object> x) {
        for (Map<String, Object> s : list("staples")) {
            if (Json.s(s, "name").equals(Json.s(x, "name"))) {
                toast("もう定番にあります");
                return;
            }
        }
        Map<String, Object> rec = new LinkedHashMap<>();
        rec.put("id", newId());
        rec.put("name", Json.s(x, "name"));
        rec.put("need", Json.RawNum.of(Json.n(x, "need", 2)));
        rec.put("price", Json.RawNum.of(Json.n(x, "price", 0)));
        Json.arr(groceries, "staples").add(rec);
        scheduleSave();
        toast("定番に登録しました");
    }

    // ================= 一覧を描く =================
    private void render() {
        listBox.removeAllViews();
        tabList.setTypeface(null, showStaples ? Typeface.NORMAL : Typeface.BOLD);
        tabStaples.setTypeface(null, showStaples ? Typeface.BOLD : Typeface.NORMAL);
        tabList.setBackgroundColor(showStaples ? Color.rgb(233, 236, 239) : Color.rgb(208, 235, 255));
        tabStaples.setBackgroundColor(showStaples ? Color.rgb(208, 235, 255) : Color.rgb(233, 236, 239));
        if (groceries == null) {
            listBox.addView(text(fileUri == null ? "右上の「ファイル」から、Googleドライブにある Mind_Navi のデータファイル（.json）を選んでください。"
                    : "読み込んでいます…", 15, false));
            totalView.setText("");
            countView.setText("");
            return;
        }
        if (showStaples) {
            renderStaples();
        } else {
            renderItems();
        }
        renderTotals();
    }

    // ---- 欄（PC版と同じ。データファイルの view.groceries.layout を読む） ----
    private static final String[][] DEFAULT_COLS = {
            {"chk", "購入", "46"}, {"name", "品名", "190"}, {"qty", "個数", "46"}, {"price", "価格", "80"},
            {"sub", "小計", "84"}, {"need", "必要度", "70"}, {"wk", "週", "38"}, {"mo", "月", "38"}, {"yr", "年", "42"}};

    private List<String[]> columns() {
        List<String[]> out = new ArrayList<>();
        Object lay = groceries == null ? null : groceries.get("layout");
        if (lay instanceof Map) {
            Object cols = ((Map<?, ?>) lay).get("columns");
            if (cols instanceof List) {
                for (Object c : (List<?>) cols) {
                    if (c instanceof List && ((List<?>) c).size() >= 2) {
                        List<?> l = (List<?>) c;
                        String w = l.size() >= 3 && l.get(2) != null ? l.get(2).toString() : "60";
                        out.add(new String[]{String.valueOf(l.get(0)), String.valueOf(l.get(1)), w});
                    }
                }
            }
        }
        if (out.isEmpty()) {
            for (String[] c : DEFAULT_COLS) {
                out.add(c);
            }
        }
        return out;
    }

    private int colWidth(String[] c) {
        int w;
        try {
            w = (int) Double.parseDouble(c[2]);
        } catch (NumberFormatException e) {
            w = 60;
        }
        if ("name".equals(c[0])) {
            return dp(Math.max(140, (int) (w * 0.8)));
        }
        return dp(Math.max(40, (int) (w * 0.9)));
    }

    private static long qty(Map<String, Object> x) {
        return Math.max(1, Json.n(x, "qty", 1));
    }

    private static long sub(Map<String, Object> x) {
        return qty(x) * Json.n(x, "price", 0);
    }

    private TextView cellText(String s, boolean bold, int gravity) {
        TextView t = text(s, 14, bold);
        t.setGravity(gravity | Gravity.CENTER_VERTICAL);
        t.setPadding(dp(2), dp(4), dp(2), dp(4));
        return t;
    }

    private void renderItems() {
        List<Map<String, Object>> items = list("items");
        items.sort(new java.util.Comparator<Map<String, Object>>() {
            @Override
            public int compare(Map<String, Object> a, Map<String, Object> b) {   // 未購入 → 必要度（高い順） → 追加した順
                int c = Boolean.compare(Json.b(a, "bought"), Json.b(b, "bought"));
                if (c != 0) {
                    return c;
                }
                c = Long.compare(Json.n(a, "need", 2), Json.n(b, "need", 2));
                return c != 0 ? c : Json.s(a, "added").compareTo(Json.s(b, "added"));
            }
        });
        List<String[]> cols = columns();
        android.widget.HorizontalScrollView hs = new android.widget.HorizontalScrollView(this);
        LinearLayout table = new LinearLayout(this);
        table.setOrientation(LinearLayout.VERTICAL);
        hs.addView(table);
        LinearLayout head = row();   // 見出し（PC版と同じ並び）
        head.setBackgroundColor(Color.rgb(241, 243, 245));
        for (String[] c : cols) {
            TextView t = cellText(c[1], true, "name".equals(c[0]) ? Gravity.START : Gravity.CENTER);
            t.setTextColor(Color.DKGRAY);
            head.addView(t, new LinearLayout.LayoutParams(colWidth(c), ViewGroup.LayoutParams.WRAP_CONTENT));
        }
        table.addView(head);
        for (Map<String, Object> x : items) {
            table.addView(itemRow(x, cols));
        }
        // 新しい品の行：品名の欄に直接入力して追加
        LinearLayout nr = row();
        for (String[] c : cols) {
            if ("name".equals(c[0])) {
                final EditText ne = edit("", "＋ 新しい品", false);
                ne.setImeOptions(EditorInfo.IME_ACTION_DONE);
                ne.setOnEditorActionListener(new TextView.OnEditorActionListener() {
                    @Override
                    public boolean onEditorAction(TextView v, int actionId, android.view.KeyEvent ev) {
                        String t = ne.getText().toString().trim();
                        if (!t.isEmpty()) {
                            long need = 2, price = 0;
                            for (Map<String, Object> s : list("staples")) {   // 定番にあれば価格・必要度も
                                if (Json.s(s, "name").equals(t)) {
                                    need = Json.n(s, "need", 2);
                                    price = Json.n(s, "price", 0);
                                }
                            }
                            addItem(t, need, price);
                            render();
                            focusNewRow();
                        }
                        return true;
                    }
                });
                nr.addView(ne, new LinearLayout.LayoutParams(colWidth(c), ViewGroup.LayoutParams.WRAP_CONTENT));
            } else {
                nr.addView(new View(this), new LinearLayout.LayoutParams(colWidth(c), 1));
            }
        }
        newRow = nr;
        table.addView(nr);
        // いちばん下：総計
        long tq = 0, ts = 0;
        for (Map<String, Object> x : items) {
            tq += qty(x);
            ts += sub(x);
        }
        LinearLayout tr = row();
        tr.setBackgroundColor(Color.rgb(231, 245, 255));
        for (String[] c : cols) {
            String v = "name".equals(c[0]) ? "総計" : "qty".equals(c[0]) ? Long.toString(tq) : "sub".equals(c[0]) ? yen(ts) : "";
            TextView t = cellText(v, true, "name".equals(c[0]) ? Gravity.START : "sub".equals(c[0]) ? Gravity.END : Gravity.CENTER);
            t.setTextColor(Color.rgb(24, 100, 171));
            tr.addView(t, new LinearLayout.LayoutParams(colWidth(c), ViewGroup.LayoutParams.WRAP_CONTENT));
        }
        table.addView(tr);
        listBox.addView(hs, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
    }

    private LinearLayout newRow;

    private void focusNewRow() {
        if (newRow == null) {
            return;
        }
        for (int i = 0; i < newRow.getChildCount(); i++) {
            if (newRow.getChildAt(i) instanceof EditText) {
                newRow.getChildAt(i).requestFocus();
                return;
            }
        }
    }

    private View itemRow(final Map<String, Object> x, List<String[]> cols) {
        boolean bought = Json.b(x, "bought");
        LinearLayout r = row();
        r.setPadding(0, dp(1), 0, dp(1));
        for (String[] c : cols) {
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(colWidth(c), ViewGroup.LayoutParams.WRAP_CONTENT);
            String k = c[0];
            if ("chk".equals(k)) {
                CheckBox cb = new CheckBox(this);
                cb.setChecked(bought);
                cb.setOnCheckedChangeListener(new android.widget.CompoundButton.OnCheckedChangeListener() {
                    @Override
                    public void onCheckedChanged(android.widget.CompoundButton v, boolean on) {
                        toggleBought(x, on);
                    }
                });
                r.addView(cb, lp);
            } else if ("name".equals(k)) {
                final EditText name = edit(Json.s(x, "name"), "品名", false);   // 品名：その場で書きかえ
                if (bought) {
                    name.setTextColor(Color.GRAY);
                }
                commitOnLeave(name, new Runnable() {
                    @Override
                    public void run() {
                        String t = name.getText().toString().trim();
                        if (!t.isEmpty() && !t.equals(Json.s(x, "name"))) {
                            x.put("name", t);
                            scheduleSave();
                        }
                    }
                });
                r.addView(name, lp);
            } else if ("qty".equals(k) || "price".equals(k)) {
                final String key = k;
                long pv = "qty".equals(k) ? qty(x) : Json.n(x, "price", 0);
                final EditText e = edit(pv == 0 ? "" : Long.toString(pv), "qty".equals(k) ? "1" : "¥", true);
                commitOnLeave(e, new Runnable() {
                    @Override
                    public void run() {
                        String t = e.getText().toString().replace(",", "").trim();
                        long v;
                        try {
                            v = t.isEmpty() ? ("qty".equals(key) ? 1 : 0) : Long.parseLong(t);
                        } catch (NumberFormatException ex) {
                            toast("数字で入力してください");
                            return;
                        }
                        if ("qty".equals(key)) {
                            v = Math.max(1, v);
                        }
                        long old = "qty".equals(key) ? qty(x) : Json.n(x, "price", 0);
                        if (v != old) {
                            x.put(key, Json.RawNum.of(v));
                            scheduleSave();
                            render();
                        }
                    }
                });
                r.addView(e, lp);
            } else if ("sub".equals(k)) {
                r.addView(cellText(Json.n(x, "price", 0) == 0 ? "―" : yen(sub(x)), false, Gravity.END), lp);
            } else if ("need".equals(k)) {   // 必要度：タップで一覧（高・中・低）から選ぶ（ふだんは中）
                r.addView(needPicker((int) Json.n(x, "need", 2), new IntCallback() {
                    @Override
                    public void on(long v) {
                        if (v != Json.n(x, "need", 2)) {
                            x.put("need", Json.RawNum.of(v));
                            scheduleSave();
                            render();
                        }
                    }
                }), lp);
            } else if ("wk".equals(k) || "mo".equals(k) || "yr".equals(k)) {
                long[] cn = counts(Json.s(x, "name"));
                long v = "wk".equals(k) ? cn[0] : "mo".equals(k) ? cn[1] : cn[2];
                TextView t = cellText(v == 0 ? "" : Long.toString(v), false, Gravity.CENTER);
                t.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        itemMenu(x);
                    }
                });
                r.addView(t, lp);
            } else {
                r.addView(cellText("", false, Gravity.CENTER), lp);
            }
        }
        r.setOnLongClickListener(new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                itemMenu(x);
                return true;
            }
        });
        return r;
    }

    private void itemMenu(Map<String, Object> x) {
        new AlertDialog.Builder(this)
                .setTitle(Json.s(x, "name"))
                .setItems(new String[]{"定番に登録", "削除"}, new android.content.DialogInterface.OnClickListener() {
            @Override
            public void onClick(android.content.DialogInterface d, int which) {
                    if (which == 0) {
                        toStaples(x);
                    } else {
                        Json.arr(groceries, "items").remove(x);
                        scheduleSave();
                        render();
                    }
                }
        })
                .show();
    }

    private void renderStaples() {
        List<Map<String, Object>> st = list("staples");
        st.sort(new java.util.Comparator<Map<String, Object>>() {
            @Override
            public int compare(Map<String, Object> a, Map<String, Object> b) {
            int c = Long.compare(Json.n(a, "need", 2), Json.n(b, "need", 2));
            return c != 0 ? c : Json.s(a, "name").compareTo(Json.s(b, "name"));
        }
        });
        java.util.Set<String> inList = new java.util.HashSet<>();
        for (Map<String, Object> x : list("items")) {
            if (!Json.b(x, "bought")) {
                inList.add(Json.s(x, "name"));
            }
        }
        listBox.addView(text("＋ で買い物リストへ（長押しで削除）", 13, false));
        for (Map<String, Object> s : st) {
            LinearLayout r = row();
            Button add = smallButton("＋");
            add.setEnabled(!inList.contains(Json.s(s, "name")));
            add.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                addItem(Json.s(s, "name"), Json.n(s, "need", 2), Json.n(s, "price", 0));
                toast("買い物リストに入れました");
                render();
            }
        });
            r.addView(add, new LinearLayout.LayoutParams(dp(56), ViewGroup.LayoutParams.WRAP_CONTENT));
            EditText name = edit(Json.s(s, "name"), "品名", false);
            if (inList.contains(Json.s(s, "name"))) {
                name.setTextColor(Color.GRAY);
            }
            commitOnLeave(name, new Runnable() {
            @Override
            public void run() {
                String t = name.getText().toString().trim();
                if (!t.isEmpty() && !t.equals(Json.s(s, "name"))) {
                    s.put("name", t);
                    scheduleSave();
                }
            }
        });
            r.addView(name, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
            long pv = Json.n(s, "price", 0);
            EditText price = edit(pv == 0 ? "" : Long.toString(pv), "¥", true);
            commitOnLeave(price, new Runnable() {
            @Override
            public void run() {
                String t = price.getText().toString().replace(",", "").trim();
                try {
                    long v = t.isEmpty() ? 0 : Long.parseLong(t);
                    if (v != Json.n(s, "price", 0)) {
                        s.put("price", Json.RawNum.of(v));
                        scheduleSave();
                    }
                } catch (NumberFormatException e) {
                    toast("価格は数字で入力してください");
                }
            }
        });
            r.addView(price, new LinearLayout.LayoutParams(dp(80), ViewGroup.LayoutParams.WRAP_CONTENT));
            r.addView(needPicker((int) Json.n(s, "need", 2), new IntCallback() {
            @Override
            public void on(long v) {
                if (v != Json.n(s, "need", 2)) {
                    s.put("need", Json.RawNum.of(v));
                    scheduleSave();
                    render();
                }
            }
        }), new LinearLayout.LayoutParams(dp(76), ViewGroup.LayoutParams.WRAP_CONTENT));
            View.OnLongClickListener del = new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                new AlertDialog.Builder(MainActivity.this).setTitle("「" + Json.s(s, "name") + "」を定番から外しますか？")
                        .setPositiveButton("外す", new android.content.DialogInterface.OnClickListener() {
            @Override
            public void onClick(android.content.DialogInterface d, int w) {
                            Json.arr(groceries, "staples").remove(s);
                            scheduleSave();
                            render();
                        }
        })
                        .setNegativeButton("やめる", null).show();
                return true;
            }
        };
            r.setOnLongClickListener(del);
            add.setOnLongClickListener(del);
            listBox.addView(r);
        }
        LinearLayout nr = row();   // いちばん下の行：ここに直接入力して定番を追加
        EditText ne = edit("", "＋ 新しい定番（ここに入力）", false);
        ne.setImeOptions(EditorInfo.IME_ACTION_DONE);
        ne.setOnEditorActionListener(new TextView.OnEditorActionListener() {
            @Override
            public boolean onEditorAction(TextView v, int actionId, android.view.KeyEvent ev) {
            String t = ne.getText().toString().trim();
            if (!t.isEmpty()) {
                Map<String, Object> x = new LinkedHashMap<>();
                x.put("name", t);
                x.put("need", Json.RawNum.of(2));
                x.put("price", Json.RawNum.of(0));
                toStaples(x);
                render();
                focusNewRow();
            }
            return true;
        }
        });
        nr.addView(ne, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        listBox.addView(nr);
    }

    private void renderTotals() {
        if (groceries == null) {
            return;
        }
        long todoN = 0, todoP = 0, doneN = 0, doneP = 0;
        for (Map<String, Object> x : list("items")) {
            long p = sub(x);
            if (Json.b(x, "bought")) {
                doneN++;
                doneP += p;
            } else {
                todoN++;
                todoP += p;
            }
        }
        totalView.setText("未購入 " + todoN + "品 " + yen(todoP) + "　購入済み " + doneN + "品 " + yen(doneP)
                + "　合計 " + yen(todoP + doneP));
        LocalDate today = LocalDate.now();
        LocalDate mon = today.minusDays(today.getDayOfWeek().getValue() - 1);
        long wk = 0, mo = 0, yr = 0, wkP = 0, moP = 0, yrP = 0;
        for (Map<String, Object> h : list("history")) {
            LocalDate d;
            try {
                d = LocalDate.parse(Json.s(h, "date").substring(0, 10));
            } catch (Exception e) {
                continue;
            }
            long p = Json.n(h, "price", 0);
            if (d.getYear() == today.getYear()) {
                yr++;
                yrP += p;
                if (d.getMonthValue() == today.getMonthValue()) {
                    mo++;
                    moP += p;
                }
            }
            if (!d.isBefore(mon) && ChronoUnit.DAYS.between(d, today) >= 0) {
                wk++;
                wkP += p;
            }
        }
        countView.setText("購入回数　今週 " + wk + "回（" + yen(wkP) + "）・今月 " + mo + "回（" + yen(moP) + "）・今年 "
                + yr + "回（" + yen(yrP) + "）");
        clearDoneBtn.setVisibility(showStaples ? View.GONE : View.VISIBLE);
    }

    // ================= 小さな部品 =================
    private interface IntCallback {
        void on(long v);
    }

    /** 必要度：タップすると 高・中・低 の一覧が出て選ぶ（PC版と同じ操作） */
    private View needPicker(final int cur, final IntCallback cb) {
        final TextView t = cellText(NEED[Math.max(0, Math.min(2, cur - 1))] + " ▾", true, Gravity.CENTER);
        t.setTextColor(cur == 1 ? Color.rgb(201, 42, 42) : Color.rgb(33, 37, 41));
        t.setBackgroundColor(Color.rgb(241, 243, 245));
        t.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                new AlertDialog.Builder(MainActivity.this).setTitle("必要度")
                        .setSingleChoiceItems(NEED, Math.max(0, Math.min(2, cur - 1)),
                                new android.content.DialogInterface.OnClickListener() {
                                    @Override
                                    public void onClick(android.content.DialogInterface d, int which) {
                                        d.dismiss();
                                        cb.on(which + 1);
                                    }
                                }).show();
            }
        });
        return t;
    }

    private void commitOnLeave(EditText e, Runnable commit) {
        e.setOnFocusChangeListener(new View.OnFocusChangeListener() {
            @Override
            public void onFocusChange(View v, boolean has) {
            if (!has) {
                commit.run();
            }
        }
        });
        e.setImeOptions(EditorInfo.IME_ACTION_DONE);
        e.setOnEditorActionListener(new TextView.OnEditorActionListener() {
            @Override
            public boolean onEditorAction(TextView v, int actionId, android.view.KeyEvent ev) {
            commit.run();
            e.clearFocus();
            return false;
        }
        });
    }

    private LinearLayout row() {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        r.setGravity(Gravity.CENTER_VERTICAL);
        return r;
    }

    private TextView text(String s, int sp, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        t.setTextColor(Color.rgb(33, 37, 41));
        if (bold) {
            t.setTypeface(null, Typeface.BOLD);
        }
        return t;
    }

    private TextView label(String s, int widthDp) {
        TextView t = text(s, 12, true);
        t.setTextColor(Color.GRAY);
        if (widthDp > 0) {
            t.setLayoutParams(new LinearLayout.LayoutParams(dp(widthDp), ViewGroup.LayoutParams.WRAP_CONTENT));
        }
        return t;
    }

    private EditText edit(String value, String hint, boolean number) {
        EditText e = new EditText(this);
        e.setText(value);
        e.setHint(hint);
        e.setSingleLine(true);
        e.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        e.setInputType(number ? InputType.TYPE_CLASS_NUMBER : InputType.TYPE_CLASS_TEXT);
        if (number) {
            e.setGravity(Gravity.END);
        }
        return e;
    }

    private Button smallButton(String s) {
        Button b = new Button(this);
        b.setText(s);
        b.setAllCaps(false);
        b.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        return b;
    }

    private Button tabButton(String s) {
        Button b = smallButton(s);
        b.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15);
        return b;
    }

    private static String yen(long v) {
        return String.format("¥%,d", v);
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private void status(String s) {
        statusView.setText(s);
    }

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_SHORT).show();
    }
}
// # END OF FILE
