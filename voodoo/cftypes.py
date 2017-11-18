from enum import Enum, IntFlag


class RLType(Enum):
    Release = 1
    Beta = 2
    Alpha = 3

    @staticmethod
    def get(v):
        if isinstance(v, RLType):
            return v
        if isinstance(v, int):
            return [t for t in RLType if t.value == v][0]
        if isinstance(v, str):
            return [t for t in RLType if t.name.lower() == v.lower()][0]

    def __lt__(self, other: 'RLType'):
        return self.value < other.value

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)


class DependencyType(Enum):
    Required = 1
    Optional = 2
    Embedded = 3

    @staticmethod
    def get(v):
        if isinstance(v, DependencyType):
            return v
        if isinstance(v, int):
            return [t for t in DependencyType if t.value == v][0]
        if isinstance(v, str):
            return [t for t in DependencyType if t.name.lower() == v.lower()][0]

    def __lt__(self, other: 'DependencyType'):
        return self.value < other.value

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

class Side(IntFlag):
    Client = 1
    Server = 2
    Both = 3

    @staticmethod
    def get(v):
        if isinstance(v, Side):
            return v
        if isinstance(v, int):
            return [t for t in Side if t.value == v][0]
        if isinstance(v, str):
            if v == '':
                return Both
            return [t for t in Side if t.name.lower() == v.lower()][0]

    def __lt__(self, other: 'Side'):
        return self.value < other.value

    def __str__(self):
        return self.name
        
    def __repr__(self):
        return str(self)
