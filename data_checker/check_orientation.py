# -*- coding: utf-8 -*-
"""
check_orientation.py —— 图像与标签的方向 / 原点一致性检查。

医学影像里，图像与标签若方向(direction 余弦矩阵)或原点(origin)不一致，
配准时会错位，直接影响分割训练。本脚本检查：
  1) 每一对图像与标签的方向矩阵是否一致
  2) 每一对图像与标签的原点是否一致
  3) 全样本的方向种类（解剖学轴代码，如 RAI/LPI）分布 —— 判断不同样本间
     方向是否统一，若不统一建议训练前统一到同一方向。

用法：
  python check_orientation.py --image_dir <图像目录> --label_dir <标签目录>
"""

import argparse
import sys
from collections import Counter

import numpy as np

from common import add_common_args, direction_to_axcode, find_files, read_image, Report

MAX_SHOW = 50


def main(argv=None):
    parser = argparse.ArgumentParser(description="图像与标签方向/原点一致性检查")
    add_common_args(parser)
    args = parser.parse_args(argv)

    rep = Report("方向一致性检查报告", args.report, args.no_save)

    try:
        imgs = find_files(args.image_dir, args.image_ext)
        labs = find_files(args.label_dir, args.label_ext)
    except Exception as exc:  # noqa: BLE001
        rep.add_section("错误", [str(exc)])
        rep.summary = {"ok": False, "error": str(exc)}
        rep.emit()
        return 1

    common = sorted(set(imgs) & set(labs))
    if args.limit is not None:
        common = common[: args.limit]

    dir_mismatch = []    # (stem, img_dir, lab_dir)
    origin_mismatch = []  # (stem, img_origin, lab_origin)
    axcode_dist = Counter()

    for i, s in enumerate(common, 1):
        iimg, ierr = read_image(f"{args.image_dir}/{imgs[s]}")
        limg, lerr = read_image(f"{args.label_dir}/{labs[s]}")
        if ierr or lerr:
            dir_mismatch.append((s, "读取失败", "读取失败"))
            continue

        idir = iimg.GetDirection()
        ldir = limg.GetDirection()
        iori = iimg.GetOrigin()
        lori = limg.GetOrigin()

        axcode_dist[direction_to_axcode(idir)] += 1

        if not _same(idir, ldir, atol=1e-3):
            dir_mismatch.append((s, idir, ldir))
        if not _same(iori, lori, atol=1e-2):
            origin_mismatch.append((s, iori, lori))

        if i % 200 == 0:
            print(f"  已检查 {i}/{len(common)} ...", flush=True)

    rep.add_section("方向不一致（图像 vs 标签）",
                    [f"{len(dir_mismatch)} 对"] +
                    [f"  {s}" for s, _, _ in dir_mismatch[:MAX_SHOW]])
    rep.add_section("原点不一致（图像 vs 标签）",
                    [f"{len(origin_mismatch)} 对"] +
                    [f"  {s}: {_fmt(ori)} != {_fmt(lo)}"
                     for s, ori, lo in origin_mismatch[:MAX_SHOW]])

    rep.add_section("全样本方向种类分布（解剖学轴代码）", [
        f"  {code}: {c} 个" for code, c in sorted(axcode_dist.items(), key=lambda kv: -kv[1])
    ])
    rep.add_section("提示", [
        f"样本共有 {len(axcode_dist)} 种方向。",
        "常见标准方向为 RAI / LPS。若方向种类 >1，建议训练前用重定向统一到同一方向。"
    ])

    ok = (not dir_mismatch) and (not origin_mismatch)
    rep.add_section("结论", ["通过：所有配对的图像与标签方向、原点一致" if ok
                           else "不通过：存在方向或原点不一致的配对"])

    rep.summary = {
        "ok": ok,
        "n_pairs": len(common),
        "direction_mismatch": [s for s, _, _ in dir_mismatch],
        "origin_mismatch": [{"stem": s, "image": list(a), "label": list(b)}
                            for s, a, b in origin_mismatch],
        "axcode_distribution": dict(axcode_dist),
    }
    rep.emit()
    return 0 if ok else 1


def _same(a, b, atol=1e-6):
    return all(abs(x - y) <= atol for x, y in zip(a, b))


def _fmt(t):
    return "(" + ", ".join(str(round(v, 4)) for v in t) + ")"


if __name__ == "__main__":
    sys.exit(main())
