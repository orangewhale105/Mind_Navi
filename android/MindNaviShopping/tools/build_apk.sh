#!/bin/bash
# Mind_Navi 買い物アプリ（Android）の APK を、Gradle を使わずに作るスクリプト
# VERSION 1.2 / 最終更新日 2026-11-08
# 使い方：bash tools/build_apk.sh   （Ubuntu 24.04 で、次を apt で入れておく）
#   sudo apt-get install -y aapt android-sdk-platform-23 apksigner dalvik-exchange zipalign openjdk-21-jdk-headless
# versionCode / versionName は app/build.gradle から読む。
# 署名の鍵はリポジトリに入れない。実行前に次の2つを設定する（鍵とパスワードはリポジトリ外で保管）
#   export MIND_NAVI_KEYSTORE=/path/to/mind_navi.keystore   # 鍵の別名（alias）は旧名の taskmap のまま
#   export MIND_NAVI_KS_PASS=（パスワード）
set -e
: "${MIND_NAVI_KEYSTORE:?署名の鍵の場所を MIND_NAVI_KEYSTORE に設定してください}"
: "${MIND_NAVI_KS_PASS:?鍵のパスワードを MIND_NAVI_KS_PASS に設定してください}"
P=$(cd "$(dirname "$0")/.." && pwd)
B=${BUILD_DIR:-/tmp/mind_navi_apkbuild}
BT=/usr/lib/android-sdk/build-tools/debian
AJ=/usr/lib/android-sdk/platforms/android-23/android.jar
VC=$(grep -oP '^\s*versionCode \K\d+' $P/app/build.gradle); VN=$(grep -oP "^\s*versionName '\K[^']+" $P/app/build.gradle)
rm -rf $B; mkdir -p $B/gen $B/obj $B/dex
# Gradle 用の AndroidManifest.xml には package・uses-sdk が無いので、ここで足す
sed "s#<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\">#<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\" package=\"jp.mindnavi.shopping\" android:versionCode=\"$VC\" android:versionName=\"$VN\">\n    <uses-sdk android:minSdkVersion=\"26\" android:targetSdkVersion=\"34\" />#" $P/app/src/main/AndroidManifest.xml > $B/AndroidManifest.xml
cd $B
$BT/aapt package -f -m -J gen -M AndroidManifest.xml -S $P/app/src/main/res -I $AJ
# android.jar は API 23（apt で入るもの）。java.time などは JDK 側の定義でコンパイルし、実機（Android 8.0 以上）の実装を使う
javac --release 8 -encoding UTF-8 -Xlint:-options -classpath $AJ -d obj gen/jp/mindnavi/shopping/R.java $P/app/src/main/java/jp/mindnavi/shopping/*.java
# dx はラムダ式を変換できない（Android では動かない）ので、ソースではラムダ式を使わない（匿名クラスで書く）
$BT/dx --dex --min-sdk-version=26 --output=dex/classes.dex obj
if strings dex/classes.dex | grep -qi lambdametafactory; then echo "ラムダ式が含まれています（匿名クラスに書きかえてください）"; exit 1; fi
$BT/aapt package -f -M AndroidManifest.xml -S $P/app/src/main/res -I $AJ -F unsigned.apk
cp dex/classes.dex . && $BT/aapt add unsigned.apk classes.dex >/dev/null
zipalign -f -p 4 unsigned.apk aligned.apk
apksigner sign --ks "$MIND_NAVI_KEYSTORE" --ks-pass env:MIND_NAVI_KS_PASS --ks-key-alias taskmap --out MindNaviShopping_v$VN.apk aligned.apk
apksigner verify MindNaviShopping_v$VN.apk
$BT/aapt dump badging MindNaviShopping_v$VN.apk | head -1
echo "出力：$B/MindNaviShopping_v$VN.apk"
# # END OF FILE
