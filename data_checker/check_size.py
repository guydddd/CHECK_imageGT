# -*- coding: utf-8 -*-
"""
check_size.py —— 图像与标签的空间尺寸 / 体素间距一致性检查。

对每一对图像与标签检查：
  1) 尺寸 GetSize() 是否一致（深度学习训练的硬性前提）
  2) 体素间距 GetSpacing() 是否一致
  3) 全样本的尺寸分布与间距分布（判断训练前是否需统一分辨率 / 裁剪）

用法：
  python check_size.py --image_dir <图像目录> --label_dir <标签目录>
"""

import argparse
import sys
from collections import Counter

import SimpleITK as sitk

from common import add_common_args, find_files, read_image, Report

MAX_SHOW = 50


def _fmt_tuple(t):
    return "(" + ", ".join(str(round(v, 4)) for v in t) + ")"


def main(argv=None):
    parser = argparse.ArgumentParser(description="图像与标签尺寸/间距一致性检查")
    add_common_args(parser)
    args = parser.parse_args(argv)

    rep = Report("尺寸一致性检查报告", args.report, args.no_save)

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

    size_mismatch = []   # (stem, img_size, lab_size)
    spacing_mismatch = []  # (stem, img_spacing, lab_spacing)
    size_dist = Counter()
    spacing_dist = Counter()

    for i, s in enumerate(common, 1):
        iimg, ierr = read_image(f"{args.image_dir}/{imgs[s]}")
        limg, lerr = read_image(f"{args.label_dir}/{labs[s]}")
        if ierr or lerr:
            size_mismatch.append((s, "读取失败", "读取失败"))
            continue

        isz = iimg.GetSize()
        lsz = limg.GetSize()
        isp = iimg.GetSpacing()
        lsp = limg.GetSpacing()

        size_dist[isz] += 1
        # spacing 存在浮点噪声（如 3.29999998 vs 3.3），round 后再聚合统计
        spacing_dist[tuple(round(v, 3) for v in isp)] += 1

        if isz != lsz:
            size_mismatch.append((s, isz, lsz))
        if not _same(isp, lsp, atol=1e-3):
            spacing_mismatch.append((s, isp, lsp))

        if i % 200 == 0:
            print(f"  已检查 {i}/{len(common)} ...", flush=True)

    rep.add_section("尺寸不一致（图像 vs 标签）",
                    [f"{len(size_mismatch)} 对"] +
                    [f"  {s}: {a} != {b}" for s, a, b in size_mismatch[:MAX_SHOW]])
    rep.add_section("间距不一致（图像 vs 标签）",
                    [f"{len(spacing_mismatch)} 对"] +
                    [f"  {s}: {a} != {b}" for s, a, b in spacing_mismatch[:MAX_SHOW]])

    rep.add_section("图像尺寸分布 (x,y,z)", [
        f"  {sz}: {c} 个" for sz, c in sorted(size_dist.items(), key=lambda kv: -kv[1])
    ])
    rep.add_section("体素间距分布 (x,y,z) mm", [
        f"  {sp}: {c} 个" for sp, c in sorted(spacing_dist.items(), key=lambda kv: -kv[1])
    ])

    n_distinct_size = len(size_dist)
    n_distinct_spacing = len(spacing_dist)
    rep.add_section("提示", [
        f"图像存在 {n_distinct_size} 种不同尺寸、{n_distinct_spacing} 种不同间距。",
        "若训练需统一输入，请在预处理阶段做重采样(resample)到相同 spacing 与尺寸。"
    ])

    ok = (not size_mismatch) and (not spacing_mismatch)
    rep.add_section("结论", ["通过：所有配对的尺寸与间距一致" if ok
                           else "不通过：存在尺寸或间距不一致的配对"])

    rep.summary = {
        "ok": ok,
        "n_pairs": len(common),
        "size_mismatch": [{"stem": s, "image": list(a), "label": list(b)}
                          for s, a, b in size_mismatch],
        "spacing_mismatch": [{"stem": s, "image": list(a), "label": list(b)}
                             for s, a, b in spacing_mismatch],
        "size_distribution": {str(k): v for k, v in size_dist.items()},
        "spacing_distribution": {str(k): v for k, v in spacing_dist.items()},
    }
    rep.emit()
    return 0 if ok else 1


def _same(a, b, atol=1e-3):
    return all(abs(x - y) <= atol for x, y in zip(a, b))


if __name__ == "__main__":
    sys.exit(main())
