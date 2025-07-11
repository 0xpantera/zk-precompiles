from src import ec_matmul
from moccasin.boa_tools import VyperContract

def deploy_ec_matmul() -> VyperContract:
    print("deploying EC matmul")
    ec_matmul_contract = ec_matmul.deploy()
    print(f"Contract: {ec_matmul}")
    return ec_matmul_contract

def moccasin_main() -> VyperContract:
    return deploy_ec_matmul()

