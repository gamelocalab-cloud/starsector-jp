#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Starsector 日本語化パッチャー (game_loca_lab)
対象バージョン: Starsector 0.98a-RC8

あなたの PC にある正規の jar ファイルに対して、文字列だけを日本語に
書き換えます。jar 本体は配布していません。このスクリプトが読み書き
するのは、あなた自身のゲームファイルだけです。

使い方:
  python apply_patch.py [Starsector インストールフォルダ]
  python apply_patch.py --restore [フォルダ]   元に戻す

フォルダを省略すると、カレントフォルダとその周辺から自動検出します。
初回適用時に starfarer.api.jar.orig / starfarer_obfuscated.jar.orig
という名前で元ファイルを自動バックアップします。
"""
import hashlib
import io
import json
import os
import shutil
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "patch_data.json"), encoding="utf-8"))
CORE_FILES = ["tips.json", "ship_names.json"]


# ---------- class file constant-pool patching ----------
def mutf8_encode(s):
    out = bytearray()
    for ch in s:
        cp = ord(ch)
        if cp == 0:
            out += b"\xc0\x80"
        elif cp < 0x80:
            out.append(cp)
        elif cp < 0x800:
            out.append(0xC0 | (cp >> 6)); out.append(0x80 | (cp & 0x3F))
        elif cp < 0x10000:
            out.append(0xE0 | (cp >> 12)); out.append(0x80 | ((cp >> 6) & 0x3F)); out.append(0x80 | (cp & 0x3F))
        else:
            v = cp - 0x10000
            for u in (0xD800 + (v >> 10), 0xDC00 + (v & 0x3FF)):
                out.append(0xE0 | (u >> 12)); out.append(0x80 | ((u >> 6) & 0x3F)); out.append(0x80 | (u & 0x3F))
    return bytes(out)


def parse_entries(data):
    """Yield (index, tag, start, end, payload) per constant-pool entry."""
    cp_count = struct.unpack(">H", data[8:10])[0]
    pos = 10
    entries = []
    i = 1
    while i < cp_count:
        start = pos
        tag = data[pos]
        pos += 1
        if tag == 1:
            ln = struct.unpack(">H", data[pos:pos + 2])[0]
            entries.append((i, tag, start, pos + 2 + ln, data[pos + 2:pos + 2 + ln]))
            pos += 2 + ln
        elif tag in (7, 8, 16, 19, 20):
            entries.append((i, tag, start, pos + 2, data[pos:pos + 2]))
            pos += 2
        elif tag == 15:
            entries.append((i, tag, start, pos + 3, None))
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            entries.append((i, tag, start, pos + 4, None))
            pos += 4
        elif tag in (5, 6):
            entries.append((i, tag, start, pos + 8, None))
            pos += 8
            i += 1
        else:
            raise ValueError("bad tag %d" % tag)
        i += 1
    return entries, pos


def patch_class(data, mapping):
    """Replace only String-referenced Utf8 payloads.

    Safety rule: an entry that is ALSO referenced by a NameAndType
    (method/field name) is never replaced, even if it is in the map.
    (A shared entry once caused a NoSuchMethodError crash.)
    """
    entries, cp_end = parse_entries(data)
    string_idxs = set()
    nat_idxs = set()
    for (i, tag, s, e, payload) in entries:
        if tag == 8:
            string_idxs.add(struct.unpack(">H", payload)[0])
        elif tag == 12:
            a, b = struct.unpack(">HH", data[s + 1:s + 5])
            nat_idxs.add(a)
            nat_idxs.add(b)
    out = bytearray(data[:10])
    changed = 0
    skipped = 0
    for (i, tag, s, e, payload) in entries:
        if tag == 1 and i in string_idxs:
            try:
                val = payload.decode("utf-8")
            except UnicodeDecodeError:
                val = None
            if val in mapping:
                if i in nat_idxs:
                    skipped += 1
                    out += data[s:e]
                    continue
                nb = mutf8_encode(mapping[val])
                out.append(1)
                out += struct.pack(">H", len(nb))
                out += nb
                changed += 1
                continue
        out += data[s:e]
    out += data[cp_end:]
    return bytes(out), changed, skipped


# ---------- helpers ----------
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_core_dir(arg):
    cands = []
    if arg:
        cands += [arg, os.path.join(arg, "starsector-core")]
    cwd = os.getcwd()
    cands += [cwd, os.path.join(cwd, "starsector-core"),
              os.path.dirname(cwd), os.path.join(os.path.dirname(cwd), "starsector-core"),
              r"C:\Program Files (x86)\Fractal Softworks\Starsector\starsector-core",
              r"C:\Program Files\Fractal Softworks\Starsector\starsector-core"]
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "starfarer.api.jar")):
            return c
    return None


def class_string_values(data):
    entries, _ = parse_entries(data)
    string_idxs = set()
    vals = {}
    for (i, tag, s, e, payload) in entries:
        if tag == 8:
            string_idxs.add(struct.unpack(">H", payload)[0])
        elif tag == 1:
            try:
                vals[i] = payload.decode("utf-8")
            except UnicodeDecodeError:
                pass
    return {vals[i] for i in string_idxs if i in vals}


def jar_state(jar_path, spec):
    """Return 'original', 'patched', or 'unknown'."""
    if sha256(jar_path) == spec["orig_sha256"]:
        return "original"
    try:
        z = zipfile.ZipFile(jar_path)
    except Exception:
        return "unknown"
    remaining = 0
    for name, mp in spec["classes"].items():
        try:
            vals = class_string_values(z.read(name))
        except KeyError:
            return "unknown"
        remaining += sum(1 for en in mp if en in vals)
    return "patched" if remaining == 0 else "unknown"


def apply_jar(jar_path, spec):
    state = jar_state(jar_path, spec)
    name = os.path.basename(jar_path)
    if state == "patched":
        print("  %s: 適用済みのためスキップ" % name)
        return True
    if state == "unknown":
        print("  %s: 対象バージョン (0.98a-RC8) と一致しません。中止します。" % name)
        print("    (ゲームのバージョンが違うか、他の Mod で改変済みの可能性があります)")
        return False
    backup = jar_path + ".orig"
    if not os.path.exists(backup):
        shutil.copy2(jar_path, backup)
        print("  バックアップ作成: %s" % os.path.basename(backup))
    z = zipfile.ZipFile(jar_path)
    buf = io.BytesIO()
    out = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
    total = 0
    skipped = 0
    for item in z.namelist():
        data = z.read(item)
        if item in spec["classes"]:
            data, n, sk = patch_class(data, spec["classes"][item])
            total += n
            skipped += sk
        out.writestr(item, data)
    out.close()
    with open(jar_path, "wb") as f:
        f.write(buf.getvalue())
    print("  %s: %d 箇所を日本語化しました" % (name, total))
    if skipped:
        print("    (安全のため %d 件の共有エントリを保護しました)" % skipped)
    return jar_state(jar_path, spec) == "patched"


def apply_core_files(core_dir):
    src_dir = os.path.join(HERE, "core_replace")
    dst_dir = os.path.join(core_dir, "data", "strings")
    for fn in CORE_FILES:
        src = os.path.join(src_dir, fn)
        dst = os.path.join(dst_dir, fn)
        if not os.path.isfile(src) or not os.path.isdir(dst_dir):
            continue
        if os.path.exists(dst) and open(dst, "rb").read() == open(src, "rb").read():
            print("  %s: 適用済みのためスキップ" % fn)
            continue
        backup = dst + ".orig"
        if os.path.exists(dst) and not os.path.exists(backup):
            shutil.copy2(dst, backup)
            print("  バックアップ作成: %s" % os.path.basename(backup))
        shutil.copy2(src, dst)
        print("  %s: 本体ファイルを差し替えました" % fn)


def restore(core_dir):
    ok = True
    for key in ("api", "obf"):
        jar = os.path.join(core_dir, DATA[key]["file_name"])
        backup = jar + ".orig"
        if os.path.exists(backup):
            shutil.copy2(backup, jar)
            print("  %s を元に戻しました" % DATA[key]["file_name"])
        else:
            print("  %s のバックアップがありません" % DATA[key]["file_name"])
            ok = False
    dst_dir = os.path.join(core_dir, "data", "strings")
    for fn in CORE_FILES:
        backup = os.path.join(dst_dir, fn + ".orig")
        if os.path.exists(backup):
            shutil.copy2(backup, os.path.join(dst_dir, fn))
            print("  %s を元に戻しました" % fn)
    return ok


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_restore = "--restore" in sys.argv
    core = find_core_dir(args[0] if args else None)
    if not core:
        print("Starsector の starsector-core フォルダが見つかりません。")
        print("インストールフォルダを引数で指定してください:")
        print("  python apply_patch.py \"E:\\Starsector\"")
        return 1
    print("対象: %s" % core)
    if do_restore:
        return 0 if restore(core) else 1
    ok = True
    for key in ("api", "obf"):
        jar = os.path.join(core, DATA[key]["file_name"])
        if not os.path.isfile(jar):
            print("  %s が見つかりません" % DATA[key]["file_name"])
            ok = False
            continue
        if not apply_jar(jar, DATA[key]):
            ok = False
    apply_core_files(core)
    if ok:
        print("完了。ゲームを起動して確認してください。")
        print("元に戻すとき: python apply_patch.py --restore")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
