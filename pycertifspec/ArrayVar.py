import collections
from .Var import Var
from .DataTypes import DataTypes

from typing import Tuple

class ArrayVar(Var, collections.MutableSequence):
    """
    Represents a SPEC array and behaves like a regular python list. Values assigned to array indices will be pushed to SPEC.

    The connection to SPEC decreases performance since the array gets fetched every time it is accessed. Therefore, for expensive computations, store the .value to a different variable and use that.
    """
    def __init__(self, name, client):
        super().__init__(name, client)

    @property
    def shape(self) -> Tuple[int]:
        """Shape of the array like in numpy"""
        res = self.conn.get("var/{}".format(self.name))
        if res is None:
            return None
        
        if res.type in DataTypes.ARRAYS:
            if res.cols == 1 or res.rows == 1: # 1D array
                return (max(res.cols, res.rows),)
            return (res.rows, res.cols)
        
        raise Exception("SPEC returned incorrect variable type")

    @property
    def is_2d(self) -> bool:
        """True if 2D array"""
        return len(self.shape) == 2
    
    def __getitem__(self, key):
        if isinstance(key, slice) or not self.is_2d:
            return self.value.__getitem__(key)
        elif isinstance(key, int):
            if self._sv_type == DataTypes.SV_ARR_STRING:
                return self.value[key]
            return SubArrayVar(self, key)
        else:
            raise KeyError("Invalid index of type {}".format(type(key)))

    def __setitem__(self, key, item):
        if isinstance(key, int):
            if hasattr(item, "__len__") and self.is_2d and self._sv_type != DataTypes.SV_ARR_STRING:
                if self.shape[1] == len(item):
                    sub = self[key]
                    for i, v in enumerate(item):
                        sub[i] = v
                else:
                    raise ValueError("Array length must match number of columns")
            else:
                if key >= len(self):
                    raise IndexError("Index out of range")
                if self._sv_type == DataTypes.SV_ARR_STRING:
                    item = "\"{}\"".format(item.replace('"', '\\"'))
                self.conn.run("{}[{}]={}".format(self.name, key, item))
        else:
            raise IndexError("Index must be of type int")

    def __delitem__(self, key):
        raise Exception("Array shape cannot be modified")
    
    def __len__(self):
        return self.shape[0]

    def insert(self, index, value):
        raise Exception("Array shape cannot be modified")

    def __str__(self):
        return self.value.__str__()

    def __repr__(self):
        return 'ArrayVar("{}", client)'.format(self.name)


class SubArrayVar(collections.MutableSequence):
    """
    Represents a row in a 2-dimensional SPEC array. 
    All data and modifications are still synced with SPEC.
    """
    def __init__(self, parent: ArrayVar, index: int):
        if not isinstance(parent, ArrayVar):
            raise ValueError("parent should be instance of ArrayVar")
        if index >= len(parent):
            raise IndexError("Index {} is out of bounds for axis 0 of array")

        self.parent = parent
        self.index = index

    def __getitem__(self, index: int):
        return self.parent.value[self.index][index]
    
    def __setitem__(self, index: int, item):
        if not isinstance(index, int):
            raise IndexError("Index must be of type int")
        if index >= self.parent.shape[1]:
            raise IndexError("Index out of range")
        
        self.parent.conn.run("{}[{}][{}]={}".format(self.parent.name, self.index, index, item))

    def __delitem__(self, index):
        raise Exception("Array shape cannot be modified")
    
    def __len__(self):
        return self.parent.shape[1]

    def insert(self, index, value):
        """Array shape cannot be modified"""
        raise Exception("Array shape cannot be modified")

    @property
    def value(self):
        return self.parent.value[self.index]
    
    def __str__(self):
        return self.value.__str__()

    def __repr__(self):
        return 'ArrayVar("{}", client)[{}]'.format(self.parent.name, self.index)