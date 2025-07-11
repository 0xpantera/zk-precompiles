from script.deploy_ec_matmul import deploy_ec_matmul
import pytest
from hypothesis import given, strategies as st, settings

# ---- py_ecc gives us BN-254 arithmetic off-chain ---------------------------
from py_ecc.bn128.bn128_curve import multiply
from py_ecc.bn128.bn128_curve import G1, curve_order as R
from py_ecc.bn128.bn128_curve import field_modulus as P

# @dev must match the constant inside the Vyper contract
MAX_DIM = 6

# ----------------------------------------------------------------------------
# Contract fixture
# ----------------------------------------------------------------------------
@pytest.fixture(scope="module")
def ec_matmul():
    """Deploy the Vyper matrix-verifier contract once for the entire module."""
    return deploy_ec_matmul()

# ----------------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------------
def to_affine(pt):
    """Convert a py_ecc (FQ,FQ) point to integer tuple modulo the base field."""
    # py_ecc uses None for the point at infinity
    if pt is None:                
        return (0, 0)
    x, y = pt
    return (int(x.n) % P, int(y.n) % P)

def g_mul(k):
    """kG in affine ints.  k==0 -> (0,0) (same convention as the precompile)."""
    k %= R
    return (0, 0) if k == 0 else to_affine(multiply(G1, k))

def mat_vec(mat, scalars, n):
    """(n x n) matrix x (n)-vector over F_r -> list length n."""
    out = []
    for i in range(n):
        acc = 0
        base = i * n
        for j in range(n):
            acc = (acc + mat[base + j] * scalars[j]) % R
        out.append(acc)
    return out

def pad_points(vec):
    """Pad list of (x,y) tuples up to MAX_DIM with (0,0)."""
    return vec + [(0, 0)] * (MAX_DIM - len(vec))

def pad_scalars(vec):
    """Pad list of uint256 scalars up to MAX_DIM with 0."""
    return vec + [0] * (MAX_DIM - len(vec))

def pad_matrix(flat):
    """Pad to MAX_DIM**2 with zeros for the contract's static array."""
    return flat + [0] * (MAX_DIM * MAX_DIM - len(flat))

def pad_vector(vec):
    """Pad to MAX_DIM with zeros."""
    return vec + [0] * (MAX_DIM - len(vec))

# ----------------------------------------------------------------------------
# Hypothesis composite generator
# ----------------------------------------------------------------------------
@st.composite
def instance(draw):
    n        = draw(st.integers(min_value=1, max_value=MAX_DIM))
    scalar   = st.integers(min_value=0, max_value=R - 1)
    matrix   = [draw(scalar) for _ in range(n * n)]
    # the hidden s_i scalars
    secrets  = [draw(scalar) for _ in range(n)]
    return n, matrix, secrets

# ----------------------------------------------------------------------------
# 1) Deterministic sanity test (n = 2)
# ----------------------------------------------------------------------------
def test_manual_example(ec_matmul):
    n = 2
    # 2×2
    matrix = [1, 2,
              3, 4]
    secrets = [5, 7]

    calldata_matrix = pad_matrix(matrix)
    calldata_s      = pad_points([g_mul(k) for k in secrets])
    o_vec           = pad_scalars(mat_vec(matrix, secrets, n))

    assert ec_matmul.matmul(calldata_matrix, n, calldata_s, o_vec) is True

# ----------------------------------------------------------------------------
# 2) Hypothesis: valid instances must verify
# ----------------------------------------------------------------------------
@given(inst=instance())
@settings(max_examples=25)
def test_matmul_holds(ec_matmul, inst):
    n, matrix, secrets = inst

    calldata_matrix = pad_matrix(matrix)
    calldata_s      = pad_points([g_mul(k) for k in secrets])
    o_vec           = pad_scalars(mat_vec(matrix, secrets, n))

    assert ec_matmul.matmul(calldata_matrix, n, calldata_s, o_vec) is True

# ----------------------------------------------------------------------------
# 3) Hypothesis: flip one o_i -> verification must fail
# ----------------------------------------------------------------------------
@given(inst=instance())
@settings(max_examples=25)
def test_matmul_fails_on_wrong_output(ec_matmul, inst):
    n, matrix, secrets = inst

    calldata_matrix = pad_matrix(matrix)
    calldata_s      = pad_points([g_mul(k) for k in secrets])
    o_vec           = mat_vec(matrix, secrets, n)

    # Corrupt the first entry
    o_vec[0] = (o_vec[0] + 1) % R
    o_vec_pad = pad_scalars(o_vec)

    assert ec_matmul.matmul(calldata_matrix, n, calldata_s, o_vec_pad) is False

# ----------------------------------------------------------------------------
# 4) Revert tests: illegal n (0 and > MAX_DIM)
# ----------------------------------------------------------------------------
def test_revert_on_bad_n(ec_matmul):
    dummy_matrix = pad_matrix([])
    dummy_vec    = pad_vector([])

    with pytest.raises(Exception):
        # n == 0
        ec_matmul.matmul(dummy_matrix, 0, dummy_vec, dummy_vec)

    with pytest.raises(Exception):
        # n too large
        ec_matmul.matmul(dummy_matrix, MAX_DIM + 1, dummy_vec, dummy_vec)