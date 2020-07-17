from .DataTypes import DataTypes
import numpy as np
import struct
from functools import reduce

class Var:
    """
    Represents a var/ property. All types can be read, but currently only non-arrays can be written
    """
    def __init__(self, name, conn, dtype=str):
        """
        Create a variable object.

        Parameters:
            name (str): The name of the variable
            conn (Client): An instance of Client connected to SPEC
            dtype (Type): The datatype of the variable (Only if not array)
        """
        self.name = name
        """Name of the variable"""
        self.conn = conn
        self.dtype = dtype
        self._rows = None
        self._cols = None
        self._sv_type = DataTypes.SV_STRING
        if self.value is None:
            raise ValueError("Variable doesn't exist")

    @property
    def value(self):
        """The value of the variable"""
        res = self.conn.get("var/{}".format(self.name))
        if res is None:
            return None

        self._sv_type = res.type
        self._cols = res.cols
        self._rows = res.rows

        if res.type == DataTypes.SV_STRING:
            return self.dtype(res.body)
        elif res.type == DataTypes.SV_ERROR:
            raise Exception(res.body)
        elif res.type == DataTypes.SV_ASSOC:
            elems = res.body.decode("utf-8").split("\x00")[:-2]
            out = {}
            for i in range(0, len(elems), 2):
                out[elems[i]] = elems[i+1]
            return out

        if res.type == DataTypes.SV_ARR_STRING:
            allstr = res.body.decode("utf-8")
            outarr = np.asarray([allstr[i:i+res.cols] for i in range(0, len(allstr), res.cols)])
        else:
            outarr = np.frombuffer(res.body, dtype=DataTypes.NP_TYPES[res.type])

        if res.rows + res.cols != 1 and res.type != DataTypes.SV_ARR_STRING: # For a one-dimensional array, the value of one of rows or cols will be one.
            outarr = np.reshape(outarr, (res.rows, res.cols))

        return outarr

    @value.setter
    def value(self, value):
        print(self.conn.set("var/{}".format(self.name), value, wait_for_error=1, dtype=DataTypes.SV_ARR_STRING, cols=self._cols, rows=self._rows))

    def subscribe(self, callback, nowait=False, timeout=1):
        """
        Subscribe to changes in the value.

        Parameters:
            callback (function): The function to be called when the event is received
            nowait (boolean): By default the function waits for the first event after registering to see if an error occurred. To skip that set True
            timeout (float): The timeout to wait for a response after subscribing. Function returns False when it runs out 

        Returns:
            True if successful, False when an error occurred or timeout reached
        """
        return self.conn.subscribe("var/{}".format(self.name), callback, nowait=nowait, timeout=timeout)

    def unsubscribe(self, callback):
        """
        Unsubscribe from changes.

        Parameters:
            callback (function): The callback function

        Returns:
            (boolean): True if the callback was removed, False if it didn't exist anyways
        """
        return self.conn.unsubscribe("var/{}".format(self.name), callback)
