import pandas as pd
import numpy as np

from src.circuit import Circuit
import src.component as Component

# Ler e salvar a Netlist
# Funções personalizadas de erro
# Concertar a Transfer Funcion
# Adaptar para uma análise DC

if __name__ == "__main__":

    circuit = Circuit()

    components = [
        Component.VoltageFont("V1", 'a', 'gnd', 5),
        Component.VoltageFont("V2", 'b', 'a', 5),
        Component.Resistor("R1", 'b', 'c', 1000),
        Component.Resistor("R2", 'c', 'gnd', 1000)
    ]
    for component in components:
        circuit.add_component(component)

    circuit.solve('gnd')
    for variable, value in zip(circuit.terminals, circuit.voltages):
        print(f"{variable}: {value} V")
    print(circuit.table())

    circuit.clear_components()

    components = [ #Falstad Capacitor example
        Component.VoltageFont("V1", 'a', 'gnd', 5),
        Component.Capacitor("C1", 'a', 'b', 200e-6),
        Component.Resistor("R1", 'b', 'gnd', 100)
    ]

    for component in components:
        circuit.add_component(component)

    circuit.solve('gnd')
    for variable, value in zip(circuit.terminals, circuit.voltages):
        print(f"{variable}: {value} V")
    print(circuit.table())

    circuit.clear_components()

    components = [ #Falstad Voltage Divider example
    Component.VoltageFont("V1", 'top', 'gnd', 10),  # 10V source
    Component.Resistor("R1", 'top', 'mid_left', 10000),
    Component.Resistor("R2", 'mid_left', 'gnd', 10000),
    Component.Resistor("R3", 'top', 'n1', 10000),
    Component.Resistor("R4", 'n1', 'n2', 10000),
    Component.Resistor("R5", 'n2', 'n3', 10000),
    Component.Resistor("R6", 'n3', 'gnd', 10000),
]

    for component in components:
        circuit.add_component(component)

    circuit.solve('gnd')
    for variable, value in zip(circuit.terminals, circuit.voltages):
        print(f"{variable}: {value} V")
    print(circuit.table())

    circuit.clear_components()

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
    
    df = circuit.table()

    print(df)