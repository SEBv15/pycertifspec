from typing import Optional
from ophyd.status import Status
try:
    from pycertifspec import Client as SPECClient
    from pycertifspec.SpecSocket import SpecMessage
except:
    SPECClient = object
    SpecMessage = object
from collections import OrderedDict
import time as tm
import threading
from typing import Callable

class CommandDetector:
    def __init__(
        self, 
        client:SPECClient, 
        name:str, 
        start_command:str, 
        poll_command:Optional[str] = None, 
        evaluate_poll:Callable[[SpecMessage, str], bool] = lambda _, __: True
        ):
        """
        Create a bluesky combatible detector backed by SPEC commands.

        For each run, the response to all commands will be saved as metadata. 
        In addition, it is possible to configure a description string which can be used to store, 
        for example, the location of the data files for later reference.

        Parameters:
            client (Client): An instance of the Client class
            name (str): Name for the detector to be used in bluesky
            start_command (str): SPEC command to start data aquisition
            poll_command (str): SPEC command to poll if detector is finished (If not set it is assumed detector finishes when start_command finishes)
            evaluate_poll (Callable[[SpecMessage, str], bool]): Function used to parse the response to the poll command (should return True when done). It will be given a SpecMessage object and the console print from the command.
        """
        if not isinstance(client, SPECClient):
            raise ValueError("client needs to be instance of Client")

        self.client = client
        self.name = name
        self.hints = {}
        self.parent = None

        self._start_cmd = start_command
        self._poll_cmd = poll_command
        self._eval_poll = evaluate_poll

        self.description = ""
        self._description_time = 0

        self._data = OrderedDict(
            ('start_response', {'value': ('', ''), 'timestamp': 0}),
            ('poll_responses', {'value': [], 'timestamp': 0})
        )

    def read(self):
        return self._data
    
    def describe(self):
        return OrderedDict(
            ('start_response', {'source': 'SPEC', 'dtype': 'tuple', 'shape': [2]}),
            ('poll_responses', {'source': 'SPEC', 'dtype': 'list', 'shape': []})
        )

    def trigger(self):
        self._status = Status()
        def run():
            msg, cons = self.client.run(self._start_cmd)
            self._data['start_response']['value'] = (msg.body, cons)
            self._data['start_response']['timestamp'] = tm.time()

            self._data['poll_responses']['value'] = []
            self._data['poll_responses']['timestamp'] = tm.time()
            if self._poll_cmd is not None:
                while True:
                    msg, cons = self.client.run(self._poll_cmd)
                    self._data['poll_responses']['value'].append((msg.body, cons))
                    self._data['poll_responses']['timestamp'] = tm.time()

                    if self._eval_poll(msg, cons):
                        break

            self._status.set_finished()
        threading.Thread(target=run).start()
        return self._status

    def read_configuration(self):
        return OrderedDict(('description', {'value': self.description, 'timestamp': self._description_time}))

    def describe_configuration(self):
        return OrderedDict(('description', {'source': 'user-defined', 'dtype': 'string', 'shape': []}))

    def configure(self, description:str):
        """
        Configure the description of the detector.

        Parameters:
            description (str): The description
        """
        old = self.read_configuration()
        self.description = description
        self._description_time = tm.time()
        return (old, self.read_configuration())
