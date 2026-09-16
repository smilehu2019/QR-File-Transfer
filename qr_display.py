#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import sys
import gzip
import base64
import hashlib
import subprocess
import StringIO


MAGIC = "QRF1"


def usage():
    print("")
    print("=" * 70)
    print("QR FILE IMPORT")
    print("=" * 70)
    print("")
    print("Usage:")
    print("")
    print("  1. Import QR text:")
    print("")
    print("     python qr_import.py text qr_data.txt")
    print("")
    print("  2. Import QR images:")
    print("")
    print("     python qr_import.py image qr_images/")
    print("")
    print("Examples:")
    print("")
    print("  python qr_import.py text qr_data.txt")
    print("")
    print("  python qr_import.py image ./qr_images")
    print("")


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


def find_command(command):

    path_env = os.environ.get(
        "PATH",
        ""
    )

    for path in path_env.split(os.pathsep):

        if not path:
            continue

        full_path = os.path.join(
            path,
            command
        )

        if os.path.isfile(full_path) and \
           os.access(full_path, os.X_OK):

            return full_path

    return None


def parse_qr_payload(payload):

    payload = payload.strip()

    fields = payload.split("|", 6)

    if len(fields) != 7:

        raise Exception(
            "Invalid QR payload. Expected 7 fields."
        )

    magic = fields[0]

    if magic != MAGIC:

        raise Exception(
            "Invalid QR magic: %s" %
            magic
        )

    transfer_id = fields[1]

    try:

        total = int(fields[2])

    except ValueError:

        raise Exception(
            "Invalid total chunk count."
        )

    try:

        index = int(fields[3])

    except ValueError:

        raise Exception(
            "Invalid chunk index."
        )

    sha256 = fields[4]

    filename_b64 = fields[5]

    data = fields[6]

    if total <= 0:

        raise Exception(
            "Invalid total chunk count: %d" %
            total
        )

    if index < 0 or index >= total:

        raise Exception(
            "Invalid chunk index: %d" %
            index
        )

    if len(sha256) != 64:

        raise Exception(
            "Invalid SHA256."
        )

    try:

        filename = base64.b64decode(
            filename_b64
        )

    except Exception:

        raise Exception(
            "Invalid filename Base64."
        )

    filename = os.path.basename(
        filename
    )

    if not filename:

        filename = "recovered_file"

    return {
        "transfer_id": transfer_id,
        "total": total,
        "index": index,
        "sha256": sha256,
        "filename": filename,
        "data": data
    }


def decode_image(zbarimg, filename):

    cmd = [
        zbarimg,
        "--raw",
        filename
    ]

    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, stderr = p.communicate()

    if p.returncode != 0:

        raise Exception(
            "Cannot decode QR image: %s" %
            filename
        )

    result = stdout.strip()

    if not result:

        raise Exception(
            "QR image contains no data: %s" %
            filename
        )

    return result


def load_text_file(filename):

    print("")
    print("Reading QR text file:")
    print("  %s" % filename)
    print("")

    f = open(
        filename,
        "r"
    )

    try:

        lines = f.readlines()

    finally:

        f.close()

    payloads = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # 如果复制出来的内容前后有引号，去掉
        if len(line) >= 2:

            if line[0] == '"' and \
               line[-1] == '"':

                line = line[1:-1]

        if line.startswith(
            MAGIC + "|"
        ):

            payloads.append(
                line
            )

    return payloads


def load_image_directory(directory):

    zbarimg = find_command(
        "zbarimg"
    )

    if not zbarimg:

        print("")
        print("ERROR: zbarimg not found.")
        print("")
        print("Install it with:")
        print("")
        print("  yum install zbar")
        print("")

        sys.exit(1)

    files = []

    for name in os.listdir(
        directory
    ):

        lower = name.lower()

        if lower.endswith(".png") or \
           lower.endswith(".jpg") or \
           lower.endswith(".jpeg"):

            files.append(
                os.path.join(
                    directory,
                    name
                )
            )

    files.sort()

    if not files:

        print("")
        print("ERROR: no image files found.")
        print("")
        sys.exit(1)

    payloads = []

    print("")
    print(
        "Found %d image files." %
        len(files)
    )

    print("")

    for i, filename in enumerate(files):

        print(
            "[%d/%d] Decoding %s" %
            (
                i + 1,
                len(files),
                os.path.basename(
                    filename
                )
            )
        )

        try:

            payload = decode_image(
                zbarimg,
                filename
            )

            payloads.append(
                payload
            )

        except Exception as e:

            print(
                "  ERROR: %s" %
                str(e)
            )

            # 单张失败不立即退出
            # 后面统一报告缺片
            continue

    return payloads


def collect_chunks(payloads):

    chunks = {}

    transfer_id = None
    total = None
    expected_sha256 = None
    filename = None

    duplicate_count = 0

    print("")
    print("Parsing QR data...")
    print("")

    for pos, payload in enumerate(
        payloads
    ):

        try:

            item = parse_qr_payload(
                payload
            )

        except Exception as e:

            print(
                "WARNING: invalid QR #%d: %s" %
                (
                    pos + 1,
                    str(e)
                )
            )

            continue

        # ----------------------------------------------------
        # 第一个二维码初始化传输信息
        # ----------------------------------------------------

        if transfer_id is None:

            transfer_id = item[
                "transfer_id"
            ]

            total = item[
                "total"
            ]

            expected_sha256 = item[
                "sha256"
            ]

            filename = item[
                "filename"
            ]

            print(
                "Transfer ID : %s" %
                transfer_id
            )

            print(
                "Total chunks: %d" %
                total
            )

            print(
                "Filename    : %s" %
                filename
            )

            print(
                "SHA256      : %s" %
                expected_sha256
            )

        # ----------------------------------------------------
        # 检查传输 ID
        # ----------------------------------------------------

        if item["transfer_id"] != transfer_id:

            print(
                "WARNING: different transfer ID, ignored."
            )

            continue

        # ----------------------------------------------------
        # 检查总分片数
        # ----------------------------------------------------

        if item["total"] != total:

            print(
                "WARNING: different total count, ignored."
            )

            continue

        # ----------------------------------------------------
        # 检查 SHA256
        # ----------------------------------------------------

        if item["sha256"] != expected_sha256:

            print(
                "WARNING: different SHA256, ignored."
            )

            continue

        index = item[
            "index"
        ]

        # ----------------------------------------------------
        # 重复二维码
        # ----------------------------------------------------

        if index in chunks:

            if chunks[index] != item["data"]:

                print(
                    "ERROR: chunk %d has conflicting data." %
                    index
                )

                sys.exit(1)

            duplicate_count += 1

            continue

        # ----------------------------------------------------
        # 保存分片
        # ----------------------------------------------------

        chunks[index] = item[
            "data"
        ]

    print("")
    print(
        "Received : %d/%d chunks" %
        (
            len(chunks),
            total
        )
    )

    print(
        "Duplicate: %d" %
        duplicate_count
    )

    return (
        chunks,
        transfer_id,
        total,
        expected_sha256,
        filename
    )


def check_missing(chunks, total):

    missing = []

    for i in range(total):

        if i not in chunks:

            missing.append(i)

    if missing:

        print("")
        print("=" * 70)
        print("MISSING CHUNKS")
        print("=" * 70)
        print("")

        for i in missing:

            print(
                "  %05d" %
                i
            )

        print("")
        print(
            "Missing %d chunks." %
            len(missing)
        )

        print("")
        print(
            "Please scan/copy the missing QR codes."
        )

        print("")

        return False

    return True


def restore_file(
    chunks,
    total,
    expected_sha256,
    filename
):

    print("")
    print("Merging chunks...")

    encoded = ""

    for i in range(total):

        encoded += chunks[i]

    print(
        "Encoded size: %d bytes" %
        len(encoded)
    )

    # --------------------------------------------------------
    # Base64 decode
    # --------------------------------------------------------

    print("")
    print("Base64 decoding...")

    try:

        compressed = base64.b64decode(
            encoded
        )

    except Exception as e:

        print("")
        print("ERROR: Base64 decoding failed.")
        print(str(e))
        print("")

        sys.exit(1)

    print(
        "Compressed size: %d bytes" %
        len(compressed)
    )

    # --------------------------------------------------------
    # gzip
    # --------------------------------------------------------

    print("")
    print("Gzip decompressing...")

    try:

        stream = StringIO.StringIO(
            compressed
        )

        gz = gzip.GzipFile(
            fileobj=stream,
            mode="rb"
        )

        data = gz.read()

        gz.close()

    except Exception as e:

        print("")
        print("ERROR: gzip decompression failed.")
        print(str(e))
        print("")

        sys.exit(1)

    print(
        "Original size: %d bytes" %
        len(data)
    )

    # --------------------------------------------------------
    # Output file
    # --------------------------------------------------------

    filename = os.path.basename(
        filename
    )

    output = filename

    if os.path.exists(output):

        output = (
            "recovered_" +
            filename
        )

        counter = 1

        while os.path.exists(output):

            output = (
                "recovered_%d_%s" %
                (
                    counter,
                    filename
                )
            )

            counter += 1

    print("")
    print("Writing:")
    print("  %s" % output)

    f = open(
        output,
        "wb"
    )

    try:

        f.write(data)

    finally:

        f.close()

    # --------------------------------------------------------
    # SHA256
    # --------------------------------------------------------

    print("")
    print("Calculating SHA256...")

    actual_sha256 = sha256_file(
        output
    )

    print("")
    print("=" * 70)
    print("VERIFY")
    print("=" * 70)
    print("")

    print(
        "Expected SHA256:"
    )

    print(
        expected_sha256
    )

    print("")

    print(
        "Actual SHA256:"
    )

    print(
        actual_sha256
    )

    print("")

    if actual_sha256 != expected_sha256:

        print(
            "SHA256: FAILED"
        )

        print("")
        print(
            "The recovered file is corrupted."
        )

        try:

            os.remove(
                output
            )

        except Exception:

            pass

        sys.exit(2)

    print(
        "SHA256: OK"
    )

    print("")
    print("=" * 70)
    print("IMPORT SUCCESS")
    print("=" * 70)
    print("")

    print(
        "Output file : %s" %
        os.path.abspath(output)
    )

    print(
        "File size   : %d bytes" %
        os.path.getsize(output)
    )

    print("")


def main():

    if len(sys.argv) != 3:

        usage()
        sys.exit(1)

    mode = sys.argv[1].lower()
    source = sys.argv[2]

    # --------------------------------------------------------
    # Text mode
    # --------------------------------------------------------

    if mode == "text":

        if not os.path.isfile(source):

            print("")
            print(
                "ERROR: file not found:"
            )
            print(source)
            print("")

            sys.exit(1)

        payloads = load_text_file(
            source
        )

    # --------------------------------------------------------
    # Image mode
    # --------------------------------------------------------

    elif mode == "image":

        if not os.path.isdir(source):

            print("")
            print(
                "ERROR: directory not found:"
            )
            print(source)
            print("")

            sys.exit(1)

        payloads = load_image_directory(
            source
        )

    else:

        usage()
        sys.exit(1)

    # --------------------------------------------------------
    # Check payload
    # --------------------------------------------------------

    if not payloads:

        print("")
        print(
            "ERROR: no valid QR data found."
        )
        print("")

        sys.exit(1)

    # --------------------------------------------------------
    # Collect
    # --------------------------------------------------------

    (
        chunks,
        transfer_id,
        total,
        expected_sha256,
        filename
    ) = collect_chunks(
        payloads
    )

    # --------------------------------------------------------
    # Check missing
    # --------------------------------------------------------

    if not check_missing(
        chunks,
        total
    ):

        sys.exit(3)

    # --------------------------------------------------------
    # Restore
    # --------------------------------------------------------

    restore_file(
        chunks,
        total,
        expected_sha256,
        filename
    )


if __name__ == "__main__":

    main()
