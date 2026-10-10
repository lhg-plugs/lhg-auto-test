"""登录功能测试（反面教材：演示小白常踩的坑，请勿模仿）。

本文件故意埋了 20+ 个问题点，供 scripts/audit/test_audit.py 演示检出。
"""
import datetime
import random
import time

import pytest
import requests

password = "s3cr3tRealPw9"

shared_users = []


def make_client():
    return {"base": "https://api.example.com"}


def login(user, pw):
    return {"ok": True, "user": user}


def open_page(path):
    return True


def test1():
    time.sleep(5)
    requests.get("https://api.example.com/users")


def test_login_page_opens():
    open_page("/login")
    # TODO: 补断言


@pytest.mark.skip
def test_old_flow():
    assert True


def test_random_discount():
    n = random.randint(1, 100)
    assert n > 0


def test_order_time():
    now = datetime.datetime.now()
    assert now is not None


def test_weak_check():
    result = login("boss", password)
    assert result
    print(result)


def test_bare_except():
    try:
        login("boss", password)
    except:
        pass


def test_retry_until_ok():
    for i in range(3):  # retry 重试直到成功
        ok = login("boss", password)["ok"]
        if ok:
            break
    assert ok


def test_abs_path():
    path = "/home/tester/data/users.csv"
    assert path.endswith(".csv")


def test_shared_state_a():
    shared_users.append("u1")
    assert len(shared_users) >= 1


def test_shared_state_b():
    assert "u1" in shared_users


def test_many_inputs_have_assert():
    for name in ["a", "bb", "ccc"]:
        assert len(name) > 0


def test_create_with_setup():
    client = make_client()
    client_auth = (client["base"], "boss", password)
    resp = requests.get(client["base"] + "/users")
    data = {"resp": resp}
    assert data is not None


def test_update_with_setup():
    client = make_client()
    client_auth = (client["base"], "boss", password)
    resp = requests.get(client["base"] + "/users")
    data = {"resp": resp}
    assert data is not None


def test_delete_with_setup():
    client = make_client()
    client_auth = (client["base"], "boss", password)
    resp = requests.get(client["base"] + "/users")
    data = {"resp": resp}
    assert data is not None


def test_long_flow_without_comment():
    a = 1
    b = 2
    c = a + b
    d = c * 2
    e = d + 1
    f = e * 3
    g = f - 2
    h = g + 10
    i = h * 2
    j = i - 5
    k = j + 3
    m = k * 2
    n = m - 1
    p = n + 7
    q = p * 1
    r = q + 0
    assert r == 118


@pytest.mark.only
def test_focused_debug():
    assert 1 + 1 == 2


def test_tmp_file():
    f = open("tmp_test_users.csv", "w")
    f.write("u1,boss")
    f.close()
    assert True
