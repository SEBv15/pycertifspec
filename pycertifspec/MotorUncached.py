class MotorProperty:
    def __init__(self, name, readonly=False, dtype=str):
        self.name = name
        self.readonly = readonly
        self.dtype = dtype

    def __get__(self, instance, type):
        if instance is None:
            return self
        if self.name == "move_done":
            return not bool(float(instance.get(self.name).body))
        if self.dtype == bool:
            return self.dtype(float(instance.get(self.name).body))
        return self.dtype(instance.get(self.name).body)

    def __set__(self, instance, val):
        if self.readonly:
            return
        instance.set(self.name, val)

class Motor(object):
    position = MotorProperty("position", dtype=float)
    """Get the motor position in user units (setting a value will NOT move the motor but change the position offset)"""
    dial_position = MotorProperty("dial_position", dtype=float)
    """Get motor position in dial units (setting a value will NOT move the motor)"""
    offset = MotorProperty("offset", dtype=float)
    """The current user offset in dial units"""
    step_size = MotorProperty("step_size", readonly=True, dtype=float)
    """Steps-per-unit (read-only)"""
    sign = MotorProperty("sign", readonly=True)
    """Sign of user dial parameter (read-only)"""
    move_done = MotorProperty("move_done", readonly=True, dtype=bool)
    """True if done, False if busy (read-only). WARNING: The original value from SPEC is inverted"""
    high_lim_hit = MotorProperty("high_lim_hit", readonly=True, dtype=bool)
    """nonzero if the high-limit switch has been hit (read-only)"""
    low_lim_hit = MotorProperty("low_lim_hit", readonly=True, dtype=bool)
    """nonzero if the low-limit switch has been hit (read-only)"""
    emergency_stop = MotorProperty("emergency_stop", readonly=True, dtype=bool)
    """nonzero if an emergency-stop switch or condition has been activated (read-only)"""
    motor_fault = MotorProperty("motor_fault", readonly=True, dtype=bool)
    """Returns nonzero if a motor-fault condition has been activated (read-only)"""
    high_limit = MotorProperty("high_limit", dtype=float)
    """the high limit in dial units"""
    low_limit = MotorProperty("low_limit", dtype=float)
    """the low limit in dial units"""
    unusable = MotorProperty("unusable", readonly=True, dtype=bool)
    """Returns nonzero if the motor is unusable (read-only)"""
    base_rate = MotorProperty("base_rate", dtype=float)
    """base_rate"""
    slew_rate = MotorProperty("slew_rate", dtype=float)
    """slew_rate"""
    acceleration = MotorProperty("acceleration", dtype=float)
    """acceleration"""
    backlash = MotorProperty("backlash", dtype=float)
    """backlash"""

    def __init__(self, mne, conn):
        self.name = mne
        """The string mnemonic of the motor"""
        self.conn = conn

    def get(self, prop_name):
        """
        Get a motor property.

        Attributes:
            prop_name (string): The name of the property

        Returns:
            None if property doesn't exist
        """
        return self.conn.get("motor/{}/{}".format(self.name, prop_name))

    def set(self, prop_name, value, wait_for_error=0):
        """
        Set a motor property.

        Attributes:
            prop_name (string): The name of the property
            value: The value (will be converted to string before sending)
            wait_for_error (float): SPEC only sends a message back if the property doesn't exist. Set the number of seconds to wait for an error message (if there is one)

        Returns:
            False if property doesn't exist, else True
        """
        return self.conn.set("motor/{}/{}".format(self.name, prop_name), value, wait_for_error=wait_for_error)


    def _prop_getter_setter(self, name, readonly=False):
        def getter():
            return self.get(name)
        def setter(val):
            if readonly:
                raise Exception("Property is read-only")
            self.set(name, val)
        return property(getter, setter)

    def moveto(self, value, blocking=True):
        """
        Move motor to position
        
        Arguments:
            value (float): The position to move to
            blocking (boolean): Wait for move to finish before returning
        """
        #self.set("start_one", new_pos) # Doesn't work because SPEC is adding in some random string for some reason
        res = self.conn.run("{get_angles;A["+self.name+"]="+str(value)+";move_em;}\n", blocking=blocking)
        if res[0].err != 0:
            raise Exception(res[1])

    def move(self, value, blocking=True):
        """
        Move motor relative to current position
        
        Arguments:
            value (float): The distance to move
            blocking (boolean): Wait for move to finish before returning
        """
        new_pos = self.position + value
        res = self.conn.run("{get_angles;A["+self.name+"]="+str(new_pos)+";move_em;}\n", blocking=blocking)
        if res[0].err != 0:
            raise Exception(res[1])   
     
    def subscribe(self, prop, callback, nowait=False, timeout=1):
        """
        Subscribe to changes in a motor property.

        Parameters:
            prop (string): The property to listen to
            callback (function): The function to be called when the event is received
            nowait (boolean): By default the function waits for the first event after registering to see if an error occurred. To skip that set True
            timeout (float): The timeout to wait for a response after subscribing. Function returns False when it runs out 

        Returns:
            True if successful, False when an error occurred or timeout reached
        """
        return self.conn.subscribe("motor/{}/{}".format(self.name, prop), callback, nowait=nowait, timeout=timeout)

    def unsubscribe(self, prop, callback):
        """
        Unsubscribe from changes.

        Parameters:
            prop (string): The property to stop listening to
            callback (function): The callback function

        Returns:
            (boolean): True if the callback was removed, False if it didn't exist anyways
        """
        return self.conn.unsubscribe("motor/{}/{}".format(self.name, prop), callback)