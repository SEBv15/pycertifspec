import numpy as np

class DataTypes:
    """All supported SPEC data types"""
    SV_DOUBLE = 1
    """Not used by SPEC (`np.double`)"""
    SV_STRING = 2
    """Regular string. Basically used for everything by SPEC"""
    SV_ERROR = 3
    """An error occurred"""
    SV_ASSOC = 4
    """Associative array (`dict`)"""
    SV_ARR_DOUBLE = 5
    """Array of `np.double`"""
    SV_ARR_FLOAT = 6
    """Array of `np.single`"""
    SV_ARR_LONG = 7
    """Array of `np.int32`"""
    SV_ARR_ULONG = 8
    """Array of `np.uint32`"""
    SV_ARR_SHORT = 9
    """Array of `np.int16`"""
    SV_ARR_USHORT = 10
    """Array of `np.uint16`"""
    SV_ARR_CHAR = 11
    """Array of `np.byte`"""
    SV_ARR_UCHAR = 12
    """Array of `np.ubyte`"""
    SV_ARR_STRING = 13
    """Array of `np.byte`"""
    SV_ARR_LONG64 = 14
    """Array of `np.int64`"""
    SV_ARR_ULONG64 = 15
    """Array of `np.uint64`"""


    NP_TYPES = {
        SV_DOUBLE: np.double,
        SV_ARR_DOUBLE: np.double,
        SV_ARR_FLOAT: np.single,
        SV_ARR_LONG: np.int32,
        SV_ARR_ULONG: np.uint32,
        SV_ARR_SHORT: np.int16,
        SV_ARR_USHORT: np.uint16,
        SV_ARR_CHAR: np.byte,
        SV_ARR_UCHAR: np.ubyte,
        SV_ARR_STRING: np.byte,
        SV_ARR_LONG64: np.int64,
        SV_ARR_ULONG64: np.uint64
    }
    """Dict containing numpy types for corresponding SPEC array types"""

    ARRAYS = list(range(5, 16))
    """List containing all SPEC array magic numbers"""