from script.deploy_rational_adder import deploy_rational_adder
import pytest
from hypothesis import assume, given, strategies as st

# BN-254 scalar-field prime (same constant the Vyper contract uses)
P = 21888242871839275222246405745257275088548364400416034343698204186575808495617


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def rational_adder():
    """
    Deploy the compiled Vyper contract once for the entire module.
    """
    return deploy_rational_adder()


# ---------------------------------------------------------------------------
# Helper functions (pure Python field arithmetic)
# ---------------------------------------------------------------------------

def inv_mod_p(u: int) -> int:
    """Modular inverse in F_p via Fermat’s little theorem."""
    # u^(p-2) mod p   (works because p is prime and u ≠ 0)
    return pow(u, P - 2, P)


def random_valid_triplet():
    """
    A deterministic generator for concrete values that satisfy the relation.
    """
    x1, y1 = 3, 4
    x2, y2 = 5, 7
    den    = 11
    s  = (x1 * inv_mod_p(y1) + x2 * inv_mod_p(y2)) % P
    num = (s * den) % P
    return (x1, y1), (x2, y2), num, den


# ---------------------------------------------------------------------------
# 1) Simple deterministic sanity test
# ---------------------------------------------------------------------------

def test_manual_example(rational_adder):
    (x1, y1), (x2, y2), num, den = random_valid_triplet()

    ok = rational_adder.rationalAdd((x1, y1), (x2, y2), num, den)
    assert ok is True


# ---------------------------------------------------------------------------
# 2) Hypothesis fuzzing: valid witnesses must verify
# ---------------------------------------------------------------------------

# Strategies that pick uniform random elements in the field, except 0 for denominators
field_elem = st.integers(min_value=0, max_value=P - 1)
non_zero   = st.integers(min_value=1, max_value=P - 1)

@given(
    x1=field_elem, y1=non_zero,
    x2=field_elem, y2=non_zero,
    den=non_zero,
)
def test_rational_add_holds(rational_adder, x1, y1, x2, y2, den):
    """
    Generates a valid witness and checks the contract returns `True`.
    """
    s   = (x1 * inv_mod_p(y1) + x2 * inv_mod_p(y2)) % P
    num = (s * den) % P

    assert rational_adder.rationalAdd(
        (x1, y1), (x2, y2), num, den
    ) is True


# ---------------------------------------------------------------------------
# 3) Hypothesis fuzzing: small perturbation should fail
# ---------------------------------------------------------------------------

@given(
    x1=field_elem, y1=non_zero,
    x2=field_elem, y2=non_zero,
    den=non_zero,
)
def test_rational_add_fails_on_wrong_num(rational_adder, x1, y1, x2, y2, den):
    """
    Use a correct witness, then flip `num` by ±1 (mod P); the proof must fail.
    """
    s   = (x1 * inv_mod_p(y1) + x2 * inv_mod_p(y2)) % P
    num = (s * den) % P

    # mutate num but keep it in field range
    num_bad = (num + 1) % P

    assume(num_bad != num)           # guard against rare wrap-around
    assert rational_adder.rationalAdd(
        (x1, y1), (x2, y2), num_bad, den
    ) is False


# ---------------------------------------------------------------------------
# 4) Revert tests: zero denominators
# ---------------------------------------------------------------------------

def test_reverts_on_zero_denominator(rational_adder):
    x1, x2 = 1, 2
    y1, y2 = 1, 1
    num, den = 3, 0  # <- will trigger the `assert … "division by zero"`

    with pytest.raises(Exception):
        rational_adder.rationalAdd((x1, y1), (x2, y2), num, den)