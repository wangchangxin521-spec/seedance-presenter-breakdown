# Seedance 口播视频拆解

根据口播参考视频，输出一条适用于 Seedance 的无声人物视频生成提示词，以及一段按原顺序提取的完整口播台词。

提示词保留相近的年龄段、明确性别及符合视频主题的人物身份，允许样貌、服装和场景布置自然变化。人物站立、全程直视镜头，只做小幅度讲解动作，嘴唇自然闭合，不说话、不张嘴、不露牙齿、不微笑、不大喘气。

## 文件结构

```text
seedance-presenter-breakdown/
├── SKILL.md
├── manifest.json
├── README.md
└── references/
    └── output-example.md
```

- [SKILL.md](SKILL.md)：触发条件、处理流程、固定提示词结构和台词提取规则。
- [manifest.json](manifest.json)：版本及 MyFlicker 平台元信息。
- [输出示例](references/output-example.md)：完整的口腔健康口播参考示例。

## 使用方法

将整个目录放入所用 Agent 支持的 Skill 目录，保留目录名 `seedance-presenter-breakdown`。执行环境需要能够读取视频与音频，或提供抽帧和转写能力；本 Skill 无需运行仓库内脚本。

上传口播参考视频后，可发送：

> 帮我拆解这个视频，按固定格式给我一条 Seedance 无声口播人物提示词，再提取完整台词，台词不要分行。

只修改提示词时，可发送：

> 保留人物和场景方向，把服装换成更休闲的风格，其余要求不变，再给我一个完整版本。

默认交付两项：一条完整生成提示词，以及一段连续的完整原话。只修改提示词时交付修订后的单个版本。

## 上传 GitHub

创建名为 `seedance-presenter-breakdown` 的仓库，将本目录里的 `SKILL.md`、`manifest.json`、`README.md` 和 `references` 上传到仓库根目录即可。
