# -*- coding: utf-8 -*-
"""
文件夹加密压缩工具
用法：拖拽文件夹到此程序上，或用命令行：
    folder-encrypt.exe <文件夹路径>

功能：
1. 从文件夹名开头提取 8 位日期作为密码（如 20260812）
2. 内置 AES-256 加密压缩，文件内容与文件清单一并加密，不依赖 WinRAR 等外部程序
3. 输出 .7z 文件到原文件夹的上级目录
"""

import lzma
import os
import re
import sys

import py7zr

# 输出统一走 UTF-8。非中文 Windows 上，stdout 一旦重定向到管道或日志，
# Python 会按本地编码（例如 cp1252）编码，打中文直接抛 UnicodeEncodeError。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MB = 1048576

# LZMA2 压缩级别：1 最快，9 最慢。py7zr 默认是 7|PRESET_EXTREME，
# 实测比 5 级还慢、体积反而略大，纯属白花时间。定 1 级后 38MB 样本从 13.8 秒降到 2.9 秒，
# 代价是压缩包大约 38% 大。想换级别改这里重打包即可，输出格式与兼容性不受影响。
COMPRESS_PRESET = 1
COMPRESS_FILTERS = [{"id": lzma.FILTER_LZMA2, "preset": COMPRESS_PRESET}]


def pause():
    """双击运行时留住窗口；被脚本调用、没有标准输入时直接跳过。"""
    try:
        input("按回车退出...")
    except EOFError:
        pass


def collect_files(folder_path):
    """返回 [(绝对路径, 压缩包内相对路径)]，相对路径不含最外层文件夹名。"""
    items = []
    for root, dirs, files in os.walk(folder_path):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(root, name)
            items.append((full, os.path.relpath(full, folder_path)))
    return items


def make_archive(output_path, password, items):
    """先写临时文件，成功后再顶替目标文件，避免压缩失败时丢掉已有压缩包。"""
    tmp_path = output_path + ".part"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    skipped = []
    try:
        with py7zr.SevenZipFile(
            tmp_path,
            "w",
            password=password,
            header_encryption=True,
            filters=COMPRESS_FILTERS,
        ) as archive:
            for full, arcname in items:
                try:
                    archive.write(full, arcname)
                except OSError as exc:
                    skipped.append(f"{arcname}（{exc}）")
        os.replace(tmp_path, output_path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise
    return skipped


def process(folder_path):
    if not os.path.isdir(folder_path):
        print("[错误] 不是有效的文件夹: " + folder_path)
        return False

    folder_name = os.path.basename(os.path.normpath(folder_path))
    matched = re.match(r"^(\d{8})", folder_name)
    if not matched:
        print("[错误] 文件夹名不以 8 位日期开头: " + folder_name)
        print("文件夹名应为 YYYYMMDD 开头，例如: 20260812会议评审资料")
        return False

    password = matched.group(1)
    parent_dir = os.path.dirname(os.path.abspath(folder_path))
    output_path = os.path.join(parent_dir, folder_name + ".7z")

    if os.path.exists(output_path):
        print("[提示] 已存在 " + output_path + "，覆盖...")

    items = collect_files(folder_path)

    print("文件夹 : " + folder_name)
    print("密码   : " + password)
    print("输出   : " + output_path)
    print("文件数 : " + str(len(items)))
    print("正在加密压缩（AES-256，含文件名加密）...")
    print()

    try:
        skipped = make_archive(output_path, password, items)
    except Exception as exc:
        print("[FAIL] 压缩失败: " + str(exc))
        return False

    if skipped:
        print("[警告] " + str(len(skipped)) + " 个文件未能加入压缩包：")
        for line in skipped[:10]:
            print("  " + line)
        if len(skipped) > 10:
            print("  ...另有 " + str(len(skipped) - 10) + " 个")

    file_size = os.path.getsize(output_path)
    size_mb = file_size / MB

    print("[OK] 加密压缩完成！")
    print("  文件: " + output_path)
    print("  大小: " + f"{size_mb:.2f}" + " MB")
    print("  密码: " + password)
    return True


def main():
    if len(sys.argv) < 2:
        print("==================================================")
        print("  文件夹加密压缩工具")
        print("  用法：拖拽文件夹到此程序图标上")
        print("  或命令行：folder-encrypt.exe <文件夹路径>")
        print("==================================================")
        print()
        print("提示：文件夹名必须以 8 位日期开头")
        print("  例如：20260812会议评审资料 → 密码=20260812")
        print()
        pause()
        return

    all_ok = True
    for index, folder_path in enumerate(sys.argv[1:]):
        if index:
            print()
        if not process(folder_path):
            all_ok = False

    if not all_ok:
        print()
        pause()


if __name__ == "__main__":
    main()
