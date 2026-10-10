#!/usr/bin/env python3
"""lhg-auto-test 轻提醒：写了生产代码却没有配套测试时，给一条一次性的提示。

触发：PostToolUse / Write|Edit。只在"写的不是测试文件、且同目录/测试目录下
找不到同名测试文件"时输出 additionalContext，其余情况完全静默。

这不是硬门，只是一次性提醒，不会阻止任何操作。
逃生：LHG_AT_HOOKS_OFF=1（或 /plugin disable lhg-auto-test）。
零第三方依赖，内部出错时 fail-open 静默退出。
"""

import json
import os
import sys

SRC_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rb", ".php"}
TEST_HINT_RES = ("test_", "_test", ".spec.", ".test.")


def main() -> int:
    if os.environ.get("LHG_AT_HOOKS_OFF") == "1":
        return 0
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "") or ""
    if not file_path:
        return 0

    base = os.path.basename(file_path)
    _, ext = os.path.splitext(base)
    # 测试文件本身、非源码文件：静默
    if ext not in SRC_EXTS:
        return 0
    if any(h in base for h in TEST_HINT_RES):
        return 0

    stem = os.path.splitext(base)[0]
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    # 在 tests/、test/、__tests__ 与同目录下找同名测试文件
    candidates = [
        os.path.join(project_dir, d, stem) for d in ("tests", "test", "__tests__")
    ] + [os.path.join(os.path.dirname(os.path.abspath(file_path)), stem)]
    found = False
    for cand_dir_stem in candidates:
        d = os.path.dirname(cand_dir_stem)
        if not os.path.isdir(d):
            continue
        try:
            names = os.listdir(d)
        except OSError:
            continue
        if any(stem in n and any(h in n for h in TEST_HINT_RES) for n in names):
            found = True
            break
    if found:
        return 0

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext":
                "lhg-auto-test 提醒：%s 写了/改了，但没找到它对应的测试文件。"
                "新功能建议跑 /lhg-auto-test:autotest 生成三类用例与可执行脚本。"
                "（不想被提醒：LHG_AT_HOOKS_OFF=1）" % base,
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
