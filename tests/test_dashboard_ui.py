"""v3.7.2 实时看板 UI — 与桌面主题一致性 / 字号可读性 / 渲染健壮性。"""
import re
from pathlib import Path

import pytest

HTML_PATH = Path("server/dashboard.html")


@pytest.fixture(scope="module")
def html() -> str:
    return HTML_PATH.read_text(encoding="utf-8")


def test_palette_matches_desktop_theme(html):
    """看板调色板必须与 ui/theme.py colors() 对齐。"""
    from ui.theme import colors

    theme = colors()
    for token in ("bg_body", "bg_card", "bg_header", "border", "text_primary",
                  "accent", "accent_bright"):
        value = theme[token].lower()
        assert value in html.lower(), f"看板缺少桌面主题色 {token}={value}"


def test_status_colors_and_spec_color(html):
    lowered = html.lower()
    assert "#3e9b68" in lowered      # 正常
    assert "#c4922a" in lowered      # 判异 / 超规格
    assert "#e00000" in lowered      # 离线 / 严重
    assert "#9a3a62" in lowered      # USL/LSL 规格线


def test_base_font_size_readable(html):
    """基准字号 ≥ 15px（旧版卡片标题仅 13px / 说明 11px，车间看不清）。"""
    match = re.search(r"--fs:\s*(\d+(?:\.\d+)?)px", html)
    assert match, "未定义 --fs 基准字号"
    assert float(match.group(1)) >= 15


def test_font_scale_control_present(html):
    """字号可调（车间大屏），并持久化到本地存储。"""
    assert "fs-up" in html and "fs-down" in html and "fs-reset" in html
    assert "localStorage" in html
    assert "--fs" in html and "--fs-chart" in html


def test_chinese_font_stack_declared(html):
    for family in ("Microsoft YaHei", "Noto Sans CJK SC", "PingFang SC"):
        assert family in html


def test_hidpi_and_axis_rendering(html):
    """高 DPI 缩放 + 坐标轴刻度/网格 + 悬停提示，保证图表可读。"""
    assert "devicePixelRatio" in html
    assert "setTransform" in html
    assert "ResizeObserver" in html
    assert "tooltip" in html
    assert "规格带" in html or "rgba(231,76,60,.07)" in html


def test_interaction_contract_kept(html):
    """既有交互与后端契约保持不变。"""
    assert "wheel" in html and "dblclick" in html
    assert "mousedown" in html and "mousemove" in html
    assert "charts[key] = c;" in html
    assert "dev: device, ch" in html
    assert "/api/plant" in html and "/api/oee" in html and "/api/cost" in html
    assert "/api/downtime" in html and "/ws/stream" in html
    assert "USL" in html and "LSL" in html


def test_sections_and_empty_state(html):
    for section in ("产线拓扑", "实时 OEE", "成本损失", "实时控制图"):
        assert section in html
    assert "等待设备数据" in html
    assert "charts-empty" in html


def test_token_passthrough_and_reconnect(html):
    """令牌由服务端 HttpOnly Cookie 携带，页面不得再从查询串读取或写回。

    同域 fetch 与 WebSocket（含断线后的 setTimeout 重连）由浏览器自动附带
    ``akia_dashboard``。整页刷新会丢掉内存中的控制图，因此仍然禁止 location.reload。
    """
    script = re.findall(r"<script>(.*?)</script>", html, re.S)[0]

    assert "URLSearchParams(location.search)" not in html
    assert 'get("token")' not in script
    assert "encodeURIComponent(TOKEN)" not in html
    assert "?token=" not in html
    assert re.search(r"\bTOKEN\b", script) is None
    assert "document.cookie" not in script

    strip = re.search(
        r'if \(location\.search\.includes\("token="\)\) \{.*?\n\}',
        script,
        re.S,
    )
    assert strip is not None, "地址栏里的 token= 必须被删掉，且不得当作凭证"
    block = strip.group(0)
    assert "const clean = new URL(location.href);" in block
    assert 'clean.searchParams.delete("token");' in block
    assert (
        'history.replaceState(null, "", clean.pathname + clean.search + clean.hash);'
        in block
    )
    assert "encodeURIComponent" not in block
    assert "fetch(" not in block and "WebSocket" not in block
    without_strip = script.replace(block, "", 1)
    assert "token" not in without_strip.lower()
    strip_at = script.index(block)
    assert strip_at < script.index("function api(")
    assert strip_at < script.index("const wsUrl")
    assert strip_at < script.index("function connect(")

    api_body = re.search(r"function api\(path\) \{(.*?)\}", script, re.S)
    assert api_body is not None
    assert api_body.group(1).strip() == "return path;"
    fetches = re.findall(r"fetch\(([^)]*)\)", script)
    assert fetches
    assert all(call.startswith("api(") and "token" not in call for call in fetches)

    ws_assign = re.search(r"const wsUrl = ([^;]+);", script)
    assert ws_assign is not None
    assert ws_assign.group(1) == 'wsScheme + location.host + "/ws/stream"'
    assert script.count("new WebSocket(") == 1
    assert "new WebSocket(wsUrl)" in script
    assert 'credentials: "omit"' not in script
    assert "credentials: 'omit'" not in script

    close_handler = re.search(r"ws\.onclose = \(\) => \{.*?\};", script, re.S)
    assert close_handler is not None
    assert "setTimeout(connect" in close_handler.group(0)
    assert "location.reload" not in html

    server = Path("server/app.py").read_text(encoding="utf-8")
    assert 'response.set_cookie(' in server
    assert '"akia_dashboard"' in server
    assert "httponly=True" in server
    assert 'samesite="strict"' in server
    assert 'supplied = _presented_token(ws.headers)' in server
    assert 'request.query_params.get("token"' not in server
    assert 'ws.query_params.get("token"' not in server
    presented = re.search(
        r"def _presented_token\(headers\).*?return _cookie_token",
        server,
        re.S,
    )
    assert presented is not None


def test_js_braces_balanced(html):
    """轻量语法兜底 — <script> 内花括号/圆括号配平（防止手改破坏页面）。"""
    script = re.findall(r"<script>(.*?)</script>", html, re.S)[0]
    for open_ch, close_ch in (("{", "}"), ("(", ")"), ("[", "]")):
        assert script.count(open_ch) == script.count(close_ch), \
            f"脚本 {open_ch}{close_ch} 不配平"


def test_no_external_assets(html):
    """离线工厂环境 — 不依赖 CDN / 外链字体。"""
    assert "http://cdn" not in html and "https://cdn" not in html
    assert "fonts.googleapis" not in html
