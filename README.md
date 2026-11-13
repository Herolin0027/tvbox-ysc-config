# 影视仓配置聚合仓库（TVBox Config Aggregator）

![配置状态](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FHerolin0027%2Ftvbox-ysc-config%2Fmain%2Foutput%2Fshield.json)
![更新频率](https://img.shields.io/badge/%E6%9B%B4%E6%96%B0-%E6%AF%8F%E5%A4%A9%202%20%E6%AC%A1-blue)

聚合 **肥猫、饭太硬、饭太硬江苏福建专用、王二小、老刘备、小马、讴歌（欧歌）、4K小盒子、小盒子单仓、拾光多仓、挺好分享多仓、巧技、南风** 等配置，通过 **GitHub Actions 定时自动更新**，并把结果直接提交回本仓库，供影视仓、TVBox、OK影视等软件随时拉取最新接口。

> 所有配置均来自互联网公开分享，版权归原作者所有；本仓库仅做聚合与镜像，仅供学习交流，请勿商用。

---

## 一、源可用性状态

<!-- STATUS_START -->
> 🔄 最近更新：2026-11-13 16:55:19（北京时间） · 成功 **10/12** 个源

| 配置源 | 状态 | 使用地址 |
| --- | --- | --- |
| 肥猫 | 📦 缓存 | 上次成功配置（本次更新未抓到，沿用缓存） |
| 饭太硬 | ✅ 成功 | `http://www.饭太硬.cc/tv` |
| 王二小 | ✅ 成功 | `https://d.kstore.dev/download/9280/wex.json` |
| 老刘备 | ✅ 成功 | `https://raw.liucn.cc/box/m.json` |
| 小马 | ✅ 成功 | `https://szyyds.cn/tv/x.json` |
| 讴歌 | 📦 缓存 | 上次成功配置（本次更新未抓到，沿用缓存） |
| 4K小盒子 | ✅ 成功 | `http://xhztv.top/4k.json` |
| 小盒子单仓 | ✅ 成功 | `http://xhztv.top/xhz` |
| 拾光多仓 | ✅ 成功 | `http://xmbjm.fh4u.org/dc.txt` |
| 挺好分享多仓 | ✅ 成功 | `http://ztha.top/TVBox/GYCK.json` |
| 巧技 | ⚠️ 直连回退 | 已保留源站地址；本次未通过抓取校验 |
| 南风 | ⚠️ 直连回退 | 已保留源站地址；本次未通过抓取校验 |
<!-- STATUS_END -->

## 二、仓库结构

```
tvbox-ysc-config/
├── .github/workflows/update.yml   # GitHub Actions 自动更新工作流
├── config/sources.json            # 配置源列表（主地址 + 备用地址），可自行增删改
├── scripts/update.py              # 核心更新脚本（下载→校验→合并→落盘→更新状态）
├── output/                        # 更新产物（由脚本自动生成并提交）
│   ├── 多仓订阅.json               # 多仓聚合订阅（推荐，App 内可切换各源）
│   ├── 单仓聚合.json               # 单仓聚合（仅合并抓取成功的单仓源；多仓源只进入多仓订阅）
│   ├── shield.json                # shields.io 状态徽章数据
│   ├── status.json                # 各源更新状态（机器可读）
│   ├── feimao.json / fantaiying.json / ...  # 各源独立配置
│   └── ...
├── requirements.txt
└── README.md
```

## 三、在影视仓 / TVBox 中使用

部署完成后，把下面任一地址填入 App 的「设置 → 配置地址」：

| 类型 | 地址 | 说明 |
| --- | --- | --- |
| **多仓订阅（推荐）** | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/多仓订阅.json` | App 内可在各源之间切换 |
| **单仓聚合** | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/单仓聚合.json` | 所有源站点合并成一个，无需切换 |
| 单仓 · 肥猫 | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/feimao.json` | 单独使用某一个源 |
| 单仓 · 饭太硬 | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/fantaiying.json` | |
| 饭太硬江苏福建专用 | `https://cdn09022024.gitlink.org.cn/api/v1/repos/xxooo/in/raw/in.bmp` | 独立入口，不参与普通饭太硬回退 |
| 单仓 · 巧技 | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/qiaoji.json` | |
| 单仓 · 南风 | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/nanfeng.json` | |
| 单仓 · 王二小 | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/wangerxiao.json` | |
| 单仓 · 老刘备 | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/laoliubei.json` | |
| 单仓 · 小马 | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/xiaoma.json` | |
| 单仓 · 讴歌 | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/ouge.json` | |
| 单仓 · 4K小盒子 | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/4k.json` | |
| 单仓 · 小盒子单仓 | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/xiaohezi.json` | |
| 单仓 · 拾光多仓 | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/shiguang.json` | |
| 单仓 · 挺好分享多仓 | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/tinghao.json` | |
| **普通短剧** | `https://raw.githubusercontent.com/Herolin0027/tvbox-ysc-config/main/output/short_drama.json` | 同时加入多仓订阅与单仓聚合，也可单独订阅 |

> 多仓订阅与单仓文件里的地址由脚本根据 `GITHUB_REPOSITORY` 环境变量自动生成。若国内直连 raw.githubusercontent.com 慢，可套一层 `ghproxy` / `gh-proxy` 等加速前缀。

### 普通短剧来源

普通短剧由 `config/short_drama_sources.json` 独立维护，自动更新时会同步生成 `output/short_drama.json`，并自动加入多仓订阅与单仓聚合。当前收录：星芽短剧、喜福短剧、55短剧、果果短剧、红果短剧、低端影视短剧、牛牛短剧、短剧大全、短剧巴士、毒舌短剧。

如需增删普通短剧来源，请编辑上述清单；不要直接修改自动生成的 `output/short_drama.json`。

## 四、自动更新机制

- 推送后，GitHub 自动识别 `.github/workflows/update.yml`。
- 默认每天 **02:00 和 14:00（UTC，即北京时间 10:00 和 22:00）** 自动更新一次。
- 也可在 **Actions → Auto Update TVBox Configs → Run workflow** 手动触发。
- 更新结果自动提交回 `main` 分支，README 状态表与徽章同步刷新。
- 工作流使用内置 `GITHUB_TOKEN`，无需配置任何密钥。

## 五、自定义配置源

编辑 `config/sources.json` 即可增删配置源或更换地址：

```json
{
  "id": "mysource",
  "name": "我的源",
  "urls": [
    "https://example.com/tv",
    "https://backup.example.com/tv"
  ]
}
```

- `id`：输出文件名（建议英文小写）。
- `name`：在多仓订阅与状态表中展示的名字。
- `urls`：依次尝试的地址列表，第一个成功的会被使用；可按"主地址在前、备用在后"排列。
- `direct_subscriptions`：直接加入多仓订阅的外部入口，不参与 JSON 抓取和单仓聚合，适合 BMP 等特殊格式。
- 修改后推送到 `main` 分支即会自动触发一次更新。

## 六、本地手动更新（可选）

```bash
pip install -r requirements.txt
REPO=Herolin0027/tvbox-ysc-config python scripts/update.py
```

## 七、脚本特性

- **中文域名自动转 punycode**：`饭太硬.com` → `xn--sss604efuw.com`，避免 DNS 解析失败。
- **多地址回退**：每个源按顺序尝试主/备用地址，单个地址失败不影响其他源。
- **智能重试**：仅对超时、连接错误、空响应等瞬态问题退避重试；4xx/5xx 等确定性失败直接跳过。
- **兼容多仓订阅**：既支持单仓（含 sites 字段），也支持多仓订阅（顶层 urls 数组）格式。
- **反爬兼容**：使用简洁 UA（部分接口对完整浏览器 UA 下发挑战页），自动剔除 JSON 内嵌的 `//` 注释，兼容未转义控制字符。
- **聚合单仓**：仅把有效单仓源的 `sites` 按 key 去重合并；多仓订阅源不会误纳入单仓。列表字段按完整内容去重，避免同名不同地址的解析器被误删。
- **状态可视化**：每次更新自动刷新 README 状态表与 shields.io 徽章。
- **单仓/多仓分型**：多仓源保留在多仓列表，不参与单仓聚合；单仓聚合只接受含有效 `sites` 数组的配置。\n- **部分成功可用**：只要有可用源就产出订阅，失败源记录在 `status.json` 与 README 状态表。\n- **回归测试**：构建前运行单元测试，覆盖配置类型判断、重复项合并和聚合结果。

## 八、常见问题

- **某个源一直失败？** 大部分源做了地区/频率限制，GitHub Actions 与本地网络环境不同，可能某个环境能访问、另一个不能。脚本会按 `urls` 顺序自动尝试所有备用地址，只把成功的写入。
- **自动提交会不会死循环？** 不会。push 触发只监听 `config/`、`scripts/`、`requirements.txt` 的变更，自动提交只改 `output/` 与 README 状态区，不会再次触发。

## 九、免责声明

本项目仅用于学习、测试与个人使用；聚合的接口资源来自互联网公开分享，版权归原作者所有。若涉及侵权，请联系删除相应内容。
