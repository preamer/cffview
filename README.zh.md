# cffview

> CFF 是 Ansys **C**ommon **F**luids **F**ormat 的缩写。

一个用于查看 Ansys Fluent `.cas.h5` / `.msh.h5` / `.dat.h5` 文件的命令行工具，**无需打开 Fluent**。

- 直接从 HDF5 文件中读取求解器设置、材料、边界条件、离散格式等信息。
- 使用 [PyVista](https://pyvista.org) 可视化网格或计算结果。

## 安装

### PyPI

```bash
pip install cffview
```

### 源码

```bash
git clone https://github.com/preamer/cffview.git
cd cffview
pip install .
```

## 用法

> [!IMPORTANT]
> 只在 Ansys Fluent 25R2 下进行过测试！

```
cffview <文件> [选项]
```

### 选项

| 选项 | 说明 |
|---|---|
| `--version` | 打印文件对应的 Fluent 版本号 |
| `--extract` | 将原始 Scheme 设置导出到 `general.scm` 和 `boundary.scm` |
| `--mesh`, `--showmesh` | 使用 PyVista 交互式显示网格 |
| `--data`, `--plotdata` | 使用 PyVista 以交互方式绘制数据（可能不起作用，依赖 `vtkFLUENTCFFReader`） |
| `--solver` | 求解器类型、时间类型、维度、精度、湍流模型、能量方程、辐射模型、重力 |
| `--mat`, `--materials` | 材料属性 |
| `--bd`, `--boundary` | 边界条件设置 |
| `--interfaces` | 网格交界面设置 |
| `--ne`, `--named-expressions` | 命名表达式 |
| `--disc` | 离散格式和松弛因子 |
| `--rd`, `--report-definitions` | 报告定义 |
| `--plotsets` | 图表集配置 |
| `--monitorsets` | 监控集配置 |
| `--residuals` | 残差设置 |
| `--iter` | 迭代步数 / 时间步设置 |
| `--surfaces` | 面、线、等值面等设置 |
| `--contours` | 后处理云图配置 |
| `--vectors` | 后处理矢量图配置 |
| `--xy-plot` | 后处理xy图配置 |
| `--save` | 将输出保存为 `<文件名>.json` (`文件名`可选，默认与输入文件相同) |
| `--plot` | 绘制数据文件, 支持 `--out` 和 `--xy`, 如果没有指定则从文件后缀推断 |
| `--out` | 绘制 `.out` 文件, 和 `--plot` 配合使用 |
| `--xy` | 绘制 `.xy` 文件, 和 `--plot` 配合使用 |
| `--dat` | 绘制 `.dat.h5` 文件中的残差数据, 和 `--plot` 配合使用 |

多个选项可以自由组合。算例设置类选项（`--solver`、`--mat` 等）仅适用于 `.cas.h5` 文件。

### 示例

```bash
# 查看所有设置并保存为 JSON
cffview case.cas.h5 --save

# 查看求解器设置和边界条件
cffview case.cas.h5 --solver --bd

# 可视化网格
cffview case.cas.h5 --mesh
cffview mesh.msh.h5

# 可视化计算结果
cffview case.cas.h5 --data

# 查看文件对应的 Fluent 版本
cffview case.cas.h5 --version

# 导出原始 Scheme 字符串以便手动查看
cffview case.cas.h5 --extract
```

### 演示

https://github.com/user-attachments/assets/7f97b559-87fa-4822-be9f-4e82b8c5cab6

## 开源协议

[BSD-3-Clause](LICENSE)
