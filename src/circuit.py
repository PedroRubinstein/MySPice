import typing
import numpy as np
import pandas as pd

import src.component as Component
from src.grafical import ComplexFunction

class Circuit:

    def __init__(self, path: str = None) -> None:
        """
        Initialize a new circuit object.
        
        Args:
            path: Optional path to a netlist file to load
        """
        # Counter for terminals in the system
        self.n: int = 0
        # Matrix of the circuit equation system (MNA - Modified Nodal Analysis)
        self.matrix: np.ndarray = np.zeros(shape=(0, 0), dtype=complex)
        # Both vectors store a mix of voltages and currents as per MNA approach
        # voltages stores the computed variables (node voltages, branch currents)
        # currents stores the constants used to solve the system (source values)
        self.voltages: np.ndarray = np.zeros(shape=(0, 1), dtype=complex)
        self.currents: np.ndarray = np.zeros(shape=(0, 1), dtype=complex)

        # Dictionary to store all components by name
        self.components: typing.Dict[str, Component.Component] = dict()
        # Lists for components (kept for compatibility)
        self.independent_components: typing.List[Component.Component] = []
        self.dependent_components: typing.List[Component.Component] = []
        # Maps terminal names to indices in the matrix
        self.terminals: typing.Dict[str, int] = dict()

        self.path: str = path if path else self.read_netlist(path)

    def read_netlist(self, path: str) -> str:
                pass

    def check_terminals(self, component: Component.Component):
        """
        Checks if component terminals already exist in the circuit and adds them if necessary.
        Updates the terminals mapping and expands the matrix as needed.
        
        For each new terminal, this method expands the matrix and vectors dimensions.
        
        Args:
            component: The component whose terminals need to be checked and added
        """
        for terminal in component.terminals:
            # If terminal not already in current matrix, add it
            if not terminal in self.terminals:
                # Assign index for this terminal
                self.terminals[terminal] = self.n
                self.n += 1
                # Expand matrix and vectors for the new terminal
                self.matrix = np.pad(self.matrix, ((0, 1), (0, 1)), "constant")
                self.currents = np.pad(self.currents, ((0, 1), (0, 0)), "constant")
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
        Solves the circuit using a single matrix approach.
        
        Builds a single circuit matrix considering all components at once
        and solves the system in one step.
        
        Args:
            earth: The reference node (ground) name
            sweep: Optional complex frequency value for AC analysis
        """
        # Reset matrices for this solution
        self.n = 0
        self.matrix = np.zeros(shape=(0, 0), dtype=complex)
        self.currents = np.zeros(shape=(0, 1), dtype=complex)
        self.terminals = dict()
        self.voltages = np.zeros(shape=(0, 1), dtype=complex)

        # Process all components at once
        for name, component in self.components.items():
            # Check terminals for each component
            self.check_terminals(component)
            
            # Set the complex frequency for this analysis
            if sweep is not None:
                component.set_s(sweep)
                
            # Add component to the matrix
            component.stamp(self.matrix, self.currents, self.terminals)

        # Check that the earth terminal exists
        assert earth in self.terminals

        # Remove the earth node from the system
        matrix = np.delete(np.delete(self.matrix, self.terminals[earth], axis=0), self.terminals[earth], axis=1)
        current = np.delete(self.currents, self.terminals[earth], axis=0)
        
        # Solve the system
        voltages = np.linalg.solve(matrix, current)
        
        # Insert the zero voltage at the earth node
        self.voltages = np.insert(voltages, self.terminals[earth], 0).reshape(-1, 1)

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

    def transfer_function(self, earth: str,
                        input: typing.Tuple[str, str], 
                        output: typing.Tuple[str, str]) \
                        -> ComplexFunction:
        """
        Calculates the transfer function between specified input and output components.
        
        This method creates a ComplexFunction that computes the ratio between
        an output characteristic and an input characteristic at different complex
        frequencies.
        
        Args:
            earth: The reference node (ground) name
            input: Tuple containing (component_name, property) for input
                  where property is one of "Voltage", "Current", or "Power"
            output: Tuple containing (component_name, property) for output
                   where property is one of "Voltage", "Current", or "Power"
                   
        Returns:
            A ComplexFunction object that computes the transfer function
            
        Raises:
            AssertionError: If the component names don't exist or properties are invalid
        """
        assert input[0] in self.components
        assert output[0] in self.components

        assert input[1] in ["Voltage", "Current", "Power"]
        assert output[1] in ["Voltage", "Current", "Power"]

        class function(ComplexFunction):
            @staticmethod
            def f(values):
                if type(values) == np.ndarray:
                    if len(values.shape) == 2:
                        # Handle 2D array of complex frequencies
                        answer = []
                        for values_list in values:
                            for s in values_list:
                                # Set complex frequency and solve circuit
                                self.components[input[0]].set_s(s)
                                self.solve(earth, s)

                                # Calculate ratio of output to input
                                input_component_info = self.component_info(input[0])[input[1]]
                                output_component_info = self.component_info(output[0])[output[1]]
                                answer.append(output_component_info/input_component_info)
                        answer = np.array(answer).reshape(values.shape)
                        return answer
                    elif len(values.shape) == 1:
                        # Handle 1D array of complex frequencies
                        answer = []
                        for s in values:
                            # Set complex frequency and solve circuit
                            self.components[input[0]].set_s(s)
                            self.solve(earth, s)

                            # Calculate ratio of output to input
                            input_component_info = self.component_info(input[0])[input[1]]
                            output_component_info = self.component_info(output[0])[output[1]]
                            answer.append(output_component_info/input_component_info)
                        answer = np.array(answer).reshape(values.shape)
                        return answer
                elif type(values) == complex:
                    # Handle single complex frequency
                    s = values  # Use values as the complex frequency
                    self.components[input[0]].set_s(s)
                    self.solve(earth, s)

                    # Calculate ratio of output to input
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