from ophyd.status import Status
try:
    from pycertifspec import Motor as SPECMotor
except:
    SPECMotor = object
from collections import OrderedDict
import time as tm

class Motor:
    """
    Class representing a SPEC motor that can be used with bluesky
    """
    
    def __init__(self, motor):
        """
        Create a bluesky motor from a SPEC motor

        Parameters:
            motor (pycertifspec.Motor): A pycertifspec motor
        """
        if isinstance(motor, SPECMotor):
            self.motor = motor
        else:
            raise ValueError("Motor not pycertifspec.Motor")

        self.name = self.motor.name
        self.parent = None
        self.hints = {'fields': ['{}_position'.format(self.name)]}

    def read(self):
        return OrderedDict([
            ('{}_position'.format(self.name), {'value': self.motor.position, 'timestamp': tm.time()}),
            ('{}_dial_position'.format(self.name), {'value': self.motor.dial_position, 'timestamp': tm.time()}),
        ])
    
    def describe(self):
        return OrderedDict([
            ('{}_position'.format(self.name), {'source': "motor/{}/position".format(self.motor.name), 'dtype': "number", 'shape': []}),
            ('{}_dial_position'.format(self.name), {'source': "motor/{}/dial_position".format(self.motor.name), 'dtype': "number", 'shape': []}),
        ])
    
    def trigger(self):
        status = Status()
        status.set_finished()
        return status

    def read_configuration(self):
        return OrderedDict([
            ('offset', {'value': self.motor.offset, 'timestamp': tm.time()}),
            ('step_size', {'value': self.motor.step_size, 'timestamp': tm.time()}),
            ('sign', {'value': self.motor.sign, 'timestamp': tm.time()}),
        ])

    def describe_configuration(self):
        return OrderedDict([
            ('offset', {'source': "motor/{}/offset".format(self.motor.name), 'dtype': "number", 'shape': []}),
            ('step_size', {'source': "motor/{}/step_size".format(self.motor.name), 'dtype': "number", 'shape': []}),
            ('sign', {'source': "motor/{}/sign".format(self.motor.name), 'dtype': "number", 'shape': []}),
        ])

    def configure(self, offset:float=None):
        """
        Configure settings for the motor

        Parameters:
            offset (number): Set by what amount the reported position should deviate from the measured
        """
        before = self.read_configuration

        if offset is not None:
            self.motor.offset = offset

        return (before, self.read_configuration)

    def stop(self, *args, **kwargs):
        """
        Stop all running SPEC commands if still moving
        """
        if not self.motor.move_done:
            self.motor.conn.abort()
    
    def set(self, position):
        self.status = Status()
        self.motor.moveto(position, blocking=False, callback=self.status.set_finished)
        return self.status

    @property
    def position(self):
        return self.motor.position