# BN-254 ZK Precompile Playground

This repo contains two small Vyper contracts that show how to use the
Byzantium BN-254 precompiles to validate algebraic statements on-chain
without revealing secret scalars.

| Contract | Purpose | Core precompiles |
|----------|---------|------------------|
| **`rational_adder.vy`** | Verify that two hidden rationals add up to a public one (`x₁/y₁ + x₂/y₂ = num/den`). | `modexp 0x05` |
| **`ec_matmul.vy`** | Verify that an **n × n** matrix times a hidden vector of G1 points equals a public scalar vector (`M·s = o`). | `ecMul 0x07`, `ecAdd 0x06` |

## Contract Summaries

### 1. `rational_adder.vy`

```text
A = (x₁ , y₁)    →  r₁ = x₁ · y₁⁻¹   (mod r)
B = (x₂ , y₂)    →  r₂ = x₂ · y₂⁻¹   (mod r)

Assertion checked on-chain:
        r₁ + r₂  ≟  num · den⁻¹      (mod r)
```

### 2. `ec_matmul.vy`

```text
Input:  M (n×n scalars),  s (n G1 pts = [sᵢ]G),  o (n scalars)
Goal :  M·s = o      element-wise
Check:  ∑ⱼ Mᵢⱼ·sⱼ   ?=  oᵢ·G    for each row i
```

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
* **Arkworks `ark_bn254`**, **Substrate `bn` crate** – curve libraries  
* RareSkills ZK – origin of the assignment

```

_For documentation, please run `mox --help` or visit [the Moccasin documentation](https://cyfrin.github.io/moccasin)_
