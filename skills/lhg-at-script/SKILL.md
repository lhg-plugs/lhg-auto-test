---
name: lhg-at-script
description: 测试脚本生成规范：用例表转可执行脚本的选型与写法。API 用 curl/pytest 风格，页面用 Playwright 思路，一条用例一个测试函数，人类可读。
license: MIT
compatibility: 适用于任何支持 Markdown 指令的 AI 编程助手（Claude Code、豆包、Workbuddy 等）
metadata:
  version: 1.0.0
  author: 刘洪光
---

# lhg-at-script：用例转可执行脚本

> 目标：把确认过的用例表，变成"小白能看懂、机器能跑"的测试脚本。
> 核心纪律：**一条用例一个测试函数；不许硬编码等待；没跑过的脚本不许写"通过"。**

## 1. 何时使用

- 用例表已确认，要生成可执行脚本 → 用本 skill
- 已有脚本，想按规范重写得更可读 → 看第 3~5 节
- 纠结"这个功能用什么测" → 看第 2 节选型表

## 2. 选型：三种脚本形态

| 被测对象 | 首选形态 | 什么时候换 |
|---|---|---|
| HTTP API | `curl` 可读脚本（每条带断言注释） | 需要复杂断言逻辑时换 pytest 风格（标准库 `urllib`+`json`，零第三方依赖） |
| 页面交互 | Playwright 思路脚本（`.spec.ts` 结构） | 纯静态页面可降级为"检查清单式"脚本 |
| 纯函数/逻辑 | pytest 风格（`test_*.py`） | JS 项目用同等结构的测试文件 |

选型原则：**先让小白跑起来**。curl 脚本复制粘贴就能跑，pytest 需要 Python 环境，Playwright 需要本机装浏览器——按用户的环境选，不许为了"高级"选用户跑不起来的。

## 3. 通用写法规范（三种形态都遵守）

### 3.1 一条用例一个测试函数

```python
def test_TC03_空用户名拒绝登录():
    resp = post("/api/login", {"username": "", "password": "x"})
    assert resp.status_code == 400
    assert "用户名" in resp.json()["message"]
```

不许把 5 条用例塞进一个函数"顺手测了"：失败时你不知道挂的是哪条。

### 3.2 函数名就是用例名

`test_TC03_空用户名拒绝登录` —— 测试报告里一眼看出挂的是哪条用例。
禁止 `test1`、`test_foo` 这类名字。

### 3.3 断言说人话、具体到值

- ✅ `assert resp.status_code == 401`
- ✅ `assert order["total"] == 200`
- ❌ `assert result` —— 测了个寂寞
- ❌ `assert True` —— 永远通过的测试等于没测

### 3.4 等待必须等"看得见的结果"

```python
# ❌ 硬编码等待：机器慢一点就失败
time.sleep(5)

# ✅ 等结果出现（伪代码，按实际框架写）
wait_until(lambda: page.get_by_text("支付成功").is_visible(), timeout=10)
```

页面测试同理：不许 `waitForTimeout`，等元素出现、等网络响应、等 URL 变化。

### 3.5 测试数据：建完就清

```python
@pytest.fixture
def user(tmp_path):
    u = create_test_user()      # 建
    yield u
    delete_test_user(u.id)      # 清
```

用框架的 fixture/teardown 机制，不许靠"我记得删"。

## 4. API 脚本：curl 风格模板

```bash
# TC-01 正确密码登录成功（正常）
curl -s -w "\nHTTP:%{http_code}\n" -X POST https://api.example.com/login \
  -H "Content-Type: application/json" \
  -d '{"username":"boss","password":"correct-pw"}'
# 断言：HTTP:200，且响应体包含 "token"

# TC-05 未登录下单被拒绝（异常）
curl -s -w "\nHTTP:%{http_code}\n" -X POST https://api.example.com/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"A1","qty":1}'
# 断言：HTTP:401
```

每条请求后紧跟断言注释：期望状态码 + 关键字段。小白照着跑，眼睛看注释就知道过没过。

## 5. 页面脚本：Playwright 思路模板

```typescript
// 首次运行前：npx playwright install chromium
import { test, expect } from '@playwright/test';

test('TC-01 正确密码登录成功', async ({ page }) => {
  await page.goto('https://example.com/login');
  // 定位优先用"看得见的字"，不用脆弱的 CSS
  await page.getByLabel('用户名').fill('boss');
  await page.getByLabel('密码').fill('correct-pw');
  await page.getByRole('button', { name: '登录' }).click();
  // 断言看得见的结果
  await expect(page.getByText('欢迎回来')).toBeVisible();
});
```

定位优先级：`getByRole` / `getByLabel` / `getByText` > `test-id` > CSS 选择器。
CSS 选择器（尤其 `.css-1a2b3c` 这类哈希类名）一改版就全挂。

## 6. 反模式

1. **睡眠式测试**：`time.sleep(5)` / `waitForTimeout` —— flaky 之源，见一次改一次。
2. **断言缺失**：没有断言的测试永远通过，等于没测。
3. **测试里调生产接口**：单元测试打真实 API，对方挂了你的测试就红。用替身（mock）隔离。
4. **硬编码密钥**：测试代码也会进仓库，密码/token 走环境变量或明确标注的假数据。
5. **虚假"通过"**：脚本没实际跑过，报告里写"未执行"，不许写"测试通过"。诚实比好看重要。
6. **随机不固定**：用了随机数就固定种子，否则失败了复现不了。

## 7. 交付前自检（配合审计脚本）

生成完脚本，跑插件自带的审计：

```
python3 <插件目录>/scripts/audit/test_audit.py --target <脚本所在目录>
```

blocker（无断言、硬编码等待、硬编码密钥、focused 测试）必须清零再交付。
warning 逐条处理：修掉，或写豁免理由。

## 8. 自检与反馈

每次执行完本 skill，做一次轻量自检：

1. 是否一条用例一个测试函数？→ 有没有"顺手测了"的大杂烩函数？
2. 有没有硬编码等待 / 无断言测试？→ 跑一遍审计脚本确认。
3. 没跑过的脚本有没有标注"未执行"？→ 诚实检查。

标准冒烟用例：对插件自带的 `fixtures/good` 跑审计脚本，确认零 blocker（见仓库根 `smoke_test.py`）。

反馈渠道：以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-auto-test/issues，正文写清"输入 → 错误输出 → 期望输出"。

## 出品：刘洪光

本 skill 由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw
