#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_module_info.py — Verilog/SystemVerilog 模块结构提取器
（cw-hdl-module-analyze · Phase 1 机械提取）

职责边界：
    只做"机械、可规则化"的信息收集；语义判定（协议识别、FSM 定论、复位
    语义确认等）一律由 Agent 在 Phase 2 完成。凡解析不了的写入
    parser_warnings 提示人工核对，绝不静默丢弃。

特点：
    * 零第三方依赖（仅标准库）
    * 覆盖常见可综合 RTL 写法：ANSI/non-ANSI 端口、parameter/localparam、
      always 系列、assign、模块例化、function/task 名单、generate 计数
    * 等长替换去注释，行号可回溯到原文件

已知局限（升级时参考；发现解析不了应走 parser_warnings）：
    * 不做预处理展开：`include/`define/`ifdef 内容不展开（macro_uses 计数提示）
    * interface 端口、unpacked struct、参数化维度等复杂 SV 语法可能解析不全
    * 实例化识别为启发式（已剔除 function/task/specify 区块与关键字黑名单）

用法：
    python extract_module_info.py <file_or_dir>... [--out json|md]
        --out json   结构化 JSON（默认；供 Phase 4 校验与 Agent 消费）
        --out md     人类可读 Markdown 摘要
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

EXTS = {".v", ".sv", ".vh", ".svh"}

# 实例化识别的关键字黑名单（门级原语 and/or/buf 等故意不在其中：它们本身就是实例）
KEYWORDS = {
    "module", "macromodule", "endmodule", "interface", "endinterface",
    "program", "endprogram", "package", "endpackage", "input", "output",
    "inout", "wire", "reg", "logic", "bit", "tri", "tri0", "tri1", "wand",
    "wor", "parameter", "localparam", "assign", "always", "always_ff",
    "always_comb", "always_latch", "initial", "final", "begin", "end",
    "if", "else", "case", "casez", "casex", "endcase", "default", "for",
    "while", "repeat", "forever", "generate", "endgenerate", "genvar",
    "function", "endfunction", "task", "endtask", "return", "posedge",
    "negedge", "signed", "unsigned", "integer", "int", "real", "realtime",
    "time", "string", "byte", "shortint", "longint", "shortreal", "typedef",
    "struct", "enum", "union", "packed", "modport", "import", "export",
    "assert", "property", "sequence", "cover", "clocking", "wait", "disable",
    "fork", "join", "join_any", "join_none", "unique", "unique0", "priority",
    "const", "var", "virtual", "this", "new", "extends", "implements",
    "static", "automatic", "void", "type", "event", "defparam", "specify",
    "endspecify", "primitive", "endprimitive", "table", "endtable", "cell",
    "config", "design", "instance", "liblist", "use", "rand", "randc",
    "constraint", "solve", "before", "cross", "coverpoint", "bins",
}

MODULE_HEAD_RE = re.compile(
    r"\b(module|macromodule|interface|program|package)\s+(?:automatic\s+)?([A-Za-z_]\w*)"
)
END_KW = {
    "module": "endmodule", "interface": "endinterface",
    "program": "endprogram", "package": "endpackage",
}
RESET_NAME_RE = re.compile(r"^a?(?:rst|reset)(?:_?n)?$", re.IGNORECASE)

PORT_ITEM_RE = re.compile(
    r"^\s*(?:(?P<dir>input|output|inout)\b\s*)?"
    r"(?:(?P<net>wire|reg|logic|bit|tri|tri0|tri1|wand|wor)\b\s*)?"
    r"(?:(?P<signed>signed|unsigned)\b\s*)?"
    r"(?P<packed>(?:\[[^\[\]]*\]\s*)*)"
    r"(?P<name>[A-Za-z_]\w*)\s*"
    r"(?P<unpacked>(?:\[[^\[\]]*\]\s*)*)$"
)
PARAM_ITEM_RE = re.compile(
    r"^\s*(?:parameter|localparam)\b\s*"
    r"(?:(?P<ptype>integer|int|longint|shortint|byte|bit|logic|real|realtime|time|string)\b\s*)?"
    r"(?:(?P<psigned>signed|unsigned)\b\s*)?"
    r"(?P<pdim>(?:\[[^\[\]]*\]\s*)*)"
    r"(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<value>.+)$"
)
BARE_PARAM_RE = re.compile(r"^(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<value>.+)$")
NONANSI_RE = re.compile(
    r"\b(?P<dir>input|output|inout)\b\s*(?:(?P<net>wire|reg|logic|bit|tri)\b\s*)?"
    r"(?:(?P<sg>signed|unsigned)\b\s*)?(?P<dim>(?:\[[^\[\]]*\]\s*)*)(?P<name>[A-Za-z_]\w*)"
)
LOCALPARAM_RE = re.compile(r"\blocalparam\b([^;]*);")
ALWAYS_KW_RE = re.compile(r"\b(always_ff|always_latch|always_comb|always)\b")
EDGE_RE = re.compile(r"\b(posedge|negedge)\s+([A-Za-z_]\w*)")
ASSIGN_RE = re.compile(r"\bassign\b\s*(?:#\s*[^=;]+)?([^=;]+?)\s*=")
INST_RE = re.compile(
    r"(?:^|[;)\s])([A-Za-z_]\w*)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\)\s*)?"
    r"([A-Za-z_]\w*)\s*\("
)
FUNC_RE = re.compile(
    r"\bfunction\b\s+(?:automatic\s+|static\s+)?"
    r"(?:(?:void|integer|int|real|realtime|time|logic|bit|byte|shortint|longint|string)\s+)?"
    r"(?:(?:signed|unsigned)\s+)?(?:\[[^\[\]]*\]\s*)*"
    r"([A-Za-z_]\w*)\s*\("
)
TASK_RE = re.compile(r"\btask\b\s+(?:automatic\s+|static\s+)?([A-Za-z_]\w*)\s*[(;]")
CASE_RE = re.compile(r"\b(?:case|casez|casex)\s*\(\s*([A-Za-z_]\w*)\s*\)")
DECL_RE = re.compile(
    r"\b(?:wire|reg|logic|bit)\b\s*(?:(?:signed|unsigned)\b\s*)?"
    r"(?:\[[^\[\]]*\]\s*)*([A-Za-z_]\w*)"
)
_COMPILER_DIRECTIVES = (
    "timescale|define|undef|include|ifdef|ifndef|elsif|else|endif|resetall|"
    "default_nettype|celldefine|endcelldefine|line|pragma|unconnected_drive|"
    "nounconnected_drive|begin_keywords|end_keywords|__FILE__|__LINE__"
)
MACRO_USE_RE = re.compile(r"`(?!(" + _COMPILER_DIRECTIVES + r"))[A-Za-z_]\w*")


# ---------------------------------------------------------------- 词法预处理

def preprocess(text: str) -> str:
    """移除注释（保留字符串字面量），处理 `\\`+换行 续行。

    等长替换（换行符原样保留），因此后续用 flat 中偏移计算行号是准确的。
    """
    out = []
    i, n = 0, len(text)
    NORMAL, LINE_C, BLOCK_C, STR = 0, 1, 2, 3
    mode = NORMAL
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if mode == NORMAL:
            if c == "/" and nxt == "/":
                mode = LINE_C; out.append("  "); i += 2; continue
            if c == "/" and nxt == "*":
                mode = BLOCK_C; out.append("  "); i += 2; continue
            if c == '"':
                mode = STR; out.append(c); i += 1; continue
            if c == "\\" and nxt == "\n":   # 续行：吃掉反斜杠，保留换行
                out.append(" "); i += 1; continue
            out.append(c); i += 1
        elif mode == LINE_C:
            if c == "\n":
                mode = NORMAL
            out.append(c if c == "\n" else " "); i += 1
        elif mode == BLOCK_C:
            if c == "*" and nxt == "/":
                mode = NORMAL; out.append("  "); i += 2
            else:
                out.append(c if c == "\n" else " "); i += 1
        else:  # STR
            if c == "\\" and nxt:
                out.append(c); out.append(nxt); i += 2; continue
            if c == '"':
                mode = NORMAL
            out.append(c); i += 1
    return "".join(out)


def line_of(flat: str, pos: int) -> int:
    return flat.count("\n", 0, pos) + 1


# ---------------------------------------------------------------- 基础工具

def split_top(s: str) -> list[str]:
    """按深度为 0 的逗号切分（保护 ()[]{} 内的逗号，如 $clog2(D)、{a,b}）。"""
    parts, buf, depth = [], [], 0
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf)); buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def top_level_parens(s: str) -> list[tuple[int, int]]:
    """返回深度为 0 的圆括号对 (open, close) 的位置列表。"""
    pairs, depth, start = [], 0, -1
    for i, ch in enumerate(s):
        if ch in "([{":
            if depth == 0 and ch == "(":
                start = i
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if ch == ")" and depth == 0 and start >= 0:
                pairs.append((start, i)); start = -1
    return pairs


def blank_span(text: str, a: int, b: int) -> str:
    """把 [a,b) 区间替换为等长空白（保留换行以维持行号）。"""
    return text[:a] + re.sub(r"[^\n]", " ", text[a:b]) + text[b:]


def blank_declarations(body: str) -> str:
    """抹掉 function/task/specify/primitive 声明区块（等长）。"""
    out = body
    for kw, endkw in (("function", "endfunction"), ("task", "endtask"),
                      ("specify", "endspecify"), ("primitive", "endprimitive")):
        while True:
            m = re.search(r"\b" + kw + r"\b", out)
            if not m:
                break
            e = re.search(r"\b" + endkw + r"\b", out[m.end():])
            stop = m.end() + e.end() if e else len(out)
            out = blank_span(out, m.start(), stop)
    return out


def read_sensitivity(body: str, pos: int) -> tuple[str | None, int]:
    """从 '@' 之后的位置读取敏感列表文本（括号配平 / * / 标识符）。"""
    while pos < len(body) and body[pos].isspace():
        pos += 1
    if pos < len(body) and body[pos] == "*":
        return "*", pos + 1
    if pos < len(body) and body[pos] == "(":
        depth = 0
        for i in range(pos, len(body)):
            if body[i] == "(":
                depth += 1
            elif body[i] == ")":
                depth -= 1
                if depth == 0:
                    return body[pos + 1:i], i + 1
        return body[pos + 1:], len(body)
    m = re.match(r"[A-Za-z_]\w*", body[pos:])
    if m:
        return m.group(0), pos + m.end()
    return None, pos


def is_state_like(name: str) -> bool:
    n = name.lower()
    return ("state" in n) or ("fsm" in n) or n in {"cs", "ns"}


# ---------------------------------------------------------------- 结构扫描

def scan_modules(flat: str) -> list[dict]:
    mods = []
    for m in MODULE_HEAD_RE.finditer(flat):
        kind = "module" if m.group(1) == "macromodule" else m.group(1)
        i, depth, header_end = m.end(), 0, -1
        while i < len(flat):
            ch = flat[i]
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == ";" and depth == 0:
                header_end = i
                break
            i += 1
        if header_end < 0:
            continue
        em = re.search(r"\b" + END_KW[kind] + r"\b", flat[header_end:])
        body_stop = header_end + em.start() if em else len(flat)
        mods.append({
            "kind": kind, "name": m.group(2),
            "line_start": line_of(flat, m.start()),
            "line_end": line_of(flat, max(body_stop - 1, 0)),
            "header": flat[m.start():header_end + 1],
            "body": flat[header_end + 1:body_stop],
            "body_off": header_end + 1,
        })
    return mods


def parse_params(txt: str, warnings: list, ctx: str) -> list[dict]:
    items = []
    for raw in split_top(txt):
        m = PARAM_ITEM_RE.match(raw) or BARE_PARAM_RE.match(raw)
        if m:
            items.append({
                "name": m.group("name"),
                "type": (m.groupdict().get("ptype") or "").strip(),
                "default": m.group("value").strip(),
            })
        else:
            warnings.append(f"{ctx}: 参数声明 `{raw[:60]}` 无法解析（人工核对）")
    return items


def parse_ansi_ports(txt: str, warnings: list, ctx: str) -> list[dict]:
    ports = []
    cur_dir = cur_type = cur_packed = None
    for raw in split_top(txt):
        m = PORT_ITEM_RE.match(raw)
        if not m:
            warnings.append(
                f"{ctx}: 端口 `{raw[:60]}` 无法解析（可能是 interface/复杂 SV 类型，人工核对）")
            continue
        d = m.group("dir") or None
        if d:
            if d != cur_dir:
                cur_type = None          # 方向切换后类型不跨项继承
            cur_dir = d
        if m.group("net"):
            cur_type = m.group("net")
        pk = m.group("packed").strip() or None
        if pk:
            cur_packed = pk
        if cur_dir is None:
            warnings.append(
                f"{ctx}: 端口 `{m.group('name')}` 方向未知（non-ANSI？将尝试从 body 补齐）")
        ports.append({
            "name": m.group("name"),
            "dir": cur_dir or "?",
            "net_type": cur_type or "",
            "signed": (m.group("signed") or "").strip() == "signed",
            "packed": re.sub(r"\s+", "", (pk or cur_packed or "")),
            "unpacked": re.sub(r"\s+", "", m.group("unpacked") or ""),
        })
    return ports


def parse_header(mod: dict, info: dict, warnings: list, ctx: str) -> None:
    header = mod["header"]
    stem = re.sub(
        r"^\s*(?:module|macromodule|interface|program|package)\s+(?:automatic\s+)?\w+",
        "", header)
    param_span = port_span = None
    for a, b in top_level_parens(stem):
        before = stem[:a].rstrip()
        if before.endswith("#"):
            if param_span is None:
                param_span = (a + 1, b)
        elif port_span is None:
            port_span = (a + 1, b)
    if param_span:
        info["params"] = parse_params(stem[param_span[0]:param_span[1]], warnings, ctx)
    if port_span:
        info["ports"] = parse_ansi_ports(stem[port_span[0]:port_span[1]], warnings, ctx)

    # non-ANSI 补充：方向/位宽声明在 body 中
    if port_span is None or any(p["dir"] == "?" for p in info["ports"]):
        by_name = {p["name"]: p for p in info["ports"]}
        added = False
        for m in NONANSI_RE.finditer(blank_declarations(mod["body"])):
            nm = m.group("name")
            if nm in by_name:
                by_name[nm]["dir"] = m.group("dir")
                if m.group("dim"):
                    by_name[nm]["packed"] = re.sub(r"\s+", "", m.group("dim"))
                if m.group("net"):
                    by_name[nm]["net_type"] = m.group("net")
            else:
                info["ports"].append({
                    "name": nm, "dir": m.group("dir"),
                    "net_type": m.group("net") or "",
                    "signed": (m.group("sg") or "") == "signed",
                    "packed": re.sub(r"\s+", "", m.group("dim") or ""),
                    "unpacked": "",
                })
                added = True
        if added:
            warnings.append(f"{ctx}: 存在 body 内声明的端口，请人工核对端口全集")


def analyze_module(mod: dict, path: Path, flat: str, warnings: list) -> dict:
    ctx = f"{path.name}:{mod['name']}"
    info = {
        "file": str(path), "name": mod["name"], "kind": mod["kind"],
        "line_start": mod["line_start"], "line_end": mod["line_end"],
        "params": [], "ports": [], "localparams": [],
        "always_blocks": [], "assigns": [], "instances": [],
        "functions": [], "tasks": [], "generate_count": 0,
        "edge_signals": [], "clocks": [], "async_resets": [],
        "reset_name_hits": {},
        "fsm_hints": {"state_like": [], "case_on_state_like": []},
    }
    parse_header(mod, info, warnings, ctx)

    body, off = mod["body"], mod["body_off"]
    line = lambda p: line_of(flat, off + p)   # noqa: E731

    # localparam
    for m in LOCALPARAM_RE.finditer(body):
        for item in split_top(m.group(1)):
            pm = PARAM_ITEM_RE.match(item) or BARE_PARAM_RE.match(item)
            if pm:
                info["localparams"].append(
                    {"name": pm.group("name"), "value": pm.group("value").strip(),
                     "line": line(m.start())})
            else:
                warnings.append(f"{ctx}: localparam `{item[:40]}` 解析失败（人工核对）")

    # always 块 + 边沿信号汇总
    edge_counter: Counter = Counter()
    for am in ALWAYS_KW_RE.finditer(body):
        q = am.end()
        while q < len(body) and body[q].isspace():
            q += 1
        sens = None
        if q < len(body) and body[q] == "@":
            sens, _ = read_sensitivity(body, q + 1)
        edges = EDGE_RE.findall(sens or "")
        edge_counter.update((t, s) for t, s in edges)
        info["always_blocks"].append({
            "flavor": am.group(1),
            "sensitivity": re.sub(r"\s+", " ", (sens or "").strip()),
            "edges": [{"type": t, "signal": s} for t, s in edges],
            "line": line(am.start()),
        })

    # assign 左值
    for m in ASSIGN_RE.finditer(body):
        info["assigns"].append(
            {"lhs": re.sub(r"\s+", "", m.group(1)), "line": line(m.start())})

    # function / task 名单（在抹除前）
    info["functions"] = [{"name": m.group(1), "line": line(m.start())}
                         for m in FUNC_RE.finditer(body)]
    info["tasks"] = [{"name": m.group(1), "line": line(m.start())}
                     for m in TASK_RE.finditer(body)]

    # 实例化（启发式；在抹除 function/task 等区块后的文本上匹配）
    for m in INST_RE.finditer(blank_declarations(body)):
        modname, instname = m.group(1), m.group(2)
        if modname in KEYWORDS or instname in KEYWORDS:
            continue
        info["instances"].append(
            {"module": modname, "inst": instname, "line": line(m.start())})

    # FSM 线索
    decl_names = {m.group(1) for m in DECL_RE.finditer(body)}
    decl_names |= {p["name"] for p in info["ports"]}
    decl_names |= {lp["name"] for lp in info["localparams"]}
    state_like = sorted(n for n in decl_names if is_state_like(n))
    case_vars = {m.group(1) for m in CASE_RE.finditer(body)}
    info["fsm_hints"] = {
        "state_like": state_like,
        "case_on_state_like": sorted(v for v in case_vars if v in state_like),
    }
    info["generate_count"] = len(re.findall(r"\bgenerate\b", body))

    # 时钟 / 复位归类（启发式，Agent 须核对）
    info["edge_signals"] = [
        {"edge": t, "signal": s, "count": c} for (t, s), c in sorted(edge_counter.items())
    ]
    pos = {s for (t, s) in edge_counter if t == "posedge"}
    neg = {s for (t, s) in edge_counter if t == "negedge"}
    info["async_resets"] = sorted(s for s in neg if RESET_NAME_RE.match(s))
    info["clocks"] = sorted(pos | {s for s in neg if not RESET_NAME_RE.match(s)})
    candidates = set(info["async_resets"]) | {n for n in decl_names if RESET_NAME_RE.match(n)}
    info["reset_name_hits"] = {
        n: len(re.findall(rf"\b{re.escape(n)}\b", body)) for n in sorted(candidates)
    }
    return info


# ---------------------------------------------------------------- 文件级分析

def analyze_file(path: Path, result: dict) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    flat = preprocess(text)
    m = re.search(r"`timescale\s+(\S+)", flat)
    if m:
        result["timescale"] = m.group(1)
    m = re.search(r"`default_nettype\s+(\w+)", flat)
    if m:
        result["default_nettype"] = m.group(1)
    result["macro_uses"] += len(MACRO_USE_RE.findall(flat))
    for mod in scan_modules(flat):
        result["modules"].append(analyze_module(mod, path, flat, result["parser_warnings"]))


def collect_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files.extend(sorted(q for q in path.rglob("*")
                                if q.suffix.lower() in EXTS))
        else:
            files.append(path)
    return files


# ---------------------------------------------------------------- Markdown 渲染

def render_md(result: dict) -> str:
    L = ["# 结构提取摘要", ""]
    L.append(f"- 文件：{', '.join(result['files'])}")
    if result["timescale"]:
        L.append(f"- timescale：{result['timescale']}")
    if result["default_nettype"]:
        L.append(f"- default_nettype：{result['default_nettype']}")
    if result["macro_uses"]:
        L.append(f"- 宏使用：{result['macro_uses']} 处（本工具不展开宏，相关位宽请人工核对）")
    L.append("")
    for i, m in enumerate(result["modules"], 1):
        L.append(f"## [{i}] {m['kind']} {m['name']}  ({m['file']}:{m['line_start']}-{m['line_end']})")
        L.append("")
        L.append(f"- 参数 {len(m['params'])} | 端口 {len(m['ports'])} | "
                 f"always {len(m['always_blocks'])} | assign {len(m['assigns'])} | "
                 f"实例 {len(m['instances'])} | generate {m['generate_count']}")
        if m["fsm_hints"]["state_like"]:
            L.append(f"- FSM 线索：{', '.join(m['fsm_hints']['state_like'])}")
        if m["clocks"]:
            L.append(f"- 时钟候选：{', '.join(m['clocks'])}")
        if m["async_resets"]:
            L.append(f"- 异步复位候选：{', '.join(m['async_resets'])}")
        L.append("")
        if m["params"]:
            L += ["| 参数 | 类型 | 默认值 |", "|---|---|---|"]
            L += [f"| {p['name']} | {p['type'] or '—'} | {p['default']} |" for p in m["params"]] + [""]
        if m["ports"]:
            L += ["| 端口 | 方向 | 位宽 | 类型 |", "|---|---|---|---|"]
            L += [f"| {p['name']} | {p['dir']} | {p['packed'] or '1'} | {p['net_type'] or '—'} |"
                  for p in m["ports"]] + [""]
        if m["always_blocks"]:
            L += ["| 行 | 类型 | 敏感列表 |", "|---|---|---|"]
            L += [f"| {b['line']} | {b['flavor']} | {b['sensitivity'] or '—'} |"
                  for b in m["always_blocks"]] + [""]
        if m["instances"]:
            L += ["| 行 | 模块 | 实例 |", "|---|---|---|"]
            L += [f"| {x['line']} | {x['module']} | {x['inst']} |" for x in m["instances"]] + [""]
        if m["localparams"]:
            L += ["| 行 | localparam | 值 |", "|---|---|---|"]
            L += [f"| {lp['line']} | {lp['name']} | {lp['value']} |"
                  for lp in m["localparams"]] + [""]
    L += ["## 解析警告（必须逐条人工核对）", ""]
    L += [f"{i}. {w}" for i, w in enumerate(result["parser_warnings"], 1)] or ["（无）"]
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- 入口

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Verilog/SV 模块结构提取（尽力而为，结果须人工核对）")
    ap.add_argument("paths", nargs="+", help="源文件或目录（.v/.sv/.vh/.svh）")
    ap.add_argument("--out", choices=("json", "md"), default="json")
    args = ap.parse_args(argv)

    files = collect_files(args.paths)
    if not files:
        print("error: 未找到 .v/.sv 源文件", file=sys.stderr)
        return 2

    result = {
        "files": [str(f) for f in files],
        "timescale": None, "default_nettype": None, "macro_uses": 0,
        "modules": [], "parser_warnings": [],
    }
    for f in files:
        try:
            analyze_file(f, result)
        except Exception as exc:      # 单文件失败不中断整体
            result["parser_warnings"].append(f"{f}: 解析异常 {exc!r}（该文件需全人工分析）")
    if not result["modules"]:
        result["parser_warnings"].append("未发现 module/interface 声明（检查文件与预处理条件）")

    if args.out == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_md(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
