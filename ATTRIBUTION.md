# 灵感来源与致谢（Attribution）

本插件的**方法论灵感**来自以下优秀的开源项目，**所有实现代码、检测规则与文案均为原创**，未复制任何第三方的原文案。

| 项目 | 作者 / 组织 | 许可 | 链接 | 借鉴了什么思路 |
|---|---|---|---|---|
| superpowers | Jesse Vincent（obra） | MIT | https://github.com/obra/superpowers | TDD 流程纪律："先写测试再写代码"的节奏思想；本插件与其互补——superpowers 管流程纪律，本插件管用例内容与脚本生成 |
| skills（官方技能库） | Anthropic | Apache-2.0 | https://github.com/anthropics/skills | `webapp-testing` 的"测试先行"思想；本插件定位是它的轻量入门版——只做"让小白第一次写出能跑的测试" |
| dvstack（playwright-agents） | vardanyandavit | MIT | https://github.com/vardanyandavit/dvstack | planner→generator→healer 三角色分层；"先审计划再写代码"（review the plan before the code）；本插件的 cases→script→audit 流程与 test-designer/test-reviewer 分工受其启发 |
| playwright-skills | Faisal Noman | MIT | https://github.com/faisalnoman/playwright-skills | 访谈式生成测试套件的思路；Playwright 定位优先级（语义化定位优于脆弱 CSS）的实践 |
| artifact-testing | Muse 内置 skill | 内置 | /opt/hatch/skills/artifacts/testing/SKILL.md | "交付前必须过校验门、带着 TODO 不许交付"的问题意识；本插件质量门的"没跑过不许写通过"诚实红线受其启发 |

## 声明

1. **借鉴思路，实现与文案均为原创**：以上项目的具体文案、规则原文、代码实现均未被复制。本插件的 skill 方法论文案、审计规则、命令流程均为独立撰写。
2. **许可合规**：上述项目均为 MIT / Apache-2.0 许可（或内置 skill），允许在保留声明的前提下进行思路借鉴与二次创作。本文件即为保留声明的一部分。
3. **商标与归属**：各项目名称与作者署名归其各自所有者所有。

## 本插件自身的许可

本插件原创部分采用 MIT 许可（见 `LICENSE` 文件），版权所有：刘洪光（https://github.com/lhg-skills）。
