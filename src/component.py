import abc
import typing
import string
import random
import numpy as np

K: int = 3

class Component:

    def __init__(self, terminals: typing.List[str], name: str) -> None:
        self.name = name
        self.terminals: typing.List[str] = terminals
        self.s: complex = 0
        self.independent: bool = False

    def set_s(self, s: complex) -> None:
        self.s: complex = s

    @abc.abstractmethod
    def stamp(self, matrix: np.ndarray, currents: np.ndarray, terminals: typing.Dict[str, int]) -> None:
        pass

    @abc.abstractmethod
    def voltage(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        pass

    @abc.abstractmethod
    def current(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        pass

class Resistor(Component):

    def __init__(self, name: str, positive: str, negative: str, resistence: float) -> None:
        self.x: str = f"I_{name}"
        super().__init__([positive, negative, self.x], name)
        self.positive: str = positive
        self.negative: str = negative
        self.resistence: float = resistence

    def stamp(self, matrix: np.ndarray, currents: np.ndarray, terminals: typing.Dict[str, int]) -> None:
        matrix[terminals[self.positive], terminals[self.x]] += 1
        matrix[terminals[self.negative], terminals[self.x]] -= 1
        matrix[terminals[self.x], terminals[self.positive]] -= 1
        matrix[terminals[self.x], terminals[self.negative]] += 1
        matrix[terminals[self.x], terminals[self.x]] += self.resistence

    def voltage(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return voltages[terminals[self.positive]] - voltages[terminals[self.negative]]

    def current(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return (self.voltage(terminals, voltages))/self.resistence

class CurrentSourceControledByVoltage(Component):

    def __init__(self, name: str, positive: str, negative: str, positive_control: str, negative_control: str, transconductance: complex) -> None:
        super().__init__([positive, negative, positive_control, negative_control], name)
        self.positive: str = positive
        self.negative: str = negative
        self.positive_control: str = positive_control
        self.negative_control: str = negative_control
        self.transconductance: complex = transconductance

    def stamp(self, matrix: np.ndarray, currents: np.ndarray, maping: typing.Dict[str, int]) -> None:
        matrix[maping[self.positive], maping[self.positive_control]] += self.transconductance
        matrix[maping[self.positive], maping[self.negative_control]] -= self.transconductance
        matrix[maping[self.negative], maping[self.positive_control]] -= self.transconductance
        matrix[maping[self.negative], maping[self.negative_control]] += self.transconductance

    def voltage(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return voltages[terminals[self.positive]] - voltages[terminals[self.negative]]

    def current(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return self.transconductance * (voltages[terminals[self.positive_control]] - voltages[terminals[self.negative_control]])

class CurrentSource(Component):

    def __init__(self, name: str, positive: str, negative: str, current_value: complex, s: complex = 0) -> None:
        super().__init__([positive, negative], name)
        self.positive: str = positive
        self.negative: str = negative
        self.value: complex = current_value
        self.s: complex = s
        self.independent: bool = True

    def stamp(self, matrix: np.ndarray, currents: np.ndarray, terminals: typing.Dict[str, int], active: bool) -> None:
        if active:
            currents[terminals[self.positive]] -= self.value
            currents[terminals[self.negative]] += self.value

    def voltage(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return voltages[terminals[self.positive]] - voltages[terminals[self.negative]]

    def current(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return self.value

class Capacitor(Component):

    def __init__(self, name: str, positive: str, negative: str, capacitance: float, initial_voltage: float = 0) -> None:
        super().__init__([positive, negative], name)
        self.positive: str = positive
        self.negative: str = negative
        self.capacitance: float = capacitance
        self.initial_voltage: float = initial_voltage

    def stamp(self, matrix: np.ndarray, currents: np.ndarray, terminals: typing.Dict[str, int]) -> None:
        matrix[terminals[self.negative], terminals[self.negative]] += self.s*self.capacitance
        matrix[terminals[self.positive], terminals[self.negative]] -= self.s*self.capacitance
        matrix[terminals[self.negative], terminals[self.positive]] -= self.s*self.capacitance
        matrix[terminals[self.positive], terminals[self.positive]] += self.s*self.capacitance

        currents[terminals[self.positive]] += self.capacitance*self.initial_voltage
        currents[terminals[self.negative]] -= self.capacitance*self.initial_voltage

    def voltage(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return voltages[terminals[self.positive]] - voltages[terminals[self.negative]]

    def current(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return self.s*self.capacitance*self.voltage(terminals, voltages) - self.capacitance*self.initial_voltage

class Inductor(Component):
    
    def __init__(self, name: str, positive: str, negative: str, indutance: float, initial_current: float = 0) -> None:
        self.x: str = f"I_{name}"
        super().__init__([positive, negative, self.x], name)
        self.positive: str = positive
        self.negative: str = negative
        self.indutance: float = indutance
        self.initial_current: float = initial_current

    def stamp(self, matrix: np.ndarray, currents: np.ndarray, terminals: typing.Dict[str, int]) -> None:
        matrix[terminals[self.positive], terminals[self.x]] += 1
        matrix[terminals[self.negative], terminals[self.x]] -= 1
        matrix[terminals[self.x], terminals[self.positive]] -= 1
        matrix[terminals[self.x], terminals[self.negative]] += 1
        matrix[terminals[self.x], terminals[self.x]] += self.s*self.indutance

        currents[terminals[self.x]] += self.initial_current/self.s

    def voltage(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return voltages[terminals[self.positive]] - voltages[terminals[self.negative]]

    def current(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return (self.initial_current/self.s) + (self.voltage(terminals, voltages)/(self.s*self.indutance))

class Transformer(Component):

    def __init__(self, name: str, inductor1: Inductor, inductor2: Inductor, m: float) -> None:
        self.x: str = f"I_ab_{name}"
        self.y: str = f"I_cd_{name}"
        super().__init__(inductor1.terminals + inductor2.terminals + (self.x, self.y), name)
        self.inductor1: Inductor = inductor1
        self.inductor2: Inductor = inductor2
        self.m: float = m

    def stamp(self, matrix: np.ndarray, currents: np.ndarray, terminals: typing.Dict[str, int]) -> None:
        matrix[terminals[self.inductor1.positive], terminals[self.x]] += 1
        matrix[terminals[self.inductor1.negative], terminals[self.x]] -= 1
        matrix[terminals[self.inductor2.positive], terminals[self.y]] += 1
        matrix[terminals[self.inductor2.negative], terminals[self.y]] -= 1

        matrix[terminals[self.x], terminals[self.inductor1.positive]] -= 1
        matrix[terminals[self.x], terminals[self.inductor1.negative]] += 1
        matrix[terminals[self.y], terminals[self.inductor2.positive]] -= 1
        matrix[terminals[self.y], terminals[self.inductor2.negative]] += 1

        matrix[terminals[self.x], terminals[self.x]] += self.s * self.inductor1.indutance
        matrix[terminals[self.y], terminals[self.y]] += self.s * self.inductor2.indutance
        matrix[terminals[self.x], terminals[self.y]] += self.s * self.m
        matrix[terminals[self.y], terminals[self.x]] += self.s * self.m

        currents[terminals[self.x]] += self.inductor1.indutance * self.inductor1.initial_current + self.m * self.inductor2.initial_current
        currents[terminals[self.y]] += self.m * self.inductor1.initial_current + self.inductor2.indutance * self.inductor2.initial_current 

    def voltage(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        pass

    def current(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        pass

class VoltageSource(Component):

    def __init__(self, name: str, positive: str, negative: str, voltage_value: complex, s: complex = 0) -> None:
        self.x: str = f"I_{name}" 
        super().__init__([positive, negative, self.x], name)
        self.positive: str = positive
        self.negative: str = negative

        self.value: complex = voltage_value
        self.s: complex = s
        self.independent: bool = True

    def stamp(self, matrix: np.ndarray, currents: np.ndarray, terminals: typing.Dict[str, int], active: bool) -> None:
        matrix[terminals[self.positive], terminals[self.x]] += 1
        matrix[terminals[self.negative], terminals[self.x]] -= 1
        matrix[terminals[self.x], terminals[self.positive]] -= 1
        matrix[terminals[self.x], terminals[self.negative]] += 1

        if active:
            currents[terminals[self.x]] -= self.value

    def voltage(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return self.value

    def current(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return voltages[terminals[self.x]]

class VoltageSourceControledByVoltage(Component):

    def __init__(self, name: str, positive: str, negative: str, positive_control: str, negative_control: str, amplification: complex):
        self.x: str = f"I_{name}"
        super().__init__([positive, negative, positive_control, negative_control, self.x], name)
        self.positive: str = positive
        self.negative: str = negative
        self.positive_control: str = positive_control
        self.negative_control: str = negative_control
        self.amplification: complex = amplification

    def stamp(self, matrix: np.ndarray, currents: np.ndarray, terminals: typing.Dict[str, int]) -> None:
        matrix[terminals[self.positive], terminals[self.x]] += 1
        matrix[terminals[self.negative], terminals[self.x]] -= 1
        matrix[terminals[self.x], terminals[self.positive]] -= 1
        matrix[terminals[self.x], terminals[self.negative]] += 1
        matrix[terminals[self.x], terminals[self.positive_control]] += self.amplification
        matrix[terminals[self.x], terminals[self.negative_control]] -= self.amplification

    def voltage(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return self.amplification*(voltages[terminals[self.positive_control]] - voltages[terminals[self.negative_control]])

    def current(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return voltages[terminals[self.x]]

class CurrentSourceControledByCurrent(Component):

    def __init__(self, name: str, positive: str, negative: str, positive_control: str, negative_control: str, amplification: complex):
        self.x: str = f"I_{name}"
        super().__init__([positive, negative, positive_control, negative_control, self.x], name)
        self.positive: str = positive
        self.negative: str = negative
        self.positive_control: str = positive_control
        self.negative_control: str = negative_control
        self.amplification: complex = amplification

    def stamp(self, matrix: np.ndarray, currents: np.ndarray, terminals: typing.Dict[str, int]) -> None:
        matrix[terminals[self.positive], terminals[self.x]] += self.amplification
        matrix[terminals[self.negative], terminals[self.x]] -= self.amplification
        matrix[terminals[self.positive_control], terminals[self.x]] += 1
        matrix[terminals[self.negative_control], terminals[self.x]] -= 1
        matrix[terminals[self.x], terminals[self.positive_control]] -= 1
        matrix[terminals[self.x], terminals[self.negative_control]] += 1

    def voltage(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return voltages[terminals[self.positive]] - voltages[terminals[self.negative]]

    def current(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return self.amplification * voltages[terminals[self.x]]

class VoltageSourceControledByCurrent(Component):

    def __init__(self, name: str, positive: str, negative: str, positive_control: str, negative_control: str, amplification: complex):
        self.x: str = f"I_control_{name}"
        self.y: str = f"I_{name}"
        super().__init__([positive, negative, positive_control, negative_control, self.x, self.y], name)
        self.positive: str = positive
        self.negative: str = negative
        self.positive_control: str = positive_control
        self.negative_control: str = negative_control
        self.amplification: complex = amplification

    def stamp(self, matrix: np.ndarray, currents: np.ndarray, terminals: typing.Dict[str, int]) -> None:
        matrix[terminals[self.positive], terminals[self.y]] += 1
        matrix[terminals[self.negative], terminals[self.y]] -= 1
        matrix[terminals[self.positive_control], terminals[self.x]] += 1
        matrix[terminals[self.negative_control], terminals[self.x]] -= 1
        matrix[terminals[self.x], terminals[self.positive_control]] -= 1
        matrix[terminals[self.x], terminals[self.negative_control]] += 1
        matrix[terminals[self.y], terminals[self.positive]] -= 1
        matrix[terminals[self.y], terminals[self.negative]] += 1
        matrix[terminals[self.y], terminals[self.x]] += self.amplification

    def voltage(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return self.amplification * voltages[terminals[self.y]]

    def current(self, terminals: typing.Dict[str, int], voltages: np.ndarray) -> complex:
        return voltages[terminals[self.y]]

if __name__ == "__main__":
    pass
