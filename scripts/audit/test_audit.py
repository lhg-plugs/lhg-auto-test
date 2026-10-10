#!/usr/bin/env python3
"""lhg-auto-test 确定性测试代码审计：24 条规则，零第三方依赖。

扫描目标目录的测试文件（test_*.py / *_test.py / *.test.js|ts / *.spec.js|ts /
*_test.sh 等），检查小白写测试最常踩的坑：无断言、硬编码等待、三类覆盖
缺失、测试数据不清理、硬编码密钥等。

有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用）。

用法：
    python3 test_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

规则文案均为本项目原创（思路受 dvstack/playwright-agents 的 planner→generator→healer
分层与"先审计划再写代码"启发，未复制任何第三方原文）。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-auto-test/test-audit"

SKIP_DIRS = {
    "node_modules", ".next", "dist", "build", ".git", "coverage",
    "__pycache__", "vendor", ".turbo", "out", ".venv", "venv",
}
TEST_FILE_RES = [
    re.compile(r"(^|[/_.-])test[_-].*\.(py|js|ts|sh)$"),
    re.compile(r".*[_.-]test\.(py|js|ts|sh)$"),
    re.compile(r".*\.(spec|e2e)\.(js|ts)$"),
    re.compile(r".*/tests?/.*\.(py|js|ts|sh)$"),
]
SCAN_EXTS = {".py", ".js", ".ts", ".sh"}


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line",
                 "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line,
                 snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


def is_test_file(path):
    base = os.path.basename(path)
    p = path.replace(os.sep, "/")
    return any(r.search(base) or r.search(p) for r in TEST_FILE_RES)


def collect_files(target):
    out = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext in SCAN_EXTS:
                full = os.path.join(root, f)
                if is_test_file(full):
                    out.append(full)
    return sorted(out)


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


# ---------------------------------------------------------------- 规则注册表
# 每条规则：rule(id, severity, category, title, detail, check)
# check(lines, text, path) -> [(line_no, snippet), ...]

RULES = []


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        RULES.append({
            "id": rule_id, "severity": severity, "category": category,
            "title": title, "detail": detail, "check": fn,
        })
        return fn
    return deco


def _py_test_funcs(lines):
    """找出 Python 测试函数的起止行：[(name, start, end)]。"""
    funcs, cur, indent = [], None, None
    for i, ln in enumerate(lines):
        m = re.match(r"^(\s*)def\s+(test\w*)\s*\(", ln)
        if m:
            if cur:
                funcs.append((cur[0], cur[1], i - 1))
            indent = len(m.group(1))
            cur = (m.group(2), i)
        elif cur and ln.strip() and not ln.startswith(" " * (indent + 1)) \
                and not ln.strip().startswith("#"):
            if re.match(r"^\S", ln):
                funcs.append((cur[0], cur[1], i - 1))
                cur = None
    if cur:
        funcs.append((cur[0], cur[1], len(lines) - 1))
    return funcs


ASSERT_RES = [
    re.compile(r"\bassert\b"), re.compile(r"\bassertEqual\b"),
    re.compile(r"\bexpect\s*\("), re.compile(r"\.to(Be|Equal|Contain|Match|Throw)"),
    re.compile(r"should\."), re.compile(r"\bpytest\.raises\b"),
    re.compile(r"\bassertRaises\b"), re.compile(r"\bself\.assert"),
]

BOUNDARY_WORDS = [
    "边界", "临界", "空值", "超长", "最大值", "最小值", "boundary", "edge",
    "empty", "null", "max", "min", "limit", "overflow", "0 长度", "负数",
]
ERROR_WORDS = [
    "异常", "错误", "失败", "拒绝", "超时", "error", "exception", "raises",
    "invalid", "unauthorized", "forbidden", "timeout", "reject", "4xx", "5xx",
    "500", "400", "401", "403", "404",
]


# ============================ blocker：跑了也白跑 ============================

@rule("AT-NOASSERT-001", "blocker", "断言",
      "测试函数没有任何断言",
      "没有断言的测试永远通过，等于没测。每个测试函数至少要有一个断言，"
      "说清楚'我期望发生什么'。")
def _(lines, text, path):
    if not path.endswith(".py"):
        return []
    hits = []
    for name, start, end in _py_test_funcs(lines):
        body = "\n".join(lines[start:end + 1])
        if not any(r.search(body) for r in ASSERT_RES):
            hits.append((start + 1, lines[start].strip()))
    return hits


@rule("AT-HARDWAIT-001", "blocker", "稳定性",
      "测试里出现硬编码固定等待",
      "time.sleep(5) / waitForTimeout 这类固定等待是 flaky 测试的头号来源："
      "机器慢一点就失败，快一点就浪费时间。应该等'看得见的结果'（元素出现、"
      "状态码返回、文件生成），而不是等固定的秒数。")
def _(lines, text, path):
    hits = []
    for i, ln in enumerate(lines):
        if re.search(r"\btime\.sleep\s*\(\s*\d", ln) \
                or re.search(r"waitForTimeout\s*\(", ln) \
                or re.search(r"\bsleep\s+\d", ln):
            hits.append((i + 1, ln.strip()))
    return hits


@rule("AT-SECRET-001", "blocker", "安全",
      "测试代码里硬编码了密钥/密码",
      "测试代码也会被提交到仓库，硬编码的密码、token、API key 等于公开。"
      "用环境变量或测试专用的假值（如 'test-password-123' 明确标注为假数据）代替。")
def _(lines, text, path):
    hits = []
    for i, ln in enumerate(lines):
        low = ln.lower()
        if re.search(r"(password|passwd|api[_-]?key|secret|token)\s*=\s*['\"]"
                     r"(?!test-|fake-|example|xxx|123)[^'\"]{6,}['\"]", low) \
                and "test-" not in low and "fake" not in low:
            hits.append((i + 1, ln.strip()))
    return hits


@rule("AT-FOCUSED-001", "blocker", "纪律",
      "提交了 focused/only 测试（只跑自己）",
      "it.only / test.only / fit / fdescribe 会让 CI 只跑这一个测试，"
      "其他测试全被静默跳过。本地调试用完必须删掉再提交。")
def _(lines, text, path):
    hits = []
    for i, ln in enumerate(lines):
        if re.search(r"\b(fit|fdescribe)\s*\(", ln) \
                or re.search(r"\b(it|test|describe)\.only\s*\(", ln) \
                or re.search(r"@pytest\.mark\.only", ln):
            hits.append((i + 1, ln.strip()))
    return hits


# ============================ warning：迟早会坑你 ============================

@rule("AT-COV-001", "warning", "覆盖",
      "测试文件缺少边界类用例信号",
      "三类覆盖（正常/边界/异常）缺了'边界'：空值、超长、临界值、特殊字符"
      "这类输入最容易在生产环境炸。建议至少补 2 条边界用例（见 skill lhg-at-cases）。")
def _(lines, text, path):
    low = text.lower()
    if any(w.lower() in low for w in BOUNDARY_WORDS):
        return []
    return [(1, os.path.basename(path))]


@rule("AT-COV-002", "warning", "覆盖",
      "测试文件缺少异常类用例信号",
      "三类覆盖（正常/边界/异常）缺了'异常'：错误输入、权限不足、依赖失败"
      "（网络/数据库）、超时。只测 happy path 的测试给人虚假的安全感。")
def _(lines, text, path):
    low = text.lower()
    if any(w.lower() in low for w in ERROR_WORDS):
        return []
    return [(1, os.path.basename(path))]


@rule("AT-TODO-001", "warning", "纪律",
      "测试代码里残留 TODO/FIXME",
      "TODO 意味着'这里还没测完'。带着 TODO 的测试套件上线，等于带着"
      "已知盲区上线：要么补上，要么删掉并记录原因。")
def _(lines, text, path):
    hits = []
    for i, ln in enumerate(lines):
        if re.search(r"\b(TODO|FIXME|XXX|HACK)\b", ln):
            hits.append((i + 1, ln.strip()[:80]))
    return hits


@rule("AT-SKIP-001", "warning", "纪律",
      "测试被跳过但没有写原因",
      "@pytest.mark.skip / test.skip / xit 没有 reason，等于悄悄少测了一块。"
      "跳过可以，但必须写清为什么跳过、什么时候恢复。")
def _(lines, text, path):
    hits = []
    for i, ln in enumerate(lines):
        if re.search(r"@pytest\.mark\.skip(?!\s*\()", ln) \
                or re.search(r"@pytest\.mark\.skipif\s*\(\s*True", ln) \
                or re.search(r"\b(xit|xtest|test\.skip|it\.skip)\s*\(", ln):
            hits.append((i + 1, ln.strip()))
    return hits


@rule("AT-NET-001", "warning", "隔离",
      "单元测试里出现真实网络请求",
      "requests.get / fetch / curl 真实地址的测试依赖外部服务：对方挂了、"
      "网络抖了，你的测试就红了。单元测试应该 mock 掉网络，只测自己的逻辑；"
      "真要测网络走单独的集成测试。")
def _(lines, text, path):
    hits = []
    for i, ln in enumerate(lines):
        if re.search(r"requests\.(get|post|put|delete)\s*\(\s*['\"]https?://", ln) \
                or re.search(r"fetch\s*\(\s*['\"]https?://", ln) \
                or re.search(r"curl\s+['\"]?https?://", ln):
            if "mock" not in text.lower() and "127.0.0.1" not in ln \
                    and "localhost" not in ln:
                hits.append((i + 1, ln.strip()[:80]))
    return hits


@rule("AT-RAND-001", "warning", "稳定性",
      "测试用了随机数但没有固定种子",
      "没固定种子的随机测试今天过、明天挂，失败了还复现不了。"
      "random.seed(...) / faker.seed(...) 固定下来，或者把随机部分抽出去只测确定性逻辑。")
def _(lines, text, path):
    if not re.search(r"\brandom\.(randint|choice|random|shuffle|uniform)\b", text):
        return []
    if re.search(r"random\.seed\s*\(", text):
        return []
    hits = []
    for i, ln in enumerate(lines):
        if re.search(r"\brandom\.(randint|choice|random|shuffle|uniform)\b", ln):
            hits.append((i + 1, ln.strip()))
    return hits


@rule("AT-TIME-001", "warning", "稳定性",
      "测试依赖当前时间但没有冻结时间",
      "datetime.now() / Date.now() 让测试结果取决于'什么时候跑'："
      "跨天、跨时区、CI 排队都会让它变红。用 freezegun / jest.useFakeTimers"
      "这类时间冻结手段，或把时间作为参数传进去。")
def _(lines, text, path):
    if not re.search(r"datetime\.(now|today)\s*\(|Date\.now\s*\(", text):
        return []
    if re.search(r"freezegun|useFakeTimers|mock.*datetime|freeze_time", text):
        return []
    hits = []
    for i, ln in enumerate(lines):
        if re.search(r"datetime\.(now|today)\s*\(|Date\.now\s*\(", ln):
            hits.append((i + 1, ln.strip()))
    return hits


@rule("AT-CLEAN-001", "warning", "隔离",
      "测试创建了临时资源但没有清理",
      "测试里建了临时文件、测试数据库记录、测试用户，却没有 teardown/fixture"
      "清理：跑一次没事，跑十次环境就脏了，还会互相污染。用完即删，"
      "优先用框架的 fixture/teardown 机制。")
def _(lines, text, path):
    creates = re.search(
        r"tempfile|NamedTemporaryFile|mkdtemp|open\s*\([^)]*['\"]w['\"]|"
        r"INSERT INTO|create_user|mkdir", text)
    cleans = re.search(
        r"teardown|fixture|addfinalizer|afterEach|afterAll|cleanup|"
        r"unlink|rmtree|shutil\.rmtree|tmp_path", text)
    if creates and not cleans:
        return [(1, "创建了临时资源但未发现清理机制")]
    return []


@rule("AT-WEAKASSERT-001", "warning", "断言",
      "断言太弱，几乎测不出问题",
      "assert True / expect(x).toBeTruthy() / assert result 这类断言"
      "什么都拦不住：函数返回错了它也过。断言要具体到值、状态码、字段，"
      "说清楚'我到底在验证什么'。")
def _(lines, text, path):
    hits = []
    for i, ln in enumerate(lines):
        if re.search(r"^\s*assert\s+True\s*$", ln) \
                or re.search(r"\.toBeTruthy\(\)", ln) \
                or re.search(r"^\s*assert\s+[a-zA-Z_][a-zA-Z0-9_]*\s*$", ln) \
                or re.search(r"expect\([a-zA-Z_][a-zA-Z0-9_]*\)\.toBeDefined\(\)", ln):
            hits.append((i + 1, ln.strip()))
    return hits


@rule("AT-BAREEXCEPT-001", "warning", "断言",
      "测试里用裸 except 吞掉了异常",
      "try/except: pass 的测试：被测代码抛了不该抛的异常，测试照样绿。"
      "要么断言'应该抛什么异常'（pytest.raises），要么别 catch。")
def _(lines, text, path):
    hits = []
    for i, ln in enumerate(lines):
        if re.match(r"^\s*except\s*:\s*$", ln):
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if re.match(r"^\s*(pass|\.\.\.)\s*$", nxt):
                hits.append((i + 1, ln.strip()))
    return hits


@rule("AT-RETRY-001", "warning", "稳定性",
      "测试里写了重试循环",
      "测试里 for/while 重试'直到成功'，等于承认这个测试不稳定。"
      "不稳定要修的是被测代码或等待方式，不是给测试加重试。")
def _(lines, text, path):
    hits = []
    for i, ln in enumerate(lines):
        if re.search(r"for\s+\w+\s+in\s+range\s*\(\s*\d+\s*\)\s*:\s*#.*重试", ln) \
                or re.search(r"retry|重试", ln) and re.search(r"while|for", ln):
            if "test" in path.lower():
                hits.append((i + 1, ln.strip()[:80]))
    return hits


@rule("AT-ABSPATH-001", "warning", "可移植",
      "测试里硬编码了绝对路径",
      "/home/xxx、D:\\ 这类绝对路径换台机器就跑不起来。"
      "用相对路径、tmp_path 或环境变量代替。")
def _(lines, text, path):
    hits = []
    for i, ln in enumerate(lines):
        if re.search(r"['\"]/(home|Users|tmp|var)/[^'\"]+['\"]", ln) \
                or re.search(r"['\"][A-Z]:\\\\[^'\"]+['\"]", ln):
            hits.append((i + 1, ln.strip()[:80]))
    return hits


@rule("AT-EMPTY-001", "warning", "纪律",
      "测试文件里一个测试用例都没有",
      "空的测试文件会让人误以为'这块有测试覆盖'。删掉它，或者补上用例。")
def _(lines, text, path):
    if path.endswith(".py"):
        if not re.search(r"^\s*def\s+test", text, re.M):
            return [(1, "未发现 test 函数")]
    elif path.endswith((".js", ".ts")):
        if not re.search(r"\b(it|test)(\.only|\.skip)?\s*\(", text):
            return [(1, "未发现 it/test 用例")]
    elif path.endswith(".sh"):
        if "curl" not in text and "assert" not in text.lower():
            return [(1, "shell 测试既无请求也无断言")]
    return []


@rule("AT-ORDERDEP-001", "warning", "隔离",
      "测试可能依赖执行顺序",
      "模块级可变状态（全局 dict/list 在测试里被修改）会让测试"
      "'单独跑能过、一起跑就挂'。每个测试应该自给自足，不依赖其他测试的执行结果。")
def _(lines, text, path):
    if not path.endswith(".py"):
        return []
    hits = []
    for i, ln in enumerate(lines):
        if re.match(r"^[A-Z_][A-Z0-9_]*\s*=\s*(\[|\{|dict|list)", ln) \
                or re.match(r"^[a-z_][a-z0-9_]*\s*=\s*(\[|\{)", ln):
            rest = "\n".join(lines[i + 1:])
            var = ln.split("=")[0].strip()
            if re.search(r"\b%s\s*(\[.+?\]|=)|\b%s\.(append|update|pop|clear)\b"
                         % (re.escape(var), re.escape(var)), rest):
                hits.append((i + 1, ln.strip()))
    return hits


# ============================ nit：顺手修掉 ============================

@rule("AT-NAME-001", "nit", "可读",
      "测试函数名看不出在测什么",
      "test1、test_foo 这类名字，失败时你根本不知道挂的是哪条用例。"
      "名字 = 用例编号 + 在测什么（如 test_TC03_空用户名拒绝登录）。")
def _(lines, text, path):
    hits = []
    for i, ln in enumerate(lines):
        m = re.match(r"^\s*def\s+(test\d+|test_foo|test_bar|test_x|test_a)\s*\(", ln)
        if m:
            hits.append((i + 1, ln.strip()))
        m2 = re.search(r"\b(it|test)\s*\(\s*['\"](test|foo|bar|xxx)['\"]", ln)
        if m2:
            hits.append((i + 1, ln.strip()))
    return hits


@rule("AT-PRINT-001", "nit", "卫生",
      "测试代码里残留 print 调试语句",
      "print 是调试时留下的，测试报告里满屏输出会淹没真正的信息。"
      "删掉，或换成框架的日志/断言信息。")
def _(lines, text, path):
    hits = []
    for i, ln in enumerate(lines):
        if re.search(r"^\s*print\s*\(", ln) and "test" in path.lower():
            hits.append((i + 1, ln.strip()[:60]))
    return hits


@rule("AT-LOOPASSERT-001", "nit", "断言",
      "循环里写断言但没有参数化",
      "for 循环里 assert：第一次失败就停了，后面的输入根本没测到。"
      "用 @pytest.mark.parametrize / test.each 把输入摊平成独立用例。")
def _(lines, text, path):
    if "parametrize" in text or "test.each" in text:
        return []
    if not path.endswith(".py"):
        return []
    hits = []
    for name, start, end in _py_test_funcs(lines):
        body = "\n".join(lines[start:end + 1])
        if re.search(r"^\s*for\s+", body, re.M) \
                and any(r.search(body) for r in ASSERT_RES):
            hits.append((start + 1, "函数 %s 内循环+断言" % name))
    return hits


@rule("AT-SHAREDATA-001", "nit", "隔离",
      "多个测试共享同一份可变测试数据",
      "模块级的 dict/list 被多个测试读写，一个测试改了数据，"
      "另一个测试的行为就变了。用 fixture 每次生成 fresh 数据。")
def _(lines, text, path):
    if not path.endswith(".py"):
        return []
    shared = re.findall(r"^([a-z_][a-z0-9_]*)\s*=\s*(\[|\{)", text, re.M)
    funcs = _py_test_funcs(lines)
    hits = []
    for var, _ in shared:
        users = [n for n, s, e in funcs
                 if re.search(r"\b%s\b" % re.escape(var), "\n".join(lines[s:e + 1]))]
        if len(users) >= 2:
            hits.append((1, "共享变量 %s 被 %d 个测试使用" % (var, len(users))))
    return hits


@rule("AT-COMMENT-001", "nit", "可读",
      "复杂测试缺少意图说明",
      "超过 15 行的测试函数如果没有任何注释/文档字符串，"
      "三个月后没人知道它到底在验证什么业务规则。加一行说清意图。")
def _(lines, text, path):
    if not path.endswith(".py"):
        return []
    hits = []
    for name, start, end in _py_test_funcs(lines):
        if end - start >= 15:
            body = "\n".join(lines[start:end + 1])
            if '"""' not in body and "'''" not in body \
                    and not re.search(r"^\s*#", body, re.M):
                hits.append((start + 1, "函数 %s 超过 15 行无注释" % name))
    return hits


@rule("AT-DUPSETUP-001", "nit", "卫生",
      "多个测试重复写相同的准备代码",
      "3 个以上测试函数出现雷同的准备代码（>3 行连续相同），"
      "抽成 fixture/conftest 或 setup 函数，一处改处处生效。")
def _(lines, text, path):
    if not path.endswith(".py"):
        return []
    blocks = {}
    for name, start, end in _py_test_funcs(lines):
        body_lines = [l.strip() for l in lines[start + 1:end + 1]
                      if l.strip() and not l.strip().startswith("#")]
        for j in range(len(body_lines) - 3):
            key = "\n".join(body_lines[j:j + 4])
            blocks.setdefault(key, set()).add(name)
    hits = []
    for key, users in blocks.items():
        if len(users) >= 3 and "assert" not in key:
            hits.append((1, "%d 个测试共享雷同准备代码，建议抽 fixture"
                         % len(users)))
            break
    return hits


# ---------------------------------------------------------------- 主流程

SEV_ORDER = {"blocker": 0, "warning": 1, "nit": 2}
FAIL_ON_LEVEL = {"blocker": 0, "warning": 1, "nit": 2}


def audit(target):
    files = collect_files(target)
    findings = []
    for path in files:
        text = read_text(path)
        lines = text.split("\n")
        rel = os.path.relpath(path, target)
        for r in RULES:
            try:
                for line_no, snippet in r["check"](lines, text, path):
                    findings.append(Finding(
                        r["id"], r["severity"], r["category"], r["title"],
                        rel, line_no, snippet, r["detail"]))
            except Exception:
                continue  # 单条规则出错不影响整体：fail-open
    findings.sort(key=lambda f: (SEV_ORDER[f.severity], f.file, f.line))
    return files, findings


def main():
    ap = argparse.ArgumentParser(description="lhg-auto-test 测试代码审计")
    ap.add_argument("--target", required=True, help="要扫描的目录")
    ap.add_argument("--format", default="text", choices=["json", "text"])
    ap.add_argument("--fail-on", default="blocker",
                    choices=["blocker", "warning", "nit"])
    args = ap.parse_args()

    target = os.path.abspath(args.target)
    files, findings = audit(target)
    summary = {
        "tool": TOOL, "version": VERSION, "target": target,
        "files_scanned": len(files), "rules_run": len(RULES),
        "blocker": sum(1 for f in findings if f.severity == "blocker"),
        "warning": sum(1 for f in findings if f.severity == "warning"),
        "nit": sum(1 for f in findings if f.severity == "nit"),
    }

    if args.format == "json":
        print(json.dumps({"summary": summary,
                          "findings": [f.to_dict() for f in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print("lhg-auto-test 审计报告  (v%s)" % VERSION)
        print("目标: %s  | 扫描测试文件 %d 个 | 规则 %d 条"
              % (target, summary["files_scanned"], summary["rules_run"]))
        print("blocker %d | warning %d | nit %d"
              % (summary["blocker"], summary["warning"], summary["nit"]))
        print("-" * 60)
        for f in findings:
            print("[%s][%s] %s:%s" % (f.severity, f.rule_id, f.file, f.line))
            print("  %s" % f.title)
            print("  %s" % f.snippet[:100])
        if not findings:
            print("干净：没有发现。")

    level = FAIL_ON_LEVEL[args.fail_on]
    bad = any(SEV_ORDER[f.severity] <= level for f in findings)
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
