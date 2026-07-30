# Codex 绫濑桃宠物与 PetEase

这是一个经过完整视觉质检的非官方 **《胆大党》绫濑桃** Codex v2 宠物，也是一套真正可运行的宠物动画无障碍工具：
**PetEase**。

它不是只换皮的界面项目。仓库交付：

- 1536×2288、8×11 的完整 Codex v2 精灵图；
- 9 个标准动画状态和 16 个视线方向；
- 宠物结构、透明像素、切边、闪变、亮度跳变、位移和比例变化审计；
- JSON、HTML、SARIF 三种报告；
- 可复现的 reduced-motion 宠物编译；
- 带暂存、校验、备份和失败回滚的安装；
- 确定性 `.codex-pet` 归档；
- 已提交的[视觉 QA 证据](artwork/qa/)：接触表、方向语义、连续性指标与三名独立评审者的盲测结果；
- 单元测试、跨平台 CI、示例策略、验收和修复手册。

> 本项目为非官方同人项目。绫濑桃和《胆大党》的相关权利归各权利人所有。MIT 仅适用于软件和原创文档，图片资产条款见
> [ASSET_LICENSE.md](ASSET_LICENSE.md)。

![Codex v2 宠物格式中的绫濑桃挥手动画](artwork/qa/previews/waving.gif)

[English](README.md) · [完整验收](docs/ACCEPTANCE.md) ·
[故障修复](docs/REPAIR.md) · [架构](docs/ARCHITECTURE.md)

## 安装宠物

从同一个 GitHub Release 下载 `momo-ayase-codex-pet-v0.1.0.zip` 和
`petease-0.1.0-py3-none-any.whl`，解压宠物包后执行：

```powershell
py -m pip install .\petease-0.1.0-py3-none-any.whl
petease install .\pet --dry-run
petease install .\pet
```

重启 Codex，在 **Settings → Pets** 选择 **Momo Ayase**。默认安装到
`~/.codex/pets`；如设置了 `CODEX_HOME`，则使用该目录。已有同 ID
宠物会先保存为带 UTC 时间戳的备份。

建议先在隔离目录验收：

```powershell
petease install .\pet --codex-home .\.acceptance-codex --dry-run
petease install .\pet --codex-home .\.acceptance-codex
```

## 审计任意 Codex v2 宠物

PetEase 与角色无关。目标目录只需包含 `pet.json` 和其指向的精灵图：

```powershell
petease audit .\pet `
  --json-out .\build\audit.json `
  --html-out .\build\audit.html `
  --sarif-out .\build\audit.sarif `
  --strict
```

退出码：

- `0`：结构通过；`--strict` 下也没有动作告警；
- `1`：清单、路径、尺寸或精灵图结构错误；
- `2`：结构通过，但严格动作策略发现告警。

自定义动作阈值：

```powershell
petease audit .\pet --policy .\examples\policy.json --strict
```

## 生成 reduced-motion 版本

```powershell
petease compile-reduced .\pet .\build\momo-reduced `
  --json-out .\build\reduced-audit.json
petease audit .\build\momo-reduced --strict
```

PetEase 会为每个动画状态选择确定性的代表帧并填充该状态的已用格子，
完整保留 16 个视线方向，同时记录输入/输出 SHA-256 与帧选择。
即使使用 `--force`，也不会覆盖不属于 PetEase 的任意非空目录。

## 打包与校验

```powershell
petease package .\pet .\dist\momo-ayase.codex-pet
petease verify-archive .\dist\momo-ayase.codex-pet
```

归档条目有固定顺序、固定时间戳和权限；路径穿越、软链接、重复条目会被拒绝。

## 本地开发与验收

支持 Python 3.10+。复现 CI 的锁定依赖环境：

```bash
uv sync --locked --extra dev
uv run python scripts/release_gate.py --json build/release-gate.json
```

等价的标准 `venv` / pip 流程：

```powershell
py -m venv .venv
py -m pip install -e ".[dev]"
py -m unittest discover -v
py -m coverage run -m unittest discover
py -m coverage report
py -m ruff check .
py scripts/release_gate.py --json build/release-gate.json
```

发布级验收见 [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md)，失败后的逐项修复见
[docs/REPAIR.md](docs/REPAIR.md)。

## 选题依据

绫濑桃不是虚构出来的角色，她出现在
[《胆大党》官方网站角色页](https://anime-dandadan.com/en/character/)。
立项时对主要 Codex 宠物合集、仓库名与代码进行了去重检索：未发现绫濑桃实现，
而芙莉莲、猫猫、波奇、阿尼亚、初音未来、重音 Teto 等热门角色已经有项目。
完整检索记录和局限见 [docs/RESEARCH.md](docs/RESEARCH.md)。

热门角色、真实工具价值、完整文档和发布质量能够提高传播概率，但任何人都不能诚实保证 Star 或浏览量。

## 隐私与权利

PetEase 默认完全离线，不上传遥测，不读取 Codex 对话，也不需要网络权限。
官方角色参考图只用于本地身份核对，不进入 Git 历史、发行包或网站。
详情见 [SECURITY.md](SECURITY.md)、[NOTICE.md](NOTICE.md) 和
[ASSET_LICENSE.md](ASSET_LICENSE.md)。
