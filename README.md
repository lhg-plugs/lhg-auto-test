<!-- About 简介（推送后填写到仓库 About 栏）：
自动测试专家：一句话功能描述 → 正常/边界/异常三类测试用例 → 可直接跑的测试脚本（pytest / curl / Playwright 思路）→ 覆盖率 checklist 报告。 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-auto-test
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, testing, qa, test-cases, pytest, playwright -->

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="lhg-auto-test — 自动测试专家">
</p>

> **一句话介绍**：自动测试专家：一句话功能描述 → 正常/边界/异常三类测试用例 → 可直接跑的测试脚本（pytest / curl / Playwright 思路）→ 覆盖率 checklist 报告。

**一键安装**：在 Claude Code 里运行

```bash
/plugin marketplace add lhg-plugs/lhg-auto-test
/plugin install lhg-auto-test@lhg-plugs
```

## 它能帮你做出什么

每条产出先过确定性脚本自查，再交人工复核清单——数字全部数自仓库里的审计脚本，不靠模型"自觉"。

| 自查脚本 | 规则数 | blocker | warning | nit | 覆盖 |
|---|---|---|---|---|---|
| `scripts/audit/test_audit.py` | 24 | 4 | 14 | 6 | 断言、稳定性、安全、纪律、覆盖、隔离、可移植、可读 |
| **合计** | **24** | **4** | **14** | **6** | |

- **零 LLM 成本**：规则是纯 Python 脚本，零第三方依赖，本地运行。
- **坏 / 好对照可验**：`fixtures/` 里备有坏/好用例，冒烟测试断言命中情况。
- **冒烟全绿**：`python3 smoke_test.py` 41 项全部通过（JSON 合法、frontmatter 完整、命令/skill/agent 齐全）。

## 它是什么

`lhg-auto-test` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **4 个命令**（小白入口）：`audit` 测试代码体检、`autotest` 一句话功能描述 → 三类测试用例（正常/、`cases` 只做测试用例设计、`script` 把确认过的用例表转成可执行脚本
- **3 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：lhg-at-cases, lhg-at-quality, lhg-at-script
- **2 个专家 agent**：test-designer, test-reviewer
- **2 个 hooks**（`hooks/`：post_write_test_hint.py, pre_commit_test_gate.py），关键操作前自动把关
- **24 条确定性自查规则**：纯 Python 脚本，见上表

## 为什么是它

不是一个 prompt，而是一套互相兜底的机制：

1. **确定性脚本（机器）+ 人工复核清单（人）**：先跑 `scripts/` 下的审计脚本（共 24 条规则），发现分三级：**blocker**（必须修）、**warning**（修或写豁免理由）、**nit**（顺手修）；再按对应 skill 的复核清单过一遍脚本抓不到的（内容真实性、越权、口径一致）。blocker 清零才算做完；为清零改规则算作弊，不许。
2. **硬门，不是提醒**：hooks 在关键操作前自动拦截或警告（见 `hooks/`），而不是只在文档里写一句"请注意"。
3. **方法论沉淀在 skill 里**：流程、检查清单、口径都写在 `skills/` 的方法论里，命令只是入口；换个 agent 平台也能复用同一套做法。
4. **可验，不是可信**：`fixtures/` 备有坏/好对照用例，`smoke_test.py` 一键验证，规则有没有生效、自己跑一遍就知道。

## 快速上手

```bash
# 1. 安装（Claude Code 里运行）
/plugin marketplace add lhg-plugs/lhg-auto-test
/plugin install lhg-auto-test@lhg-plugs

# 2. 一句话功能描述 → 三类测试用例（正常/边界/异常） → 可执行测试脚本 → 覆
/lhg-auto-test:autotest "用户登录接口"
```

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-auto-test:audit` | 测试代码体检：跑确定性审计脚本（断言缺失/硬编码等待/三类覆盖/数据清理等），输出分级报告并修复 blocker。 | `/lhg-auto-test:audit tests/` |
| `/lhg-auto-test:autotest` | 一句话功能描述 → 三类测试用例（正常/边界/异常） → 可执行测试脚本 → 覆盖率 checklist 报告… | `/lhg-auto-test:autotest "用户登录接口"` |
| `/lhg-auto-test:cases` | 只做测试用例设计：把一句话功能拆成正常/边界/异常三类用例表，用户确认后再走脚本生成。适合"先审计划再写代码"。 | `/lhg-auto-test:cases "优惠券领取"` |
| `/lhg-auto-test:script` | 把确认过的用例表转成可执行脚本：API 用 curl/pytest 风格，页面用 Playwright 思路… | `/lhg-auto-test:script --api` |

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你需要测试代码体检时 → 用 `/lhg-auto-test:audit`
- 你需要一句话功能描述 → 三类测试用例（正常/边界/异时 → 用 `/lhg-auto-test:autotest`
- 你需要只做测试用例设计时 → 用 `/lhg-auto-test:cases`

**什么时候不用：**

- 你只需要其中一个零散能力时 → 本插件是成套流程，单点需求用更轻量的 skill 更合适
- 你希望 AI 完全自由发挥、不接受任何自查与硬门时 → 它的规则审计与 hooks 会介入（可关，但那就别装它）
- 你的场景不在上面命令表覆盖范围内时 → 先看命令表，没有对应命令就别硬套

## 目录结构

```
lhg-auto-test/
├── smoke_test.py          # 一键冒烟测试
├── ATTRIBUTION.md         # 灵感来源与许可声明
├── LICENSE                # MIT
├── README.md              # 本文件
├── .claude-plugin/
├── agents/
├── commands/
├── fixtures/
├── hooks/
├── scripts/
├── skills/
```

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（本次实测 41 项全部通过）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-auto-test/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

同门插件见 [lhg-plugs](https://github.com/lhg-plugs)，86 个插件的完整矩阵在 [marketplace](https://github.com/lhg-plugs/marketplace) 维护。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 抖音：搜「刘老师讲AI实战」
- 微信：lhgsmsw
