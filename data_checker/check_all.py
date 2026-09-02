# -*- coding: utf-8 -*-
"""
check_all.py —— 一键运行全部四项检查。

依次运行：
  1) check_correspondence.py  一一对应
  2) check_integrity.py       完整性 / 可读性
  3) check_size.py            尺寸 / 间距一致性
  4) check_orientation.py     方向 / 原点一致性

接受的命令行参数与单个脚本一致（--image_dir、--label_dir、--image_ext、
--label_ext、--limit、--report、--no_save），并透传给每个子脚本。

用法：
  python check_all.py --image_dir ./image_T2 --label_dir ./label
  python check_all.py --image_dir ./image_T2 --label_dir ./label --limit 20 --no_save
"""

import argparse
import os
import subprocess
import sys

from common import add_common_args

SCRIPTS = [
    "check_correspondence.py",
    "check_integrity.py",
    "check_size.py",
    "check_orientation.py",
]


def main(argv=None):
    parser = argparse.ArgumentParser(description="一键运行全部数据检查")
    add_common_args(parser)
    args = parser.parse_args(argv)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    returncode = 0

    for name in SCRIPTS:
        script = os.path.join(base_dir, name)
        cmd = [
            sys.executable, script,
            "--image_dir", args.image_dir,
            "--label_dir", args.label_dir,
            "--image_ext", args.image_ext,
            "--label_ext", args.label_ext,
        ]
        if args.limit is not None:
            cmd += ["--limit", str(args.limit)]
        if args.report is not None:
            cmd += ["--report", f"{args.report}_{os.path.splitext(name)[0]}"]
        if args.no_save:
            cmd.append("--no_save")

        print(f"\n{'#' * 72}\n# 运行: {name}\n{'#' * 72}", flush=True)
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            returncode = proc.returncode

    print("\n" + "=" * 72)
    print("全部检查执行完毕。若任一项返回非 0，说明该项存在需要关注的问题。")
    print("=" * 72)
    return returncode


if __name__ == "__main__":
    sys.exit(main())
