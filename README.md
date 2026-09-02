# data_checker — 医学影像数据集检查工具

做深度学习（尤其医学图像分割）之前，先对数据集做「体检」：检查图像与标签是否**一一对应**、文件是否**完整可读**、**尺寸/间距**是否一致、**方向(orientation)**是否一致。本工具把这几类检查拆成独立的命令行脚本，需要哪项就调哪项。

## 特性

- **四个独立脚本**，各查一类问题，可单独调用，也可一键跑全部。
- **通用读取**：基于 SimpleITK，支持 `.mha` / `.mhd` / `.nii` / `.nii.gz` / `.nrrd` 等，扩展名可配置。
- **输出双格式**：终端打印摘要，同时保存 `.txt` 与 `.json` 报告，便于留档与 CI。
- **医学影像专项**：除尺寸外，还检查 `spacing`、方向余弦矩阵(direction)、原点(origin)与解剖学轴代码(RAI/LPS 等)。

## 目录结构

```
data_checker/
├── common.py                    # 公共模块（文件发现、读取、报告）
├── check_correspondence.py      # ① 图像与标签一一对应
├── check_integrity.py           # ② 完整性 / 可读性
├── check_size.py                # ③ 尺寸 / 间距一致性
├── check_orientation.py         # ④ 方向 / 原点一致性
├── check_all.py                 # 一键运行以上四项
├── requirements.txt
└── README.md
```

## 安装

```bash
pip install -r requirements.txt
```

需要 Python ≥ 3.8。核心依赖：`SimpleITK`、`numpy`。

## 数据目录约定

图像与标签分别放在两个目录，**文件名（去扩展名后）一一对应**：

```
dataset/
├── image_T2/            # 图像目录
│   ├── 10000_1000000.mha
│   └── 10001_1000001.mha
└── label/               # 标签目录（stem 与图像一致）
    ├── 10000_1000000.nii.gz
    └── 10001_1000001.nii.gz
```

`image_T2/10000_1000000.mha` 与 `label/10000_1000000.nii.gz` 视为同一对。

## 用法

### 通用参数（四个脚本通用）

| 参数 | 说明 | 默认 |
|---|---|---|
| `--image_dir` | 图像目录（必填） | — |
| `--label_dir` | 标签目录（必填） | — |
| `--image_ext` | 图像扩展名 | `.mha` |
| `--label_ext` | 标签扩展名 | `.nii.gz` |
| `--limit N` | 只检查前 N 对（快速试跑） | 全部 |
| `--report PREFIX` | 报告文件前缀（不含扩展名） | `reports/<标题>` |
| `--no_save` | 只打印、不保存报告文件 | 关闭 |

### ① 一一对应

```bash
python check_correspondence.py --image_dir ./image_T2 --label_dir ./label
```

### ② 完整性 / 可读性

```bash
python check_integrity.py --image_dir ./image_T2 --label_dir ./label
```

### ③ 尺寸 / 间距一致性

```bash
python check_size.py --image_dir ./image_T2 --label_dir ./label
```

### ④ 方向 / 原点一致性

```bash
python check_orientation.py --image_dir ./image_T2 --label_dir ./label
```

### 一键运行全部

```bash
python check_all.py --image_dir ./image_T2 --label_dir ./label
```

快速试跑前 20 对、只看终端不落盘：

```bash
python check_all.py --image_dir ./image_T2 --label_dir ./label --limit 20 --no_save
```

## 每个脚本检查什么

| 脚本 | 检查项 |
|---|---|
| `check_correspondence.py` | 图像/标签数量、stem 是否完全对齐、孤儿文件（只有图像或只有标签） |
| `check_integrity.py` | 文件能否读取、空文件(全 0)、图像数值范围与 dtype、标签取值分布、前景占比、非整数标签 |
| `check_size.py` | 每对尺寸(shape)、间距(spacing)是否一致；全样本尺寸/间距分布 |
| `check_orientation.py` | 每对方向(direction)、原点(origin)是否一致；全样本解剖学轴代码分布 |

## 返回码

每个脚本退出码为 `0` 表示该项「通过」，非 `0` 表示存在问题，方便在 CI / 脚本里做 `if` 判断。

## 常见问题

- **报告里的中文乱码？** 终端输出按系统编码，Windows 下若乱码，可在运行前执行 `chcp 65001` 或用支持 UTF-8 的终端；`.txt`/`.json` 报告本身固定以 UTF-8 写入，不受影响。
- **换数据格式？** 改 `--image_ext` / `--label_ext` 即可，无需改代码。
- **方向种类多于 1 种？** 医学数据常见不同方向混存，训练前建议统一重定向到同一方向（如 RAI/LPS）。
