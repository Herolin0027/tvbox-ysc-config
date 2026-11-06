#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影视仓 / TVBox 配置自动更新脚本
=================================
功能：
  1. 读取 config/sources.json 中的配置源列表
  2. 对每个源依次尝试"主线 + 备用"多个地址，自动做中文域名 punycode 转换
  3. 校验返回内容是否为合法的 TVBox/影视仓 单仓配置（包含 sites/spiders/lives 等字段）
     或 多仓订阅（顶层含 urls 数组）
  4. 将每个源的最新配置保存到 output/<id>.json
  5. 生成多仓订阅文件 output/多仓订阅.json（可直接填进影视仓的"订阅"或"多仓"）
  6. 生成聚合单仓 output/单仓聚合.json（所有源 sites/lives/parses 合并去重）
  7. 生成 shields 徽章 output/shield.json，并把各源状态写回 README
兼容：本脚本同时兼容 GitHub Actions 自动运行 与 本地手动运行。
在 GitHub Actions 中，环境变量 GITHUB_REPOSITORY 会被自动注入（格式 owner/repo），
用于拼出多仓订阅里指向本仓库 raw 文件的完整 URL。
用法：
  python scripts/update.py
"""
import base64
import datetime
import json
import os
import re
import sys
import time
import urllib.parse

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT, "config", "sources.json")
SHORT_DRAMA_FILE = os.path.join(ROOT, "config", "short_drama_sources.json")
OUTPUT_DIR = os.path.join(ROOT, "output")

DEFAULT_REPO = "Herolin0027/tvbox-ysc-config"  # 本地运行时的占位仓库名，GitHub Actions 会自动覆盖

# 注意：部分接口的反爬会针对"完整 Chrome UA"下发挑战页，反而用简洁 UA 能正常返回 JSON
USER_AGENT = "Mozilla/5.0"

TIMEOUT = 15  # 单个地址超时（秒）
MAX_RETRIES = 2  # 单个地址最大尝试次数（仅对超时/连接类瞬态错误重试）
RETRY_BACKOFF = 2  # 重试基础等待秒数
URL_INTERVAL = 1.0  # 每个地址之间的小间隔秒数（降低被限流概率）
SOURCE_INTERVAL = 2  # 每个源之间的间隔秒数（降低被限流概率）

# 判定"像 TVBox 单仓配置"的顶层字段
TVBOX_KEYS = ("sites", "spiders", "lives", "store", "exts", "parses", "flags")
# 多仓订阅格式：顶层为 urls 数组
MULTI_KEYS = ("urls", "订阅")


def _strip_js_comments(text: str) -> str:
    """剔除 JSON 中内嵌的 // 行注释（部分接口会在字段后追加免责注释）。"""
    lines = text.split("\n")
    cleaned = [ln for ln in lines if not ln.lstrip().startswith("//")]
    return "\n".join(cleaned)


def parse_json_lenient(text: str):
    """宽容解析普通 JSON；只移除独立 // 注释行，避免误删 URL 中的 //。"""
    text = text.lstrip("\ufeff\u200b").strip()
    text = _strip_js_comments(text)
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder(strict=False)
        obj, _ = decoder.raw_decode(text)
        return obj


_FONGMI_BASE64_PREFIX = re.compile(r"[A-Za-z0-9]{8}\*\*")


def _fongmi_base64(text: str) -> str:
    """对应 FongMi Decoder.base64：识别 8 位标记** 后的 Base64 内容。"""
    match = _FONGMI_BASE64_PREFIX.search(text)
    if not match or match.end() == len(text):
        return text
    encoded = re.sub(r"\s+", "", text[match.end():]).replace("-", "+").replace("_", "/")
    return base64.b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8")


def _fongmi_aes_cbc(text: str) -> str:
    """对应 FongMi Decoder.cbc + Crypto.decryptAesCbc。"""
    compact = re.sub(r"\s+", "", text)
    raw = bytes.fromhex(compact)
    decoded = raw.decode("utf-8").lower()
    key_start = decoded.index("$#") + 2
    key_end = decoded.index("#$", key_start)
    key_text = decoded[key_start:key_end]
    iv_text = decoded[-13:]
    if len(key_text) > 16:
        raise ValueError("FongMi AES key 长度超过 16 字节")
    key = (key_text + "0" * 16)[:16].encode("utf-8")
    iv = (iv_text + "0" * 16)[:16].encode("utf-8")
    marker = compact.index("2324") + 4
    encrypted = bytes.fromhex(compact[marker:-26])
    plain = AES.new(key, AES.MODE_CBC, iv).decrypt(encrypted)
    return unpad(plain, AES.block_size).decode("utf-8")


def decode_fongmi_payload(url: str, text: str) -> str:
    """按 FongMi Decoder.verify/fix 的顺序处理配置正文。"""
    data = (text or "").lstrip("\ufeff").strip()
    if not data:
        raise ValueError("响应正文为空")
    if not data.startswith("{"):
        if "**" in data:
            data = _fongmi_base64(data)
        if data.startswith("2423"):
            data = _fongmi_aes_cbc(data)

    # 对齐 FongMi Decoder.fix 的相对 JS 路径修复。
    data = re.sub(
        r'"(\.|\.\.)/(.?|.+?)\.js\?(.?|.+?)"',
        lambda m: '"' + urllib.parse.urljoin(url, m.group(0)[1:-1]) + '"',
        data,
    )
    data = data.replace("../", urllib.parse.urljoin(url, "../"))
    data = data.replace("./", urllib.parse.urljoin(url, "./"))
    data = data.replace("__JS1__", "./").replace("__JS2__", "../")
    return data


def parse_fongmi_json(url: str, text: str):
    """先执行 FongMi 正文解码，再解析 JSON。"""
    return parse_json_lenient(decode_fongmi_payload(url, text))

def idn_encode(url: str) -> str:
    """将 URL 中的中文（国际化）域名转成 punycode，避免 DNS 解析失败。
    例如：http://www.饭太硬.com/tv -> http://www.xn--sss604efuw.com/tv
    """
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ""
    try:
        encoded_host = host.encode("idna").decode("ascii")
    except Exception:
        encoded_host = host  # 已是 ascii 或转换失败，原样使用
    netloc = encoded_host
    if parsed.port:
        netloc = f"{encoded_host}:{parsed.port}"
    return urllib.parse.urlunsplit(
        (parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)
    )


def is_single_tvbox_config(data) -> bool:
    """判断是否为可参与单仓聚合的配置；仅有 sites 数组才算单仓。"""
    if not isinstance(data, dict):
        return False
    sites = data.get("sites")
    return isinstance(sites, list) and any(isinstance(site, dict) for site in sites)


def is_multi_subscription(data) -> bool:
    """判断是否为多仓订阅；多仓入口不能误作为单仓参与聚合。"""
    if not isinstance(data, dict):
        return False
    urls = data.get("urls")
    return isinstance(urls, list) and any(
        isinstance(item, dict) and isinstance(item.get("url"), str) and item["url"].strip()
        for item in urls
    )


def is_valid_tvbox_config(data) -> bool:
    """校验 TVBox/影视仓 单仓或多仓结构，避免仅凭字段存在就误判。"""
    return is_single_tvbox_config(data) or is_multi_subscription(data)


def _should_retry(err: Exception, resp_text_len: int = -1) -> bool:
    """判断失败是否值得重试：
    - 超时/连接类瞬态错误：重试
    - 空响应 / JSON 解析失败（疑似服务端反爬冷却）：重试（加长等待）
    - 4xx/5xx、返回了内容但结构不对（确定性失败）：不重试
    """
    if isinstance(err, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True
    if isinstance(err, requests.exceptions.HTTPError):
        return False  # 4xx/5xx 为确定性失败
    if isinstance(err, json.JSONDecodeError):
        return True  # 空响应或非 JSON，可能是反爬/冷却，给一次机会
    if resp_text_len <= 0:
        return True  # 没有拿到任何内容
    return False


def fetch_config(url: str) -> dict:
    """抓取并按 FongMi 官方 Decoder 的规则解码配置。"""
    target = idn_encode(url)
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        resp = None
        try:
            resp = requests.get(
                target,
                headers={
                    "User-Agent": "okhttp/4.12.0",
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip",
                    "Connection": "keep-alive",
                },
                timeout=(10, TIMEOUT),
                allow_redirects=True,
            )
            # FongMi Decoder 读取正文后解析，不以 HTTP 状态码单独判死刑。
            final_url = resp.url or target
            data = parse_fongmi_json(final_url, resp.text)
            if not is_valid_tvbox_config(data):
                preview = repr((resp.text or "")[:120])
                raise ValueError(
                    f"响应不是可识别的 TVBox/FongMi 配置；HTTP {resp.status_code}，"
                    f"Content-Type={resp.headers.get('Content-Type', '未知')}，正文前 120 字={preview}"
                )
            if not resp.ok:
                print(f"      [NOTICE] HTTP {resp.status_code}，但正文可按 FongMi 规则解析，接受配置")
            return data
        except Exception as e:  # noqa: BLE001
            last_err = e
            text_len = len(resp.text or "") if resp is not None else -1
            retryable = (
                isinstance(e, (requests.exceptions.Timeout, requests.exceptions.ConnectionError))
                or text_len <= 0
                or isinstance(e, (json.JSONDecodeError, ValueError))
            )
            if retryable and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * attempt * 2
                print(f"      (第 {attempt} 次失败：{e}，{wait}s 后重试)")
                time.sleep(wait)
            else:
                break
    raise last_err

def _merge_list(fetched, field):
    """合并列表字段。使用完整内容去重，避免同名不同地址的项目被误删。"""
    seen = set()
    out = []
    for _sid, _name, data in fetched:
        values = data.get(field, [])
        if not isinstance(values, list):
            continue
        for item in values:
            ident = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if ident in seen:
                continue
            seen.add(ident)
            out.append(item)
    return out


def merge_configs(fetched):
    """合并单仓配置。多仓订阅明确排除，避免生成空 sites 的伪单仓。"""
    single_sources = [
        item for item in fetched
        if len(item) == 3 and is_single_tvbox_config(item[2])
    ]
    if not single_sources:
        return None

    _base_sid, base_name, base = single_sources[0]
    merged = {}
    list_fields = (
        "lives", "parses", "doh", "rules", "flags", "exts",
        "ads", "hosts", "ijk", "proxy",
    )
    skip = {"sites", *list_fields}
    for k, v in base.items():
        if k not in skip:
            merged[k] = v
    merged["warningText"] = (
        f"本配置由 {len(single_sources)} 个单仓源自动聚合（含{base_name}等），"
        "各站点可用性及插件兼容性以客户端实际测试为准"
    )

    seen_keys = set()
    sites = []
    for sid, _name, data in single_sources:
        for index, site in enumerate(data.get("sites", [])):
            if not isinstance(site, dict):
                continue
            original_key = site.get("key")
            key = str(original_key).strip() if original_key is not None else ""
            if not key:
                key = f"{sid}_site_{index + 1}"
            new_key = key
            if new_key in seen_keys:
                new_key = f"{sid}_{key}"
            suffix = 2
            candidate = new_key
            while candidate in seen_keys:
                candidate = f"{new_key}_{suffix}"
                suffix += 1
            new_key = candidate
            seen_keys.add(new_key)
            copied = dict(site)
            copied["key"] = new_key
            sites.append(copied)
    merged["sites"] = sites

    for field in list_fields:
        # 某些配置把 proxy 等字段定义为对象或字符串；只合并确实为数组的字段。
        values = [item for item in single_sources if isinstance(item[2].get(field), list)]
        if values:
            merged[field] = _merge_list(values, field)
        elif field in base:
            merged[field] = base[field]

    return merged


README_PATH = os.path.join(ROOT, "README.md")
STATUS_START = "<!-- STATUS_START -->"
STATUS_END = "<!-- STATUS_END -->"


def update_readme(status, ok_count, total):
    """把各源更新状态以表格形式写回 README（在 STATUS_START/END 标记之间）。"""
    if not os.path.exists(README_PATH):
        return
    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()
    if STATUS_START not in readme or STATUS_END not in readme:
        return  # 未放置标记则不改动

    lines = []
    lines.append(f"> 🔄 最近更新：{status['updated_at']}（北京时间） · 成功 **{ok_count}/{total}** 个源")
    lines.append("")
    lines.append("| 配置源 | 状态 | 使用地址 |")
    lines.append("| --- | --- | --- |")
    for s in status["sources"]:
        if s.get("cached"):
            lines.append(f"| {s['name']} | 📦 缓存 | 上次成功配置（本次更新未抓到，沿用缓存） |")
        elif s.get("direct_fallback"):
            lines.append(f"| {s['name']} | ⚠️ 直连回退 | 已保留源站地址；本次未通过抓取校验 |")
        elif s["ok"]:
            lines.append(f"| {s['name']} | ✅ 成功 | `{s['used_url']}` |")
        else:
            err = (s.get("error") or "").replace("|", "/")
            if len(err) > 60:
                err = err[:57] + "..."
            lines.append(f"| {s['name']} | ❌ 失败 | {err} |")
    block = "\n".join(lines)

    prefix = readme.split(STATUS_START, 1)[0]
    suffix = readme.split(STATUS_END, 1)[1]
    new_readme = f"{prefix}{STATUS_START}\n{block}\n{STATUS_END}{suffix}"
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_readme)


def write_badge(ok_count, total):
    """生成 shields.io endpoint 徽章 JSON。"""
    if total == 0 or ok_count == 0:
        color = "red"
    elif ok_count < total:
        color = "orange"
    else:
        color = "green"
    badge = {
        "schemaVersion": 1,
        "label": "TVBox 配置",
        "message": f"{ok_count}/{total} 可用",
        "color": color,
    }
    with open(os.path.join(OUTPUT_DIR, "shield.json"), "w", encoding="utf-8") as f:
        json.dump(badge, f, ensure_ascii=False, indent=2)


def main() -> int:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 东八区时间，便于阅读
    tz = datetime.timezone(datetime.timedelta(hours=8))
    now_str = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    # GitHub Actions 中自动注入 GITHUB_REPOSITORY=owner/repo
    # 私人主仓构建时，订阅 URL 必须指向公开发布仓库，而不是私人仓库。
    repo = (
        os.environ.get("PUBLIC_REPOSITORY")
        or os.environ.get("GITHUB_REPOSITORY")
        or os.environ.get("REPO")
        or DEFAULT_REPO
    )
    raw_base = f"https://gh-proxy.org/https://raw.githubusercontent.com/{repo}/main/output"

    status = {"updated_at": now_str, "repo": repo, "sources": []}
    subscriptions = [
        item for item in cfg.get("direct_subscriptions", [])
        if isinstance(item, dict) and item.get("name") and item.get("url")
    ]
    fetched = []  # [(sid, name, data_dict), ...] 用于聚合单仓

    ok_count = 0
    for src in cfg.get("sources", []):
        name = src.get("name", "未知")
        sid = src.get("id", name)
        urls = src.get("urls", [])

        entry = {"id": sid, "name": name, "ok": False, "used_url": None, "error": None}
        saved = False

        for url in urls:
            try:
                data = fetch_config(url)
                out_path = os.path.join(OUTPUT_DIR, f"{sid}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                entry["ok"] = True
                entry["used_url"] = url
                entry["error"] = None
                subscriptions.append(
                    {"name": name, "url": f"{raw_base}/{sid}.json"}
                )
                if is_single_tvbox_config(data):
                    fetched.append((sid, name, data))
                    entry["config_type"] = "single"
                else:
                    entry["config_type"] = "multi"
                ok_count += 1
                saved = True
                print(f"[OK]   {name} <- {url}")
                break
            except Exception as e:  # noqa: BLE001
                print(f"[FAIL] {name}  {url}  ->  {e}")
                entry["error"] = str(e)

            # 地址之间稍作间隔，避免被限流
            time.sleep(URL_INTERVAL)

        if not saved:
            # 所有地址都失败：尝试使用上一次成功抓取的缓存文件
            cache_path = os.path.join(OUTPUT_DIR, f"{sid}.json")
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        cached = json.load(f)
                    if is_valid_tvbox_config(cached):
                        subscriptions.append(
                            {"name": name, "url": f"{raw_base}/{sid}.json"}
                        )
                        if is_single_tvbox_config(cached):
                            fetched.append((sid, name, cached))
                            entry["config_type"] = "single"
                        else:
                            entry["config_type"] = "multi"
                        entry["ok"] = True
                        entry["cached"] = True
                        entry["used_url"] = "(缓存)"
                        ok_count += 1
                        saved = True
                        print(f"[CACHE] {name}  使用上次缓存配置")
                except Exception:
                    pass
            if not saved:
                # 没有本地缓存时，也保留该源的外部直连接口，避免多仓订阅中整项消失。
                # 该入口不代表抓取校验成功；设备端仍会直接访问源站。
                direct_url = src.get("direct_url") or (urls[0] if urls else None)
                if direct_url:
                    subscriptions.append({"name": name, "url": direct_url})
                    entry["direct_fallback"] = True
                    entry["direct_url"] = direct_url
                    print(f"[DIRECT] {name}  抓取失败，保留源站直连接口：{direct_url}")
                entry["error"] = entry["error"] or "所有地址均失败"
                print(f"[FAIL] {name}  全部地址失败")
        status["sources"].append(entry)

        # 源之间稍作间隔，避免集中请求被限流
        time.sleep(SOURCE_INTERVAL)

    # 普通短剧是独立维护清单：同时生成独立文件，并进入多仓与单仓聚合。
    # 不扫描 output 目录，也不读取其他隐藏/私有清单。
    if os.path.exists(SHORT_DRAMA_FILE):
        with open(SHORT_DRAMA_FILE, "r", encoding="utf-8") as f:
            drama_data = json.load(f)
        if is_single_tvbox_config(drama_data):
            drama_sites = []
            for index, site in enumerate(drama_data.get("sites", [])):
                if not isinstance(site, dict):
                    continue
                copied = dict(site)
                original_key = str(copied.get("key") or f"site_{index + 1}").strip()
                copied["key"] = f"short_{original_key}"
                drama_sites.append(copied)
            drama_output = dict(drama_data)
            drama_output["sites"] = drama_sites
            with open(os.path.join(OUTPUT_DIR, "short_drama.json"), "w", encoding="utf-8") as f:
                json.dump(drama_output, f, ensure_ascii=False, indent=2)
            subscriptions.append({
                "name": "普通短剧",
                "url": f"{raw_base}/short_drama.json"
            })
            fetched.append(("short_drama", "普通短剧", drama_output))
            print(f"[OK]   普通短剧清单（{len(drama_sites)} 个入口）")


    # 生成多仓订阅文件（影视仓"订阅/多仓"格式）
    sub_path = os.path.join(OUTPUT_DIR, "多仓订阅.json")
    with open(sub_path, "w", encoding="utf-8") as f:
        json.dump({"urls": subscriptions}, f, ensure_ascii=False, indent=2)

    # 生成聚合单仓文件（把所有成功源的 sites/lives/parses 合并成一个单仓）
    merged = merge_configs(fetched)
    merged_path = os.path.join(OUTPUT_DIR, "单仓聚合.json")
    if merged is not None and merged.get("sites"):
        with open(merged_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"聚合单仓：{merged_path}（共 {len(merged.get('sites', []))} 个站点）")
        status["single_aggregate"] = {
            "generated": True,
            "source_count": len(fetched),
            "site_count": len(merged.get("sites", [])),
        }
    else:
        # 本轮没有可用单仓源时，不覆盖上一次有效的聚合文件。
        status["single_aggregate"] = {
            "generated": False,
            "source_count": 0,
            "site_count": 0,
            "retained_previous": os.path.exists(merged_path),
        }

    # 生成更新状态文件（时间取全部抓取完成之后）
    status["updated_at"] = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(OUTPUT_DIR, "status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    # 生成 shields 徽章并更新 README 状态表
    total = len(cfg.get("sources", []))
    write_badge(ok_count, total)
    update_readme(status, ok_count, total)

    print("\n" + "=" * 50)
    print(f"本次更新：{ok_count}/{total} 个源成功")
    print(f"多仓订阅：{sub_path}（共 {len(subscriptions)} 个入口，含失败源直连回退）")
    if ok_count == 0:
        print("没有任何源更新成功，返回非 0 退出码。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
