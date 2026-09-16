#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import sys
import gzip
import base64
import hashlib
import subprocess
import time


# ============================================================
# 配置
# ============================================================

# 每个二维码携带的数据量。
#
# SecureCRT + 手机摄像头场景建议不要太大。
# 1000~1400 比较稳妥。
CHUNK_SIZE = 1200

# QR Code 容错等级
# L/M/Q/H
QR_LEVEL = "M"

# 二维码边距
QR_MARGIN = "4"


# ============================================================
# 工具函数
# ============================================================

def clear_screen():
    """
    清除 SecureCRT 当前屏幕。
    """
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def find_command(command):

    path_env = os.environ.get("PATH", "")

    for path in path_env.split(os.pathsep):

        if not path:
            continue

        full_path = os.path.join(path, command)

        if os.path.isfile(full_path) and \
           os.access(full_path, os.X_OK):

            return full_path

    return None


def sha256_file(filename):

    h = hashlib.sha256()

    f = open(filename, "rb")

    try:

        while True:

            data = f.read(1024 * 1024)

            if not data:
                break

            h.update(data)

    finally:

        f.close()

    return h.hexdigest()


def gzip_data(filename):

    import StringIO

    f = open(filename, "rb")

    try:
        data = f.read()
    finally:
        f.close()

    output = StringIO.StringIO()

    gz = gzip.GzipFile(
        fileobj=output,
        mode="wb",
        compresslevel=9
    )

    try:
        gz.write(data)
    finally:
        gz.close()

    return output.getvalue()

def make_qr(qrencode, payload):

    cmd = [
        qrencode,
        "-t",
        "ANSIUTF8",

        "-l",
        QR_LEVEL,

        "-m",
        QR_MARGIN,

        "-8",

        payload
    ]

    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, stderr = p.communicate()

    if p.returncode != 0:

        print("")
        print("qrencode failed:")
        print(stderr)
        sys.exit(1)

    return stdout


# ============================================================
# 主程序
# ============================================================

def main():

    if len(sys.argv) != 2:

        print("")
        print("Usage:")
        print("")
        print("  python qr_display.py <file>")
        print("")
        print("Example:")
        print("")
        print("  python qr_display.py test.txt")
        print("")

        sys.exit(1)

    filename = sys.argv[1]

    # --------------------------------------------------------
    # 检查文件
    # --------------------------------------------------------

    if not os.path.isfile(filename):

        print("")
        print("ERROR: file not found:")
        print(filename)
        print("")

        sys.exit(1)

    # --------------------------------------------------------
    # qrencode
    # --------------------------------------------------------

    qrencode = find_command("qrencode")

    if not qrencode:

        print("")
        print("ERROR: qrencode not found.")
        print("")

        sys.exit(1)

    # --------------------------------------------------------
    # 文件信息
    # --------------------------------------------------------

    filename = os.path.abspath(filename)

    original_filename = os.path.basename(filename)

    filesize = os.path.getsize(filename)

    print("")
    print("=" * 70)
    print(" QR FILE TRANSFER")
    print("=" * 70)
    print("")
    print("File       : %s" % original_filename)
    print("Size       : %d bytes" % filesize)

    # --------------------------------------------------------
    # SHA256
    # --------------------------------------------------------

    print("")
    print("Calculating SHA256...")

    sha256 = sha256_file(filename)

    print("")
    print("SHA256:")
    print(sha256)

    # --------------------------------------------------------
    # gzip
    # --------------------------------------------------------

    print("")
    print("Compressing...")

    compressed = gzip_data(filename)

    print(
        "Compressed : %d bytes" %
        len(compressed)
    )

    # --------------------------------------------------------
    # Base64
    # --------------------------------------------------------

    encoded = base64.b64encode(compressed)

    # --------------------------------------------------------
    # filename Base64
    # --------------------------------------------------------

    filename_b64 = base64.b64encode(
        original_filename
    )

    # --------------------------------------------------------
    # Transfer ID
    # --------------------------------------------------------

    transfer_id = (
        sha256[:12] +
        "_" +
        str(int(time.time()))
    )

    # --------------------------------------------------------
    # 分片
    # --------------------------------------------------------

    total = (
        len(encoded) +
        CHUNK_SIZE -
        1
    ) / CHUNK_SIZE

    print(
        "QR count   : %d" %
        total
    )

    print("")
    print("=" * 70)
    print("")

    # --------------------------------------------------------
    # 等待用户
    # --------------------------------------------------------

    raw_input(
        "Press ENTER to start..."
    )

    # --------------------------------------------------------
    # 逐二维码显示
    # --------------------------------------------------------

    for index in range(total):

        start = (
            index *
            CHUNK_SIZE
        )

        end = min(
            start +
            CHUNK_SIZE,
            len(encoded)
        )

        chunk = encoded[start:end]

        # ----------------------------------------------------
        # 数据格式
        #
        # QRF1
        # transfer_id
        # total
        # index
        # sha256
        # filename
        # data
        # ----------------------------------------------------

        payload = (
            "QRF1|%s|%d|%d|%s|%s|%s" %
            (
                transfer_id,
                total,
                index,
                sha256,
                filename_b64,
                chunk
            )
        )

        qr = make_qr(
            qrencode,
            payload
        )

        clear_screen()

        print("")
        print(
            "QR FILE TRANSFER    [%d / %d]" %
            (
                index + 1,
                total
            )
        )

        print("")
        print(
            "File : %s" %
            original_filename
        )

        print(
            "Size : %d bytes" %
            filesize
        )

        print("")
        print("Scan this QR code:")
        print("")

        # 输出二维码
        sys.stdout.write(qr)
        sys.stdout.flush()

        print("")
        print("")
        print(
            "Chunk %d / %d" %
            (
                index + 1,
                total
            )
        )

        if index < total - 1:

            print("")
            print(
                "Scan completed? Press ENTER for next..."
            )

            raw_input()

        else:

            print("")
            print(
                "ALL QR CODES DISPLAYED."
            )

            print("")
            print(
                "Press ENTER to exit."
            )

            raw_input()

    # --------------------------------------------------------
    # 完成
    # --------------------------------------------------------

    clear_screen()

    print("")
    print("=" * 70)
    print(" QR TRANSFER FINISHED")
    print("=" * 70)
    print("")

    print(
        "File   : %s" %
        original_filename
    )

    print(
        "Size   : %d bytes" %
        filesize
    )

    print(
        "Chunks : %d" %
        total
    )

    print("")
    print(
        "SHA256 : %s" %
        sha256
    )

    print("")
    print("")


if __name__ == "__main__":
    main()
