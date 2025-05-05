from src.circuit import Circuit
import os

circuit = Circuit()

test_dir = './tests'
for file in [os.path.join(test_dir, f) for f in os.listdir(test_dir) if f.endswith('.txt')]:
    print(f"Testing {file}")
    circuit.clear_components()
    circuit.read_netlist(file)
    circuit.solve('0')

    print(circuit.table())
    circuit.print_node_tensions()