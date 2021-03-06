import pytest
from pygears.typing import Fixp, Ufixp, trunc, Uint, Int


def test_ufixp():
    q2_2 = Ufixp[2, 4]
    q3_1 = Ufixp[3, 4]
    q1_3 = Ufixp[1, 4]
    sq2_1 = Fixp[2, 3]

    assert trunc(q2_2, q3_1) == q3_1

    assert trunc(q2_2, q1_3) == q1_3

    with pytest.raises(TypeError):
        assert trunc(q2_2, sq2_1)


def test_val_ufixp():
    val = Ufixp[2, 4](2.25)

    q2_1 = Ufixp[2, 3]
    q1_2 = Ufixp[1, 3]
    q1_1 = Ufixp[1, 2]
    q3_1 = Ufixp[3, 4]
    q1_3 = Ufixp[1, 4]

    assert trunc(val, q3_1) == 2.0
    assert trunc(val, q1_3) == 0.25
    assert trunc(val, q2_1) == 2.0
    assert trunc(val, q1_2) == 0.25
    assert trunc(val, q1_1) == 0.0


def test_fixp():
    q2_2 = Fixp[3, 5]
    q3_1 = Fixp[4, 5]
    q1_3 = Fixp[2, 5]
    uq2_1 = Ufixp[2, 3]

    assert trunc(q2_2, q3_1) == q3_1

    assert trunc(q2_2, q1_3) == q1_3

    with pytest.raises(TypeError):
        assert trunc(q2_2, uq2_1)


def test_val_fixp():
    val = Fixp[3, 5](-2.75)

    q2_1 = Fixp[3, 4]
    q1_2 = Fixp[2, 4]
    q1_1 = Fixp[2, 3]
    q5_1 = Fixp[6, 7]
    q1_5 = Fixp[2, 7]

    assert trunc(val, q2_1) == -3.0
    assert trunc(val, q1_2) == -0.75
    assert trunc(val, q1_1) == -1.0
    assert trunc(val, q5_1) == -3.0
    assert trunc(val, q1_5) == -0.75


def test_uint():
    u8 = Uint[8]
    u7 = Uint[7]

    i7 = Int[7]

    assert trunc(u8, u7) == u7

    with pytest.raises(TypeError):
        assert trunc(u8, i7)


def test_val_uint():
    val = Uint[8](0xaa)

    u9 = Uint[9]
    u7 = Uint[7]

    assert trunc(val, u7) == 0x2a
    assert trunc(val, u9) == 0xaa


def test_int():
    i8 = Int[8]
    i7 = Int[7]

    u7 = Uint[7]

    assert trunc(i8, i7) == i7

    with pytest.raises(TypeError):
        assert trunc(i8, u7)


def test_val_int():
    val = Int[8](-0x56)
    i7 = Int[7]
    i15 = Int[15]

    assert trunc(val, i7) == Int[7](-0x16)
    assert trunc(val, i15) == -0x56
