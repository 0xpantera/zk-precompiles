# pragma version ^0.4.0
"""
@title Matrix verifier for BN-254 scalar field.
@custom:contract-name ec_matmul
@license GNU Affero General Public License v3.0 only
@author 0xpantera
@notice Checks that    M * s  ==  o * G
        where
            - M is an nxn matrix of uint256 (scalars in F_r),
            - s is an nx1 vector of G1 points ([s_i]G),
            - o is an nx1 vector of scalars (F_r).

        All scalar arithmetic lives in the BN-254 scalar field (prime `r`),
        while point coordinates live in the base field (prime `p`).
"""

# --------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------

# BN-254 primes
# @dev Base Field modulus p
P: constant(uint256) = (
    21888242871839275222246405745257275088696311157297823662689037894645226208583
)
# @dev Scalar field modulus r
R: constant(uint256) = (
    21888242871839275222246405745257275088548364400416034343698204186575808495617
)

# G1 generator (1, 2) in affine coords
G_X: constant(uint256) = 1
G_Y: constant(uint256) = 2

# Precompile addresses
# @dev The `modexp` precompile address.
_MODEXP: constant(address) = 0x0000000000000000000000000000000000000005
# @dev alt_bn128 `ecAdd`
_EC_ADD:  constant(address) = 0x0000000000000000000000000000000000000006
# @dev alt_bn128 `ecMul`
_EC_MUL:  constant(address) = 0x0000000000000000000000000000000000000007

# Compile-time bound on dimension n (adjust as needed)
MAX_DIM: constant(uint256) = 6


# --------------------------------------------------------------------
# Data structures
# --------------------------------------------------------------------

struct ECPoint:
    x: uint256
    y: uint256


@deploy
@payable
def __init__():
    """
    @dev To omit the opcodes for checking the `msg.value`
         in the creation-time EVM bytecode, the constructor
         is declared as `payable`.
    """
    pass


# --------------------------------------------------------------------
# Precompile wrappers
# --------------------------------------------------------------------

@internal
@view
def _ec_add(ax: uint256, ay: uint256, bx: uint256, by: uint256) -> (uint256, uint256):
    """
    Call precompile 0x06: (ax,ay) + (bx,by) -> (cx,cy)
    """
    payload: Bytes[128] = concat(
        convert(ax, bytes32), convert(ay, bytes32),
        convert(bx, bytes32), convert(by, bytes32)
    )
    out: Bytes[64] = raw_call(_EC_ADD, payload, max_outsize=64, is_static_call=True)
    cx: uint256 = convert(slice(out, 0, 32), uint256)
    cy: uint256 = convert(slice(out, 32, 32), uint256)
    return cx, cy


@internal
@view
def _ec_mul(px: uint256, py: uint256, k: uint256) -> (uint256, uint256):
    """
    Call precompile 0x07: k * (px,py) -> (qx,qy)
    The precompile reduces k modulo r internally.
    """
    payload: Bytes[96] = concat(
        convert(px, bytes32), convert(py, bytes32), convert(k, bytes32)
    )
    out: Bytes[64] = raw_call(_EC_MUL, payload, max_outsize=64, is_static_call=True)
    qx: uint256 = convert(slice(out, 0, 32), uint256)
    qy: uint256 = convert(slice(out, 32, 32), uint256)
    return qx, qy


# --------------------------------------------------------------------
# Public verifier
# --------------------------------------------------------------------

@external
@view
def matmul(
    matrix: uint256[ MAX_DIM * MAX_DIM ],  # flattened row-major, unused slots = 0
    n: uint256,                            # actual dimension
    s: ECPoint[MAX_DIM],
    o: uint256[MAX_DIM]
) -> bool:
    """
    Return True iff   M * s  ==  o * G   element-wise (all mod r).

    Reverts if dimensions are inconsistent or n == 0.
    """

    # ---------------- Dimension checks ----------------
    assert 0 < n, "n out of range"
    assert n <= MAX_DIM, "n out of range"

    # n is already checked: 0 < n <= MAX_DIM
    xs: uint256 = n * n

    # ---------------- matrix entries ----------------
    # All scalars < r
    for i: uint256 in range(xs, bound=MAX_DIM * MAX_DIM):
        assert matrix[i] < R, "matrix entry >= r"
    # ---------------- vector entries --------------
    for i: uint256 in range(n, bound=MAX_DIM):
        assert o[i] < R, "o entry >= r"

    # ---------------- Main loop ----------------
    # row index
    for i: uint256 in range(n, bound=MAX_DIM):
        # Accumulator starts at point-at-infinity (0,0)
        acc_x: uint256 = 0
        acc_y: uint256 = 0

        # column index
        for j: uint256 in range(n, bound=MAX_DIM):
            k: uint256 = matrix[i * n + j]
            if k == 0:
                # skip cheap zero terms
                continue  

            # term = k * s_j
            t_x: uint256 = 0
            t_y: uint256 = 0
            (t_x, t_y) = self._ec_mul(s[j].x, s[j].y, k)

            # acc += term
            if acc_x == 0 and acc_y == 0:
                acc_x = t_x
                acc_y = t_y
            elif t_x != 0 or t_y != 0:
                (acc_x, acc_y) = self._ec_add(acc_x, acc_y, t_x, t_y)

        # RHS = o_i * G
        exp_x: uint256 = 0
        exp_y: uint256 = 0
        (exp_x, exp_y) = self._ec_mul(G_X, G_Y, o[i])

        if acc_x != exp_x or acc_y != exp_y:
            return False

    return True