# -*- coding: utf-8 -*-
"""
check_integrity.py —— 数据完整性 / 可读性检查。

对图像与标签的每一对，用 SimpleITK 逐文件读取，检查：
  1) 能否正常读取（文件损坏 / 格式错误会在这里暴露）
  2) 是否为空文件（全 0 体素）
  3) 图像数值范围（dtype、min/max）
  4) 标签取值分布、是否整数、前景占比、空掩码（全 0）

用法：
  python check_integrity.py --image_dir <图像目录> --label_dir <标签目录>
  python check_integrity.py --image_dir ./image_T2 --label_dir ./label --limit 20
"""

import argparse
import sys
from collections import Counter

import numpy as np
import SimpleITK as sitk

from common import add_common_args, find_files, read_image, Report

MAX_SHOW = 50


def main(argv=None):
    parser = argparse.ArgumentParser(description="数据完整性 / 可读性检查")
    add_common_args(parser)
    args = parser.parse_args(argv)

    rep = Report("数据完整性检查报告", args.report, args.no_save)

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

    read_fail = []          # (stem, 图像/标签, 错误)
    zero_images = []        # 全 0 图像
    empty_labels = []       # 全 0 标签（空掩码）
    nonint_labels = []      # 标签含非整数值
    label_value_counter = Counter()   # 标签取值 -> 体素数
    total_fg_voxels = 0     # 前景体素总数
    total_voxels = 0        # 标签体素总数
    img_minmax = []         # 图像 (min, max)
    img_dtypes = Counter()  # 图像 dtype -> 数量

    for i, s in enumerate(common, 1):
        iimg, ierr = read_image(f"{args.image_dir}/{imgs[s]}")
        limg, lerr = read_image(f"{args.label_dir}/{labs[s]}")

        if ierr:
            read_fail.append((s, "图像", ierr))
        if lerr:
            read_fail.append((s, "标签", lerr))
        if ierr or lerr:
            continue

        iarr = sitk.GetArrayFromImage(iimg)
        larr = sitk.GetArrayFromImage(limg)

        img_dtypes[str(iarr.dtype)] += 1
        img_minmax.append((int(iarr.min()), int(iarr.max())))
        if int(iarr.max()) == 0:
            zero_images.append(s)

        lab_unique, lab_counts = np.unique(larr, return_counts=True)
        label_value_counter.update(dict(zip(lab_unique.tolist(), lab_counts.tolist())))
        total_voxels += int(larr.size)
        total_fg_voxels += int((larr > 0).sum())
        if int(larr.max()) == 0:
            empty_labels.append(s)
        if not np.allclose(lab_unique, np.round(lab_unique)):
            nonint_labels.append((s, lab_unique[:10].tolist()))

        if i % 200 == 0:
            print(f"  已检查 {i}/{len(common)} ...", flush=True)

    rep.add_section("读取失败", [f"{len(read_fail)} 个文件"] +
                    [f"  {s} [{kind}]: {err}" for s, kind, err in read_fail[:MAX_SHOW]])
    rep.add_section("空图像（全 0）", [f"{len(zero_images)} 个"] + zero_images[:MAX_SHOW])
    rep.add_section("空标签（全 0 掩码）", [f"{len(empty_labels)} 个"] + empty_labels[:MAX_SHOW])
    rep.add_section("非整数标签", [f"{len(nonint_labels)} 个"] +
                    [f"  {s}: {vals}" for s, vals in nonint_labels[:MAX_SHOW]])

    # 标签取值分布
    rep.add_section("标签取值分布（体素数）",
                    [f"  值 {int(v):>6}: {c:>12}" for v, c in sorted(label_value_counter.items())])
    fg_ratio = (total_fg_voxels / total_voxels) if total_voxels else 0.0
    rep.add_section("前景占比", [
        f"前景体素 / 总体素 = {total_fg_voxels} / {total_voxels} = {fg_ratio:.4%}"
    ])

    # 图像数值范围
    if img_minmax:
        mins = [m for m, _ in img_minmax]
        maxs = [m for _, m in img_minmax]
        rep.add_section("图像数值范围", [
            f"min 范围 : {min(mins)} ~ {max(mins)}",
            f"max 范围 : {min(maxs)} ~ {max(maxs)}",
            f"最大灰度值 : {max(maxs)}",
        ])
    rep.add_section("图像 dtype 分布", [f"  {d}: {c}" for d, c in sorted(img_dtypes.items())])

    ok = (not read_fail) and (not zero_images) and (not empty_labels) and (not nonint_labels)
    rep.add_section("结论", ["通过：所有文件可正常读取，无损坏/空文件/非整数标签"
                           if ok else "不通过：存在读取失败、空文件或非整数标签"])

    rep.summary = {
        "ok": ok,
        "n_pairs": len(common),
        "read_fail": read_fail,
        "zero_images": zero_images,
        "empty_labels": empty_labels,
        "nonint_labels": nonint_labels,
        "label_value_counts": {int(k): int(v) for k, v in label_value_counter.items()},
        "foreground_ratio": fg_ratio,
        "image_dtypes": dict(img_dtypes),
    }
    rep.emit()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
