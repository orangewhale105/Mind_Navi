// Mind_Navi 買い物リスト（Android）  VERSION 1.2（versionCode 3）  最終更新日 2026-11-08
package jp.mindnavi.shopping;

import android.util.JsonReader;
import android.util.JsonToken;

import java.io.IOException;
import java.io.StringReader;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Mind_Navi のデータファイル（JSON）を、書き方をできるだけ変えずに読み書きする。
 * ・キーの順番はそのまま（LinkedHashMap）
 * ・数は読んだときの書き方のまま保存（RawNum）。0.0 が 0 になるなどの変化を起こさない
 * ・書き出しは PC 版（Python の json.dumps(indent=2, ensure_ascii=False)）と同じ形
 * 買い物リスト以外の部分は、読んだ内容をそのまま書き戻す。
 */
public final class Json {

    private Json() {
    }

    /** 数（読んだときの文字のまま持つ） */
    public static final class RawNum {
        public final String text;

        public RawNum(String text) {
            this.text = text;
        }

        public static RawNum of(long v) {
            return new RawNum(Long.toString(v));
        }

        public long asLong() {
            try {
                return Long.parseLong(text);
            } catch (NumberFormatException e) {
                try {
                    return (long) Double.parseDouble(text);
                } catch (NumberFormatException e2) {
                    return 0;
                }
            }
        }

        @Override
        public String toString() {
            return text;
        }
    }

    // ---------- 読む ----------
    public static Object parse(String text) throws IOException {
        JsonReader r = new JsonReader(new StringReader(text));
        r.setLenient(false);
        Object v = read(r);
        r.close();
        return v;
    }

    private static Object read(JsonReader r) throws IOException {
        JsonToken t = r.peek();
        switch (t) {
            case BEGIN_OBJECT: {
                Map<String, Object> m = new LinkedHashMap<>();
                r.beginObject();
                while (r.hasNext()) {
                    String k = r.nextName();
                    m.put(k, read(r));
                }
                r.endObject();
                return m;
            }
            case BEGIN_ARRAY: {
                List<Object> a = new ArrayList<>();
                r.beginArray();
                while (r.hasNext()) {
                    a.add(read(r));
                }
                r.endArray();
                return a;
            }
            case STRING:
                return r.nextString();
            case NUMBER:
                return new RawNum(r.nextString());   // 数は書いてあったとおりの文字で
            case BOOLEAN:
                return r.nextBoolean();
            case NULL:
                r.nextNull();
                return null;
            default:
                throw new IOException("JSON の形が正しくありません: " + t);
        }
    }

    // ---------- 書く（Python の json.dumps(indent=2, ensure_ascii=False) と同じ形） ----------
    public static String dump(Object v) {
        StringBuilder sb = new StringBuilder();
        write(sb, v, 0);
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    private static void write(StringBuilder sb, Object v, int level) {
        if (v == null) {
            sb.append("null");
        } else if (v instanceof String) {
            str(sb, (String) v);
        } else if (v instanceof Boolean) {
            sb.append(((Boolean) v) ? "true" : "false");
        } else if (v instanceof RawNum) {
            sb.append(((RawNum) v).text);
        } else if (v instanceof Integer || v instanceof Long) {
            sb.append(v.toString());
        } else if (v instanceof Number) {
            double d = ((Number) v).doubleValue();
            sb.append(d == Math.rint(d) ? Long.toString((long) d) + ".0" : Double.toString(d));
        } else if (v instanceof Map) {
            Map<String, Object> m = (Map<String, Object>) v;
            if (m.isEmpty()) {
                sb.append("{}");
                return;
            }
            sb.append("{\n");
            int i = 0;
            for (Map.Entry<String, Object> e : m.entrySet()) {
                indent(sb, level + 1);
                str(sb, e.getKey());
                sb.append(": ");
                write(sb, e.getValue(), level + 1);
                if (++i < m.size()) {
                    sb.append(",");
                }
                sb.append("\n");
            }
            indent(sb, level);
            sb.append("}");
        } else if (v instanceof List) {
            List<Object> a = (List<Object>) v;
            if (a.isEmpty()) {
                sb.append("[]");
                return;
            }
            sb.append("[\n");
            for (int i = 0; i < a.size(); i++) {
                indent(sb, level + 1);
                write(sb, a.get(i), level + 1);
                if (i < a.size() - 1) {
                    sb.append(",");
                }
                sb.append("\n");
            }
            indent(sb, level);
            sb.append("]");
        } else {
            str(sb, v.toString());
        }
    }

    private static void indent(StringBuilder sb, int level) {
        for (int i = 0; i < level; i++) {
            sb.append("  ");
        }
    }

    private static void str(StringBuilder sb, String s) {
        sb.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"':
                    sb.append("\\\"");
                    break;
                case '\\':
                    sb.append("\\\\");
                    break;
                case '\n':
                    sb.append("\\n");
                    break;
                case '\r':
                    sb.append("\\r");
                    break;
                case '\t':
                    sb.append("\\t");
                    break;
                case '\b':
                    sb.append("\\b");
                    break;
                case '\f':
                    sb.append("\\f");
                    break;
                default:
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        sb.append('"');
    }

    // ---------- 取り出し・書き込みの小さな道具 ----------
    @SuppressWarnings("unchecked")
    public static Map<String, Object> obj(Map<String, Object> parent, String key) {
        Object v = parent.get(key);
        if (!(v instanceof Map)) {
            v = new LinkedHashMap<String, Object>();
            parent.put(key, v);
        }
        return (Map<String, Object>) v;
    }

    @SuppressWarnings("unchecked")
    public static List<Object> arr(Map<String, Object> parent, String key) {
        Object v = parent.get(key);
        if (!(v instanceof List)) {
            v = new ArrayList<Object>();
            parent.put(key, v);
        }
        return (List<Object>) v;
    }

    public static String s(Map<String, Object> m, String key) {
        Object v = m.get(key);
        return v == null ? "" : v.toString();
    }

    public static long n(Map<String, Object> m, String key, long dflt) {
        Object v = m.get(key);
        if (v instanceof RawNum) {
            return ((RawNum) v).asLong();
        }
        if (v instanceof Number) {
            return ((Number) v).longValue();
        }
        if (v instanceof String) {
            try {
                return Long.parseLong(((String) v).trim());
            } catch (NumberFormatException e) {
                return dflt;
            }
        }
        return dflt;
    }

    public static boolean b(Map<String, Object> m, String key) {
        Object v = m.get(key);
        return v instanceof Boolean && (Boolean) v;
    }
}
// # END OF FILE
