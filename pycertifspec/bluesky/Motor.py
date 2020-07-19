from ophyd.status import Status
try:
    from pycertifspec import Motor as SPECMotor
except:
    SPECMotor = object
from collections import OrderedDict
import time as tm

class Motor:
    hints = {'fields': ['position']}

    def __init__(self, motor):
        """
        Create a bluesky motor from a SPEC motor

        Parameters:
            motor (Motor): A pycertifspec motor
        """
        if isinstance(motor, SPECMotor):
            self.motor = motor
        else:
            raise ValueError("Motor not pycertifspec.Motor")

        self.name = self.motor.name
        self.parent = None

    def read(self):
        return OrderedDict([
            ('position', {'value': self.motor.position, 'timestamp': tm.time()}),
            ('dial_position', {'value': self.motor.dial_position, 'timestamp': tm.time()}),
        ])
    
    def describe(self):
        return OrderedDict([
            ('position', {'source': "motor/{}/position".format(self.motor.name), 'dtype': "number", 'shape': []}),
            ('dial_position', {'source': "motor/{}/dial_position".format(self.motor.name), 'dtype': "number", 'shape': []}),
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

    def configure(self, offset=None):
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