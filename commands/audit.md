---
description: 测试代码体检：跑确定性审计脚本（断言缺失/硬编码等待/三类覆盖/数据清理等），输出分级报告并修复 blocker。
argument-hint: [测试目录] [--fix]
---

# /lhg-auto-test:audit —— 测试代码体检

用户输入在 `$ARGUMENTS` 中：`[测试目录] [--fix]`。目录缺省为当前项目的测试目录（`tests/` / `test/` / `__tests__`，按存在选用）。

## 流程（加载 lhg-at-quality 全程指导）

### 1. 跑脚本
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/test_audit.py --target <测试目录> --format text
```
记下 blocker / warning / nit 的数量与明细（含文件、行号、规则说明）。

### 2. 分级与修复
- blocker：逐条修。`--fix` 缺省即自动修（最小改动原则）；修一条用脚本复查一条。
- 修不掉的（如需用户提供真实测试账号/环境）→ 列入"需人工处理"，不许为清零改规则。
- warning：修掉或写豁免理由（+有效期）；nit：顺手修。

### 3. 三类覆盖复核
按 lhg-at-cases 的覆盖检查：整个测试目录是否三类齐全（正常/边界/异常）？
缺类 → 明确指出缺哪类、建议补哪几条用例（只给用例建议，不直接写代码，除非用户要求）。

### 4. 输出报告
按 lhg-at-quality 的报告模板输出，存为 `docs/test-audit-YYYYMMDD.md`，结论写清"通过 / 不通过"。

## 硬规则
- 有 blocker 就说"通过" → 不许。
- 为清零改脚本规则或阈值 → 这是作弊，不许。
- 审计结论不许编造执行结果：没跑过的测试，状态写"未执行"。
