# OpenClaw Douyin Skills Pack

这是一套面向 OpenClaw 的抖音工作流 skill 包，基于 TikHub 提供的数据能力设计，当前包含 3 个 skill：

1. `douyin-subscription-manager`
2. `douyin-video-harvester`
3. `douyin-shot-analysis-kb`

这 3 个 skill 的职责划分是刻意拆开的，不是随便分文件：

- **订阅管理** 负责维护你要长期跟踪的抖音账号列表
- **视频抓取** 负责把某个账号的全部短视频尽量完整抓下来
- **镜头分析与知识库** 负责把抓到的视频转成可复用的方法论、拍摄套路、内容结构

这样拆的好处是清晰、可替换、可扩展。后面你想把 TikHub 换成别的数据源，通常只需要替换抓取层，不用把分析层也一起砸掉。

---

## 当前状态

这套 skill **已经适合作为可加载的 skill 规范包使用**，但它不是“零配置即可直接联网抓抖音”的成品插件。

说白了，它现在包含的是：

- skill 的职责定义
- 调用时机说明
- 输入输出约定
- 工作流拆分
- 后续接真实脚本的接口位置

它**还不包含**一套已经焊死的 TikHub 执行器。也就是说：

- Skill 本身告诉模型“什么时候用哪把刀”
- 真实请求 TikHub 的逻辑，需要由你的 OpenClaw 运行环境或后续脚本来执行

别把它理解成浏览器插件那种“安装即跑”。不是那个路数。

---

## 目录结构

```text
openclaw-douyin-skills/
  README.md
  douyin-subscription-manager/
    SKILL.md
  douyin-video-harvester/
    SKILL.md
  douyin-shot-analysis-kb/
    SKILL.md
```

如果后面补真实执行脚本，建议扩展成这样：

```text
openclaw-douyin-skills/
  README.md
  douyin-subscription-manager/
    SKILL.md
    scripts/
      manage_subscription.py
  douyin-video-harvester/
    SKILL.md
    scripts/
      harvest_videos.py
  douyin-shot-analysis-kb/
    SKILL.md
    scripts/
      analyze_videos.py
```

---

## 如何安装

### 1. 解压 skill 包

```bash
unzip openclaw-douyin-skills.zip
```

### 2. 放入 OpenClaw 的 skills 目录

最终结构建议类似：

```text
your-openclaw/
  skills/
    douyin-subscription-manager/
    douyin-video-harvester/
    douyin-shot-analysis-kb/
```

如果你的 OpenClaw 不是这个目录结构，就按你项目原本的 skill 加载规则放进去。核心不是路径长什么样，核心是 **OpenClaw 能扫描到每个 skill 目录里的 `SKILL.md`**。

---

## TikHub Key 应该放在哪里

**不要把 Key 写进 `SKILL.md`。也不要把 Key 直接写死在 Python、JS、Shell 脚本里。**

正确做法是放到运行环境里，统一使用环境变量：

```bash
TIKHUB_API_TOKEN=你的_tikhub_token
```

### 推荐方式 A：当前终端临时生效

```bash
export TIKHUB_API_TOKEN="你的_tikhub_token"
```

然后再启动 OpenClaw。

### 推荐方式 B：写入 `.env`

如果你的项目支持 `.env`，就在项目根目录放一个：

```env
TIKHUB_API_TOKEN=你的_tikhub_token
```

### 推荐方式 C：部署平台 Secret

如果你是服务器、Docker、CI/CD 环境部署，直接放到对应平台的 Secret 或环境变量配置里。

---

## 哪些地方不能放 Key

这些位置都不该放：

- `SKILL.md`
- `README.md`
- `references/*.md`
- 代码仓库里提交的脚本文件
- 前端代码
- 任何会被 zip 打包、git 提交、团队共享的明文文件

你一旦把 key 写进这些地方，本质上就是在主动泄露。

---

## OpenClaw 里怎么用这 3 个 skill

### 1. `douyin-subscription-manager`

用途：

- 增加订阅账号
- 取消订阅账号
- 查看当前维护的账号列表
- 校验某个账号是否已经进入跟踪池

它的目标不是“做抖音客户端”，而是帮你维护一个**稳定的创作者采集名单**。

适用场景：

- “把这个抖音号加入监控名单”
- “取消跟踪这个账号”
- “列出我当前订阅的账号”

### 2. `douyin-video-harvester`

用途：

- 抓取某个抖音账号的全部短视频
- 处理分页
- 去重
- 输出结构化数据
- 为后续分析提供原始素材

适用场景：

- “抓取这个抖音号的全部作品”
- “补抓最近新增的视频”
- “导出为后续分析可用的数据集”

### 3. `douyin-shot-analysis-kb`

用途：

- 分析拍摄手法
- 归纳镜头语言、剪辑节奏、开头钩子、文案结构
- 生成可复用知识库

适用场景：

- “分析这个账号的视频套路”
- “总结其常见拍摄手法”
- “把结果整理成知识库文档”

---

## 推荐使用顺序

推荐按下面顺序走：

1. 用 `douyin-subscription-manager` 维护你要长期跟踪的账号
2. 用 `douyin-video-harvester` 把目标账号的历史视频抓全
3. 用 `douyin-shot-analysis-kb` 从视频中提炼知识库

如果你跳过第 1 步也不是不行，但长期看会乱。因为一旦账号多起来，没有 registry，你后面连“哪些号已经抓过、哪些号要持续补抓”都说不清。

---

## 最小配置示例

项目目录：

```text
openclaw/
  skills/
  .env
```

`.env`：

```env
TIKHUB_API_TOKEN=tk_xxx_your_token_here
```

skills：

```text
openclaw/skills/douyin-subscription-manager
openclaw/skills/douyin-video-harvester
openclaw/skills/douyin-shot-analysis-kb
```

启动前检查：

```bash
echo $TIKHUB_API_TOKEN
```

如果能打印出来，说明环境变量已经生效。

---

## 执行脚本里如何读取 Key

后面你补 Python 执行层时，统一这样读取：

```python
import os

TIKHUB_API_TOKEN = os.getenv("TIKHUB_API_TOKEN")

if not TIKHUB_API_TOKEN:
    raise RuntimeError("Missing TIKHUB_API_TOKEN")
```

如果你后面要实际请求 TikHub，通常还需要把 token 放到请求头里。**但具体是 `Authorization: Bearer ...` 还是其他 header，以你自己 TikHub 控制台里该接口的示例为准。**

别在这里自作聪明写死。不同服务有时会改头部格式，瞎写只会让你排查半天。

---

## 这套 Skill 依赖什么

### 已有依赖

- OpenClaw 可以识别并加载 skill 目录
- 运行环境支持环境变量
- 你有可用的 TikHub API Token

### 后续通常还会加的依赖

- `requests` 或 `httpx` 用于请求 TikHub
- `python-dotenv` 用于加载 `.env`
- `ffmpeg` / `opencv-python` 用于视频分析
- 文本分析模型或多模态模型用于拍摄手法总结

---

## 你最容易踩的坑

### 1. 以为 skill 自己会联网执行

不会。

Skill 是规则层，不是执行层。没有执行脚本，它不会凭空替你去调 TikHub。

### 2. 以为只装 skill 就能抓全抖音视频

也不会。

抓视频这件事最终还是要有实际请求代码、分页处理、失败重试、数据落库。

### 3. 把 key 放进 markdown

这是低级错误，而且后果很蠢。只要仓库一共享，key 基本等于白送。

### 4. 不做本地 registry

一开始账号少你觉得没必要，后面十几个、几十个账号时你会被自己坑死。哪些抓过、哪些没抓过、哪些要补抓，最后全糊成一锅粥。

---

## 生产使用前要再核对的地方

虽然这套 skill 的能力边界和接口类别是按 TikHub 文档整理的，但在正式接入前，你还是应该在自己的 TikHub 控制台里再确认一遍：

- 具体接口路径
- 请求方法（GET/POST）
- header 格式
- 分页参数命名
- 返回字段结构
- 某些交互接口是否还需要额外 cookie、设备参数或账号登录态

原因很简单：公开文档索引能说明“有这个能力”，但不保证你当前账户版本、套餐、控制台示例和索引文字完全一致。

---

## 建议的下一步

如果你只是要让 OpenClaw 先识别这些能力，到这里已经够了。

如果你要真正跑起来，下一步应该是：

1. 给每个 skill 增加 `scripts/`
2. 在脚本里读取 `TIKHUB_API_TOKEN`
3. 接入真实 TikHub 请求
4. 把抓取结果统一落到 JSON 或数据库
5. 再让分析 skill 基于抓取结果产出知识库

---

## 一句话概括

这不是“装上就能跑”的万能插件，而是一套已经把边界和流程搭好的技能骨架。

**Key 放环境变量，不要放 skill 文件。先让 OpenClaw 识别 skill，再补执行层。**
