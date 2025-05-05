import pandas as pd
import numpy as np

from src.circuit import Circuit
import src.component as Component

# Ler e salvar a Netlist
# Funções personalizadas de erro
# Concertar a Transfer Funcion
# Adaptar para uma análise DC

if __name__ == "__main__":

    circuit_a = Circuit()

    components = [
        Component.VoltageFont("V1", 'a', 'gnd', 5),
        Component.VoltageFont("V2", 'b', 'a', 5),
        Component.Resistor("R1", 'b', 'c', 1000),
        Component.Resistor("R2", 'c', 'gnd', 1000)
    ]
    for component in components:
        circuit_a.add_component(component)

    circuit_a.solve('gnd')
    for variable, value in zip(circuit_a.terminals, circuit_a.voltages):
        print(f"{variable}: {value} V")
    print(circuit_a.table())


    # Correct values:
    # Va = 5.0 V
    # Vb = 10.0 V
    # Vc = 5.0 V
    # gnd = 0
    # I_V1 E I_V2 = 0,005 A
    # I_R1 E I_R2 = 0,005 A