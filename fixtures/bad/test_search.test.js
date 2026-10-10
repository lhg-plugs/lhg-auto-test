// 反面教材：页面测试常见坑（供 test_audit.py 演示检出）
it.only("search works", async () => {
  await page.goto("https://example.com");
  await page.waitForTimeout(3000);
  const res = await fetch("https://api.example.com/search?q=a");
  console.log(res.status);
});
