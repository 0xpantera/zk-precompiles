from src import rational_adder
from moccasin.boa_tools import VyperContract

def deploy() -> VyperContract:
    print("deploying")
    contract = rational_adder.deploy()
    print(f"Contract: {contract}")
    return contract


def moccasin_main() -> VyperContract:
    return deploy()
