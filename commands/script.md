---
description: 把确认过的用例表转成可执行脚本：API 用 curl/pytest 风格，页面用 Playwright 思路，单元用 pytest。输出人类可读、一条用例对应一个测试函数。
argument-hint: [用例表或功能描述] [--api|--ui|--unit]
---

# /lhg-auto-test:script —— 用例转可执行脚本

用户输入在 `$ARGUMENTS` 中：已确认的用例表（优先）或功能描述 + 类型开关。

## 流程（加载 lhg-at-script 全程指导）

### 1. 确认输入
- 如果给的是用例表 → 直接用，不许自己加戏新增用例。
- 如果给的是功能描述 → 先按 `/lhg-auto-test:cases` 产出用例表并经用户确认，再继续。
- 确认目标类型：`--api` / `--ui` / `--unit`，缺省按被测对象自动判断。

### 2. 生成脚本
按 lhg-at-script 的选型与写法规范：

- **API**：首选 `curl` 可读脚本（每条请求后紧跟"期望状态码/字段"的断言注释）；需要断言逻辑时用 pytest 风格（标准库 `urllib`+`json`，零第三方依赖）。
- **页面**：Playwright 思路脚本（`page.get_by_role` / `get_by_text` 优先定位，避开脆弱 CSS 选择器）；文件头注明"本机首次运行需 `npx playwright install chromium`"。
- **单元**：pytest 风格，一个用例一个测试函数，函数名 = 用例编号+用例名（如 `test_TC03_空用户名拒绝登录`），共享数据走 fixture，测试后清理。

### 3. 自检（加载 lhg-at-quality）
跑审计脚本：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/test_audit.py --target <脚本所在目录> --format text
```
blocker 清零（硬编码等待、无断言、硬编码密钥）再交付。

## 硬规则
- 一条用例一个测试函数，不许把 5 条用例塞进一个函数里"顺手测了"。
- 测试里不许出现 `time.sleep(固定秒数)` / `waitForTimeout`；等待必须等"看得见的结果"（元素出现、状态码返回）。
- 没实际跑过的脚本，交付时明确标注"未执行"，不许写"测试通过"。
