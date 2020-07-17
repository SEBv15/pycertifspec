import numpy as np

class DataTypes:
    # DATA TYPES
    SV_DOUBLE = 1
    SV_STRING = 2
    SV_ERROR = 3
    SV_ASSOC = 4
    SV_ARR_DOUBLE = 5
    SV_ARR_FLOAT = 6
    SV_ARR_LONG = 7
    SV_ARR_ULONG = 8
    SV_ARR_SHORT = 9
    SV_ARR_USHORT = 10
    SV_ARR_CHAR = 11
    SV_ARR_UCHAR = 12
    SV_ARR_STRING = 13
    SV_ARR_LONG64 = 14
    SV_ARR_ULONG64 = 15


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
