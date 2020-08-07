from ophyd.status import Status
try:
    from pycertifspec import Client as SPECClient
except:
    SPECClient = object
from collections import OrderedDict
import time as tm
import threading

class Counter:
    def __init__(self, client, name="SPEC", visualize_counters=[]):
        """
        Create a bluesky combatible detector from SPEC counters

        Parameters:
            client: An instance of the Client class
            name (string): Name to be used in bluesky
            visualize_counters (list): List of counter names to use for best-effort visualization
        """
        if not isinstance(client, SPECClient):
            raise ValueError("client needs to be instance of Client")

        self.client = client
        self.name = name
        self.hints = {'fields': visualize_counters}
        self.parent = None
        self.data = OrderedDict()
        self.duration = 1

    def read(self):
        return self.data

    def describe(self):
        out = OrderedDict()
        for mne in self.data.keys():
            out[mne] = {'source': "scaler/{}/value".format(mne), 'dtype': 'number', 'shape': [], 'name': self.client.counter_names[mne]}
        return out

    def _data_callback(self, rdata):
        self.data = OrderedDict()
        for key, value in rdata.items():
            self.data[key] = {'value': value, 'timestamp': tm.time()}
    
    def trigger(self):
        self.status = Status()
        def run_count():
            self.client.count(self.duration, callback=self._data_callback)
            self.status.set_finished()
        threading.Thread(target=run_count).start()
        return self.status

    def read_configuration(self):
        return OrderedDict([('duration', {'value': self.duration, 'timestamp': tm.time()})])

    def describe_configuration(self):
        return OrderedDict([('duration', {'source': "User defined", 'dtype': 'number', 'shape': []})])

    def configure(self, duration:float):
        """
        Configure the time (in seconds) to count

        Parameters:
            duration (float): Number of seconds to count
        """
        old = self.read_configuration()
        self.duration = duration
        return (old, self.read_configuration())
