# -*- coding: utf-8 -*-
"""
common.py —— 医学影像数据检查工具集的公共模块。

提供：文件发现、扩展名/stem 处理、SimpleITK 读取、统一命令行参数、
      报告打印与保存（txt + json）。

所有检查脚本与本文件放在同一目录，通过 `from common import ...` 复用。
"""

import argparse
import json
import os

import numpy as np
import SimpleITK as sitk

# SimpleITK 可读的常见医学影像扩展名（复合扩展名放前面，去扩展名时优先匹配）
KNOWN_EXTENSIONS = (".nii.gz", ".nii", ".mha", ".mhd", ".nrrd")


def strip_ext(filename, ext=None):
    """去掉文件扩展名，得到唯一的 stem 标识。

    ext 指定时按该扩展名去除；否则按 KNOWN_EXTENSIONS 匹配去除。
    例：strip_ext('a.mha') -> 'a'；strip_ext('a.nii.gz') -> 'a'。
    """
    if ext is not None:
        if filename.lower().endswith(ext.lower()):
            return filename[: -len(ext)]
        return filename
    low = filename.lower()
    for e in KNOWN_EXTENSIONS:
        if low.endswith(e):
            return filename[: -len(e)]
    return os.path.splitext(filename)[0]


def find_files(directory, ext=None):
    """列出 directory（非递归）下匹配扩展名的文件，返回 {stem: filename}。

    ext 为 None 时不过滤扩展名。若去扩展名后出现重复 stem，抛异常（命名不规范）。
    """
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"目录不存在: {directory}")
    result = {}
    for fn in sorted(os.listdir(directory)):
        full = os.path.join(directory, fn)
        if not os.path.isfile(full):
            continue
        if ext is not None and not fn.lower().endswith(ext.lower()):
            continue
        s = strip_ext(fn, ext)
        if s in result:
            raise ValueError(f"去扩展名后重名: '{result[s]}' 与 '{fn}' 的 stem 都是 '{s}'")
        result[s] = fn
    return result


def read_image(path):
    """用 SimpleITK 读取图像，返回 (SimpleITK.Image, None) 或 (None, 错误信息)。"""
    try:
        return sitk.ReadImage(path), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def direction_to_axcode(direction):
    """把 SimpleITK 的 3x3 方向余弦矩阵(direction)转成解剖学轴代码。

    返回形如 'RAI' / 'LPI' 的 3 字母代码：
      第 1 字母 = 体素 x 轴在世界坐标的方向（R/L 左右）
      第 2 字母 = 体素 y 轴（A/P 前后）
      第 3 字母 = 体素 z 轴（S/I 上下）
    """
    d = np.asarray(direction, dtype=float).reshape(3, 3)
    axis_labels = [("R", "L"), ("A", "P"), ("S", "I")]  # 世界 x/y/z 轴的正/负
    code = []
    for voxel_axis in range(3):            # 体素 x, y, z
        vec = d[voxel_axis]                 # 该体素轴在世界坐标中的方向余弦
        world_axis = int(np.argmax(np.abs(vec)))
        positive = vec[world_axis] >= 0.0
        code.append(axis_labels[world_axis][0 if positive else 1])
    return "".join(code)


def add_common_args(parser, image_ext_default=".mha", label_ext_default=".nii.gz"):
    """给 argparse.ArgumentParser 添加本工具集统一的命令行参数。"""
    parser.add_argument("--image_dir", required=True, help="图像所在目录（必填）")
    parser.add_argument("--label_dir", required=True, help="标签所在目录（必填）")
    parser.add_argument("--image_ext", default=image_ext_default,
                        help=f"图像文件扩展名，默认 {image_ext_default}")
    parser.add_argument("--label_ext", default=label_ext_default,
                        help=f"标签文件扩展名，默认 {label_ext_default}")
    parser.add_argument("--limit", type=int, default=None,
                        help="只检查前 N 对（用于快速试跑/调试，默认全部）")
    parser.add_argument("--report", default=None,
                        help="报告文件前缀（不含扩展名），默认保存到 reports/ 目录")
    parser.add_argument("--no_save", action="store_true",
                        help="只打印到终端，不保存报告文件")
    return parser


class Report:
    """检查报告：分节收集文本行，打印到终端，并可保存 txt + json。"""

    def __init__(self, title, report_prefix=None, no_save=False):
        self.title = title
        self.report_prefix = report_prefix
        self.no_save = no_save
        self.sections = []          # [(heading, [line, ...]), ...]
        self.summary = {}           # 结构化结果，用于 json

    def add_section(self, heading, lines):
        self.sections.append((heading, list(lines)))

    def render_text(self):
        lines = ["=" * 72, self.title, "=" * 72, ""]
        for heading, body in self.sections:
            lines.append(f"[{heading}]")
            lines.extend(f"  {ln}" for ln in body)
            lines.append("")
        return "\n".join(lines)

    def _default_prefix(self):
        safe = "".join(c if c.isalnum() else "_" for c in self.title)
        return os.path.join("reports", safe)

    def emit(self):
        """打印到终端；若未关闭保存，则同时写出 .txt 与 .json 报告。"""
        text = self.render_text()
        print(text)
        if self.no_save:
            return None
        prefix = self.report_prefix or self._default_prefix()
        os.makedirs(os.path.dirname(prefix) or ".", exist_ok=True)
        txt_path = prefix + ".txt"
        json_path = prefix + ".json"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.summary, f, ensure_ascii=False, indent=2)
        print(f"\n[报告已保存] {txt_path}")
        print(f"[报告已保存] {json_path}")
        return prefix
