class Flags:
    """
    Building blocks for the `flags` field
    
    Currently only one flag is in use by SPEC
    """

    SV_DELETED = 0x1000
    """Sent to clients when watched variables or associative array elements are deleted"""
