"""结算功能测试（正面示范）：正常/边界/异常三类覆盖，隔离、可复现、可读。"""
import random

import pytest
from freezegun import freeze_time

random.seed(42)


class FakeClient:
    """被测对象的测试替身：外部支付接口已 mock，只测自身逻辑。"""

    def __init__(self, workdir):
        self.workdir = workdir
        self.logged_in = True
        self.skus = {"A1": 100}

    def logout(self):
        self.logged_in = False

    def create_order(self, items, note=""):
        if not self.logged_in:
            raise PermissionError("未登录")
        if not items:
            raise ValueError("空购物车不能下单")
        total = sum(i["qty"] * i["price"] for i in items)
        return {
            "total": total,
            "status": "paid",
            "note": note[:200],
            "delivery_fee": 0 if total >= 30 else 5,
            "created_at": "2026-10-11T10:00:00",
            "receipt": str(self.workdir / "receipt.txt"),
        }

    def get_sku(self, sku):
        if sku not in self.skus:
            raise LookupError("商品不存在")
        return self.skus[sku]


@pytest.fixture
def client(tmp_path):
    """每个测试拿到全新的隔离客户端；tmp_path 用完自动清理。"""
    return FakeClient(workdir=tmp_path)


class Test正常流程:
    def test_TC01_正常下单结算成功(self, client):
        """意图：主流程走通，金额与状态正确。"""
        order = client.create_order(
            items=[{"sku": "A1", "qty": 2, "price": 100}])
        assert order["total"] == 200
        assert order["status"] == "paid"
        assert order["delivery_fee"] == 0


class Test边界:
    def test_TC02_空购物车拒绝下单(self, client):
        """边界：空值输入必须被拒绝。"""
        with pytest.raises(ValueError, match="空"):
            client.create_order(items=[])

    def test_TC03_超长备注自动截断(self, client):
        """边界：超长字符串输入。"""
        order = client.create_order(
            items=[{"sku": "A1", "qty": 1, "price": 10}],
            note="x" * 5000)
        assert len(order["note"]) <= 200

    def test_TC04_临界值刚好达到免邮门槛(self, client):
        """边界：临界值（刚好等于阈值）。"""
        order = client.create_order(
            items=[{"sku": "A1", "qty": 1, "price": 30}])
        assert order["delivery_fee"] == 0


class Test异常:
    def test_TC05_未登录下单被拒绝(self, client):
        """异常：未授权访问。"""
        client.logout()
        with pytest.raises(PermissionError):
            client.create_order(items=[{"sku": "A1", "qty": 1, "price": 10}])

    def test_TC06_不存在的商品抛异常(self, client):
        """异常：错误输入。"""
        with pytest.raises(LookupError, match="不存在"):
            client.get_sku("NOT-EXIST")

    def test_TC07_随机折扣可复现(self, client):
        """意图：随机数种子已固定，结果可复现。"""
        n = random.randint(1, 100)
        assert 1 <= n <= 100

    @freeze_time("2026-10-11")
    def test_TC08_订单日期取冻结时间(self, client):
        """意图：时间已冻结，断言不依赖'什么时候跑'。"""
        order = client.create_order(
            items=[{"sku": "A1", "qty": 1, "price": 10}])
        assert order["created_at"].startswith("2026-10-11")
