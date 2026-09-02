# -*- coding: utf-8 -*-
"""
check_correspondence.py —— 图像与标签一一对应检查。

检查图像目录与标签目录的文件：
  1) 数量是否相等
  2) 去扩展名后的 stem 是否完全一致（每个图像都有标签、每个标签都有图像）
  3) 是否存在孤儿文件（只有图像 / 只有标签）

用法：
  python check_correspondence.py --image_dir <图像目录> --label_dir <标签目录>
  python check_correspondence.py --image_dir ./image_T2 --label_dir ./label \
      --image_ext .mha --label_ext .nii.gz
"""

import argparse
import sys

from common import add_common_args, find_files, Report

MAX_SHOW = 50  # 孤儿清单最多显示条数


def main(argv=None):
    parser = argparse.ArgumentParser(description="图像与标签一一对应检查")
    add_common_args(parser)
    args = parser.parse_args(argv)

    rep = Report("图像-标签一一对应检查报告", args.report, args.no_save)

    try:
        imgs = find_files(args.image_dir, args.image_ext)
        labs = find_files(args.label_dir, args.label_ext)
    except Exception as exc:  # noqa: BLE001
        rep.add_section("错误", [str(exc)])
        rep.summary = {"ok": False, "error": str(exc)}
        rep.emit()
        return 1

    img_stems = set(imgs)
    lab_stems = set(labs)
    common = img_stems & lab_stems
    img_only = sorted(img_stems - lab_stems)
    lab_only = sorted(lab_stems - img_stems)

    rep.add_section("文件数量", [
        f"图像目录 ({args.image_dir}) : {len(imgs)} 个 ({args.image_ext})",
        f"标签目录 ({args.label_dir}) : {len(labs)} 个 ({args.label_ext})",
        f"共同 stem : {len(common)}",
    ])

    if img_only:
        lines = img_only[:MAX_SHOW]
        if len(img_only) > MAX_SHOW:
            lines.append(f"... 共 {len(img_only)} 个，仅显示前 {MAX_SHOW}")
        rep.add_section("孤儿：只有图像、无标签", lines)
    if lab_only:
        lines = lab_only[:MAX_SHOW]
        if len(lab_only) > MAX_SHOW:
            lines.append(f"... 共 {len(lab_only)} 个，仅显示前 {MAX_SHOW}")
        rep.add_section("孤儿：只有标签、无图像", lines)

    ok = bool(common) and not img_only and not lab_only
    conclusion = "通过：图像与标签一一对应" if ok else "不通过：存在孤儿文件或数量不等"
    rep.add_section("结论", [conclusion])

    rep.summary = {
        "ok": ok,
        "n_images": len(imgs),
        "n_labels": len(labs),
        "n_common": len(common),
        "image_only": img_only,
        "label_only": lab_only,
    }
    rep.emit()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
