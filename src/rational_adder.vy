# pragma version ^0.4.0
"""
@title Verify that  x1/y1 + x2/y2 == num/den inside the BN-254 scalar field.
@custom:contract-name rational_adder
@license GNU Affero General Public License v3.0 only
@author 0xpantera
"""

# @dev The `modexp` precompile address.
_MODEXP: constant(address) = 0x0000000000000000000000000000000000000005
# @dev The byte size length of `B` (base), `E` (exponent), and `M`
# (modulus) in the `modexp` precompile.
C: constant(uint256) = 32

# @notice All of the constant values defined subsequently are
# parameters for the elliptical curve BN254


# @dev Field modulus p (same as curve-order of the scalar field).
P: constant(uint256) = (
    21888242871839275222246405745257275088548364400416034343698204186575808495617
)

# @dev The "-2 mod _P" constant is used to speed up inversion
# and doubling (avoid negation).
MINUS_2MODP: constant(uint256) = (
    21888242871839275222246405745257275088548364400416034343698204186575808495615
)

struct ECPoint:
    x: uint256  # numerator
    y: uint256  # denominator (must be non-zero mod P)

@deploy
@payable
def __init__():
    """
    @dev To omit the opcodes for checking the `msg.value`
         in the creation-time EVM bytecode, the constructor
         is declared as `payable`.
    """
    pass


@external
@view
def rationalAdd(
    A: ECPoint,
    B: ECPoint,
    num: uint256,
    den: uint256
) -> bool:
    """
    Return `True` iff A.x/A.y + B.x/B.y == num/den (all in F_p).
    """

    # Non-zero denominators are required for the inverse to exist.
    assert A.y != 0 and B.y != 0 and den != 0, "division by zero"

    # Inverses via Fermat’s little theorem:  a^(p-2) ≡ a⁻¹  (mod p)
    inv_y1: uint256  = self._p_mod_inv(A.y)
    inv_y2: uint256  = self._p_mod_inv(B.y)
    inv_den: uint256 = self._p_mod_inv(den)

    # r1 = x1 / y1 ,  r2 = x2 / y2 ,  target = num / den
    r1: uint256     = uint256_mulmod(A.x, inv_y1, P)
    r2: uint256     = uint256_mulmod(B.x, inv_y2, P)
    target: uint256 = uint256_mulmod(num, inv_den, P)

    # Verify the sum inside the field.
    return uint256_addmod(r1, r2, P) == target


@internal
@view
def _p_mod_inv(u: uint256) -> uint256:
    """
    @dev Computes "u"**(-1) mod _P".
    @param u The 32-byte base for the `modexp` precompile.
    @return uint256 The 32-byte calculation result.
    """
    return self._mod_inv(u, MINUS_2MODP, P)

@internal
@view
def _mod_inv(u: uint256, minus_2modf: uint256, f: uint256) -> uint256:
    """
    @dev Computes "u**(-1) mod f = u**(phi(f) - 1) mod f = u**(f-2) mod f"
         for prime f by Fermat's little theorem, compute "u**(f-2) mod f"
         using the `modexp` precompile. Assumes "f != 0". If `u` is `0`,
         then "u**(-1) mod f" is undefined mathematically, but this function
         returns `0`.
    @param u The 32-byte base for the `modexp` precompile.
    @param minus_2modf The 32-byte exponent for the `modexp` precompile.
    @param f The 32-byte modulus for the `modexp` precompile.
    @return uint256 The 32-byte calculation result.
    """
    return_data: Bytes[32] = b""
    return_data = raw_call(
        _MODEXP, 
        abi_encode(C, C, C, u, minus_2modf, f), 
        max_outsize=32, 
        is_static_call=True
    )
    return abi_decode(return_data, (uint256))