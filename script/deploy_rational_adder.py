from src import rational_adder
from moccasin.boa_tools import VyperContract

def deploy_rational_adder() -> VyperContract:
    print("deploying rational adder")
    rational_adder_contract = rational_adder.deploy()
    print(f"Contract: {rational_adder_contract}")
    return rational_adder_contract

def moccasin_main() -> VyperContract:
    return deploy_rational_adder()

