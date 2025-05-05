import typing
import numpy as np
import pandas as pd
import os

import src.component as Component
from src.grafical import ComplexFunction

class Circuit:

    def __init__(self, path: str = None) -> None:
        # Counter for real terminals across all active component analyses
        self.n: int = 0
        # Counter for terminals within a single active component analysis
        self.temp_n: int = 0
        # Matrix of the circuit equation system (MNA - Modified Nodal Analysis)
        self.matrix: np.ndarray = np.zeros(shape=(0, 0), dtype=complex)
        # Both vectors don't just store voltages, but are a mix of voltages and currents 
        # voltages accumulates results across all superposition analyses (are the variables e1, iR1, etc)
        # currents accumulates the constants that are used to solve the system (are the constants I1, V1, etc)
        # suggestion (pedro): rename to variables and constants. Names come from original Nodal Analysis
        self.voltages: np.ndarray = np.zeros(shape=(0, 1), dtype=complex)
        self.currents: np.ndarray = np.zeros(shape=(0, 1), dtype=complex)

        # Dictionary to store all components by name
        self.components: typing.Dict[str, Component.Component] = dict()
        # Lists to separate independent sources and dependent components (active and passive)
        self.independent_components: typing.List[Component.Component] = []
        self.dependent_components: typing.List[Component.Component] = []
        # Maps terminal names to indices in the current analysis matrix
        self.terminals: typing.Dict[str, int] = dict()
        # Maps terminal names to indices in the final results vector
        # Used to accumulate superposition results across analyses
        self.real_terminals: typing.Dict[str, int] = dict()

    def read_netlist(self, path: str) -> None: # Changed return type to None
        """
        Reads a netlist file, parses components, and adds them to the circuit.

        Args:
            path: The path to the netlist file.

        Raises:
            FileNotFoundError: If the specified netlist file does not exist.
            ValueError: If a line in the netlist has an invalid format or unknown component type.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Netlist file not found: {path}")

        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                # Ignore comments and empty lines
                if not line or line.startswith('*'):
                    continue

                parts = line.split()
                if len(parts) < 3:
                    print(f"Skipping invalid line: {line}") # Or raise ValueError
                    continue

                component_type_char = parts[0][0].upper()
                name = parts[0]
                
                try:
                    if component_type_char == 'R':
                        # Format: R<name> <node1> <node2> <value>
                        if len(parts) != 4: raise ValueError("Invalid Resistor format")
                        comp = Component.Resistor(name, parts[1], parts[2], float(parts[3]))
                    elif component_type_char == 'V':
                        # Format: V<name> <node+> <node-> DC <value> (Assuming DC for now)
                        # TODO: Handle AC sources
                        if len(parts) != 5 or parts[3].upper() != 'DC': raise ValueError("Invalid or non-DC Voltage Source format")
                        comp = Component.VoltageSource(name, parts[1], parts[2], float(parts[4]))
                    elif component_type_char == 'I':
                         # Format: I<name> <node+> <node-> DC <value> (Assuming DC for now)
                         # TODO: Handle AC sources
                        if len(parts) != 5 or parts[3].upper() != 'DC': raise ValueError("Invalid or non-DC Current Source format")
                        comp = Component.CurrentSource(name, parts[1], parts[2], float(parts[4]))
                    elif component_type_char == 'C':
                        # Format: C<name> <node+> <node-> <value> [IC=<initial_voltage>]
                        if len(parts) < 4: raise ValueError("Invalid Capacitor format")
                        initial_voltage = 0.0
                        if len(parts) > 4 and parts[4].upper().startswith('IC='):
                            initial_voltage = float(parts[4].split('=')[1])
                        comp = Component.Capacitor(name, parts[1], parts[2], float(parts[3]), initial_voltage)
                    elif component_type_char == 'L':
                         # Format: L<name> <node+> <node-> <value> [IC=<initial_current>]
                        if len(parts) < 4: raise ValueError("Invalid Inductor format")
                        initial_current = 0.0
                        if len(parts) > 4 and parts[4].upper().startswith('IC='):
                            initial_current = float(parts[4].split('=')[1])
                        comp = Component.Inductor(name, parts[1], parts[2], float(parts[3]), initial_current)
                    # Dependent Sources
                    elif component_type_char == 'G': # VCCS
                        # Format: G<name> <out+> <out-> <control+> <control-> <transconductance>
                        if len(parts) != 6: raise ValueError("Invalid VCCS (G) format")
                        comp = Component.CurrentSourceControledByVoltage(name, parts[1], parts[2], parts[3], parts[4], float(parts[5]))
                    elif component_type_char == 'E': # VCVS
                        # Format: E<name> <out+> <out-> <control+> <control-> <gain>
                        if len(parts) != 6: raise ValueError("Invalid VCVS (E) format")
                        comp = Component.VoltageSourceControledByVoltage(name, parts[1], parts[2], parts[3], parts[4], float(parts[5]))
                    elif component_type_char == 'F': # CCCS
                         # Format: F<name> <out+> <out-> <control_Vname> <gain>
                        if len(parts) != 6: raise ValueError("Invalid CCCS (F) format - Check implementation details")
                        comp = Component.CurrentSourceControledByCurrent(name, parts[1], parts[2], parts[3], parts[4], float(parts[5]))
                    elif component_type_char == 'H': # CCVS
                        # Format: H<name> <out+> <out-> <control_Vname> <transresistance>
                        if len(parts) != 6: raise ValueError("Invalid CCVS (H) format - Check implementation details")
                        comp = Component.VoltageSourceControledByCurrent(name, parts[1], parts[2], parts[3], parts[4], float(parts[5]))
                        # H<name> <out+> <out-> <control_node+> <control_node-> <value>
                    # TODO: Add K (Transformer) parsing - requires finding L1, L2 first.
                    else:
                        print(f"Skipping unknown component type: {parts[0]}")
                        continue
                        
                    self.add_component(comp)

                except (ValueError, IndexError) as e:
                    print(f"Error parsing line: {line} - {e}")

    def check_terminals(self, component: Component.Component):
        """
        Checks if component terminals already exist in the circuit and adds them if necessary.
        Updates both the temporary terminals for the current analysis and the global terminal mapping.
        
        For each new terminal, this method:
        1. Updates the current analysis mapping and matrix dimensions
        2. Updates the global terminal mapping for superposition results
        
        Args:
            component: The component whose terminals need to be checked and added
        """
        for terminal in component.terminals:
            # If terminal not already in current analysis, add it
            if not terminal in self.terminals:
                # Assign temporary index for this analysis
                self.terminals[terminal] = self.temp_n
                self.temp_n += 1
                # Expand matrix and vectors for the new terminal
                self.matrix = np.pad(self.matrix, ((0, 1), (0, 1)), "constant")
                self.currents = np.pad(self.currents, ((0, 1), (0, 0)), "constant")
                self.voltages = np.pad(self.voltages, ((0, 1), (0, 0)), "constant") # Changing to voltages alters results. Which is correct?

            # If terminal not registered in global mapping for superposition, add it
            if not terminal in self.real_terminals:
                # Assign global index for superposition results
                self.real_terminals[terminal] = self.n
                self.n += 1
                # Expand final results vector to accommodate new terminal
                self.voltages = np.pad(self.voltages, ((0, 1), (0, 0)), "constant")

    def add_component(self, component: Component.Component) -> None:
        """
        Adds a component to the circuit and registers its terminals.
        
        Args:
            component: The component to add to the circuit
        """
        self.components[component.name] = component
        self.check_terminals(component)

    def solve(self, earth: str, sweep: complex = None) -> None:
        """
        Solves the circuit using superposition principle.
        
        For each independent source (active component):
        1. Builds a new circuit matrix considering just that source
        2. Solves the system with the source active
        3. Accumulates results using superposition
        
        Args:
            earth: The reference node (ground) name
            sweep: Optional complex frequency value for AC analysis
        """
        self.voltages: np.ndarray = np.zeros(shape=(0, 1))

        self.independent_components: typing.List[Component.Component] = []
        self.dependent_components: typing.List[Component.Component] = []

        for name in self.components:
            component = self.components[name]
            if component.independent:
                self.independent_components.append(component)
            else:
                self.dependent_components.append(component)

        for independent_component in self.independent_components:
            self.temp_n = 0
            self.matrix: np.ndarray = np.zeros(shape=(0, 0), dtype=complex)
            self.currents: np.ndarray = np.zeros(shape=(0, 1), dtype=complex)
            self.terminals: typing.Dict[str, int] = dict()

            self.check_terminals(independent_component)
            independent_component.stamp(self.matrix, self.currents, self.terminals, active=True)
            if sweep: s = sweep
            else: s = independent_component.s

            for dependent_component in self.dependent_components:
                self.check_terminals(dependent_component)
                dependent_component.set_s(s)
                dependent_component.stamp(self.matrix, self.currents, self.terminals)
            
            for component in self.independent_components:
                if component != independent_component:
                    self.check_terminals(component)
                    component.set_s(s)
                    component.stamp(self.matrix, self.currents, self.terminals, active=False)

            assert earth in self.terminals

            matrix = np.delete(np.delete(self.matrix, self.terminals[earth], axis=0) , self.terminals[earth], axis=1)
            current = np.delete(self.currents, self.terminals[earth], axis=0)
            voltages = np.linalg.solve(matrix, current)
            voltages = np.insert(voltages, self.terminals[earth], 0).reshape(-1, 1)

            if self.voltages.dtype != voltages.dtype:
                self.voltages = self.voltages.astype(complex)
                voltages = voltages.astype(complex)

            for key in self.terminals:
                self.voltages[self.real_terminals[key]] += voltages[self.terminals[key]]

    def clear_components(self) -> None:
        """
        Clears all components from the circuit.
        
        Resets the component dictionary and terminal mappings.
        """
        self.components = dict()
        self.independent_components = []
        self.dependent_components = []
        self.terminals = dict()
        self.real_terminals = dict()
        self.n = 0
        self.temp_n = 0

    def component_info(self, name: str) -> pd.Series:
        """
        Retrieves information about a specific component in the circuit.
        
        Calculates voltage, current, and power for the component based
        on the current state of the solved circuit.
        
        Args:
            name: The name of the component to retrieve information about
            
        Returns:
            A pandas Series containing the component name, voltage, current, and power
            
        Raises:
            AssertionError: If the component name doesn't exist in the circuit
        """
        assert name in self.components
        info: pd.Series = pd.Series(index = ["Name", "Voltage", "Current", "Power"], dtype=object)
        info["Name"] = self.components[name].name
        info["Voltage"] = self.components[name].voltage(self.terminals, self.voltages)
        info["Current"] = self.components[name].current(self.terminals, self.voltages)
        info["Power"] = info["Voltage"]*info["Current"]
        return info

    def print_node_tensions(self) -> None:
        """
        Prints the voltages at each node in the circuit.
        
        This method iterates through the terminals and prints the voltage
        at each terminal based on the current state of the solved circuit.
        """
        for key in dict(sorted(self.real_terminals.items())):

            if "I" in key:
                continue
            print(f"{key}: {self.voltages[self.real_terminals[key]]} V")

    def transfer_function(self, earth: str,
                        input: typing.Tuple[str, str], 
                        output: typing.Tuple[str, str]) \
                        -> ComplexFunction:
        
        assert input[0] in self.components
        assert output[0] in self.components

        assert input[1] in ["Voltage", "Current", "Power"]
        assert output[1] in ["Voltage", "Current", "Power"]

        class function(ComplexFunction):
            @staticmethod
            def f(values):
                if type(values) == np.ndarray:
                    if len(values.shape) == 2:
                        answer = []
                        for values_list in values:
                            for s in values_list:
                                self.components[input[0]].set_s(s)
                                self.solve(earth, s)

                                input_component_info = self.component_info(input[0])[input[1]]
                                output_component_info = self.component_info(output[0])[output[1]]
                                answer.append(output_component_info/input_component_info)
                        answer = np.array(answer).reshape(values.shape)
                        return answer
                    elif len(values.shape) == 1:
                        answer = []
                        for s in values:
                            self.components[input[0]].set_s(s)
                            self.solve(earth, s)

                            input_component_info = self.component_info(input[0])[input[1]]
                            output_component_info = self.component_info(output[0])[output[1]]
                            answer.append(output_component_info/input_component_info)
                        answer = np.array(answer).reshape(values.shape)
                        return answer
                elif type(values) == complex:
                    self.components[input[0]].set_s(s)
                    self.solve(earth, s)

                    input_component_info = self.component_info(input[0])[input[1]]
                    output_component_info = self.component_info(output[0])[output[1]]
                    return output_component_info/input_component_info

        return function()

    def table(self, components: typing.List[str] = None) -> pd.DataFrame:
        """
        Creates a table with information about all or selected components.
        
        Args:
            components: Optional list of component names to include in the table.
                       If None, includes all components.
                       
        Returns:
            A pandas DataFrame with component information (name, voltage, current, power)
        """
        series = []

        if not components: components = self.components.keys()

        for component_name in components:
            series.append(self.component_info(component_name))

        return pd.concat(series, axis=1).T

if __name__ == "__main__":
    pass
