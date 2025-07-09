# Rational Adder (BN-254)

A tiny Vyper contract that verifies, inside the scalar field of the BN‑254 curve, that two secret rational numbers add up to a public rational number – without revealing the summands themselves.

```
A = (x₁ , y₁)    →  r₁ = x₁ · y₁⁻¹   (mod r)
B = (x₂ , y₂)    →  r₂ = x₂ · y₂⁻¹   (mod r)

Assertion checked on-chain:
        r₁ + r₂  ≟  num · den⁻¹      (mod r)
```

The only expensive primitive required is the modular inverse, obtained with the Byzantium-era `modexp` precompile at address `0x05`.

---

## Curve & Field Parameters

| Symbol | Meaning | Decimal value |
|--------|---------|---------------|
| **p**  | Base‑field prime (coordinates live in ℱ_p) | 21888242871839275222246405745257275088696311157297823662689037894645226208583 |
| **r**  | Scalar‑field / group‑order prime (scalars live in ℱ_r) | 21888242871839275222246405745257275088548364400416034343698204186575808495617 |

> **Important:** `r ≠ p`.  
> **Coordinates** and pairing precompiles (`0x06`, `0x07`, `0x08`) validate inputs modulo **p**, but **all scalar arithmetic (and SNARK circuits) happens modulo r**.  
> `r` is the modulus used by `Fr` in Arkworks, `bn::Fr` in the Substrate `bn` crate, and by the in‑EVM scalar‑multiplication precompile itself (`k·P` is internally reduced `k mod r`).

---

## Precompiles Used

| Address | Opcode   | Purpose                                                      |
|---------|----------|--------------------------------------------------------------|
| 0x05    | `modexp` | `base^exp mod mod` – used to compute inverses `a^(r‑2)`      |
| 0x06    | `ecAdd`  | Point addition on BN‑254 G1                                  |
| 0x07    | `ecMul`  | Scalar multiplication on BN‑254 G1                           |
| 0x08    | `ecPairing` | Pairing check for zk‑SNARK verification                   |

---

## How the Contract Works

1. **Inputs**

   ```vyper
   struct ECPoint:
       x: uint256  # numerator
       y: uint256  # denominator (non‑zero)
   ```

2. **Inverse via Fermat**

   ```vyper
   pow(y, r - 2, r)  # via modexp
   ```

3. **Field arithmetic** uses `uint256_mulmod` / `addmod` with modulus **r**.

4. **Equality checked**

   ```
   (x₁·y₁⁻¹ + x₂·y₂⁻¹) mod r == num·den⁻¹ mod r
   ```

Return `True` if the equation holds, else `False`. Witnesses remain secret.

---

## Finite‑Field & Group Context

* **Elliptic‑curve group:** BN‑254 G1 is cyclic of prime order **r**.  
* **Field choice:** All computation here is in ℱ_r, not ℱ_p.  
* **Zero‑knowledge link:** The same constraint would be embedded inside a Groth16/Plonk circuit, ensuring the on‑chain check and off‑chain proof agree.

---

## Testing

`tests/test_rational_adder.py` (pytest + hypothesis):

1. Deploys the contract (Moccasin).  
2. Generates random valid witnesses → expects `True`.  
3. Tweaks `num` by ±1 → expects `False`.  
4. Confirms revert on zero denominators.

Run:

```bash
mox test
```

---

## References

* **EIP‑196 / 197** – BN‑254 precompiles  
* [Arkworks](https://github.com/arkworks-rs/algebra) `ark_bn254`
* [Substrate](https://github.com/m-kus/substrate-bn-sp1) `bn`
* [RareSkills ZK](https://www.rareskills.io/zk-book) – origin of the assignment

```

_For documentation, please run `mox --help` or visit [the Moccasin documentation](https://cyfrin.github.io/moccasin)_
