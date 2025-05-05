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

    circuit = Circuit()

    components = [
        Component.CurrentFont("I1", 'a', 'b', 1j),
        Component.Inductor("L1", 'a', 'b', 2),
        Component.Capacitor("C1", 'a', 'c', 2),
        Component.Resistor("R1", 'c', 'b', 5),
        Component.VoltageFontControledByCurrent("Gm1", 'c', 'd', 'b', 'c', 2),
        Component.Resistor("R2", 'd', 'b', 3)
    ]

    for component in components:
        circuit.add_component(component)

    f = circuit.transfer_function('b', ("R2", "Current"), ("I1", "Current"))
    f.plot_laplace()
    f.plot_bode()

    circuit.solve('b', sweep=1j)
    
    for variable, value in zip(circuit.terminals, circuit.voltages):
        print(f"{variable}: {value} V")
    print(circuit.table())
