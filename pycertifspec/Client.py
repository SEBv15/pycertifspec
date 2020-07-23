import numpy as np
import socket
from functools import reduce
import time as tm
import threading
import struct
import collections
from .EventTypes import EventTypes
from .DataTypes import DataTypes
from .Motor import Motor
from .Var import Var

"""
TODO: Add support for arrays in Client.set()
TODO: Add ability to scan ports
TODO: Maybe merge the two sockets into one
TODO: Rewrite Client._create_header() with struct
TODO: See if there is a better option for handling socket event listening. The threading.Event approach I am using seems kinda meh
"""

Message = collections.namedtuple('Message', 'magic vers size sn sec usec cmd type rows cols len err flags name body')

class Client:
    SV_VERSION = 4
    SV_NAME_LEN = 80
    SV_SPEC_MAGIC = 4277009102
    MAX_SCREEN_PRINT_LEN = 10000
    """The number of tty output characters to remember"""
    debug = False

    def __init__(self, host="localhost", port=6510):
        # Socket for events
        self.event_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.event_sock.connect((host, port))
        self._event_lock = threading.Lock()

        # Socket for everything else
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self._lock = threading.RLock()

        self._reply_data = {} # Holds replies
        self._reply_events = {} # To hold threading.Event for responses with serial number

        # Used to wait for errors or success when subscribing to events
        self._event_available = threading.Event()
        self._last_event = None

        # Serial number counter
        self._sn_counter = 0

        # The event subscription callbacks
        self._subscriptions = {}

        # Start event receiver deamon
        self._recv_thread = threading.Thread(target=self._threaded_event_listener)
        self._recv_thread.daemon = True
        self._recv_thread.start()

        # Start reply receiver deamon
        self._reply_thread = threading.Thread(target=self._threaded_reply_listener)
        self._reply_thread.daemon = True
        self._reply_thread.start()

        # Subscribe to errors when registering for events
        self.sock.send(self._create_header(123, EventTypes.SV_HELLO, 0, 0, "pycertifspec"))
        self.subscribe("error", lambda res : True, nowait=True)

        # Subscribe to screen print
        self._screen_print = ""
        self.sock.send(self._create_header(0, EventTypes.SV_REGISTER, 0, 0, "output/tty"))

        self.counter_names = collections.OrderedDict()
        """Dict containing mnemonic and pretty names for counters"""
        self._get_counter_names()

    def _create_header(self, serial_number, command, data_type, body_len, property_name, error=False, flags=[], rows=0, cols=0):
        """
        Create header bits send to SPEC server
        https://www.certif.com/spec_help/server.html.#protocol

        Attributes:
            serial_number (int): Serial number of message. Will be the same in server reply
            command (int): The command/event from EventTypes to execute
            data_type (int): The data type of the body
            body_len (int): The length of the body
            property_name (string): The name of the property to do work on
            error (int): Error if != 0
            flags (int): Set a flag (isn't used yet)
            rows (int): The number of rows of the body (if array)
            cols (int): The number of cols of the body (if array)

        Returns:
            (bytes): The header as bytes
        """
        magic = np.uint32(self.SV_SPEC_MAGIC)
        vers = np.int32(self.SV_VERSION)
        size = np.uint32(132)
        sn = np.uint32(serial_number)
        sec = np.uint32(tm.time())
        usec = np.uint32(int(tm.time()*(10**6)) & 2**32-1)
        cmd = np.int32(command)
        dtype = np.int32(data_type)
        rows = np.uint32(rows)
        cols = np.uint32(cols)
        blen = np.uint32(body_len)
        err = np.int32(error)
        flags = np.int32(reduce(lambda acc, f : acc | f, flags) if flags else 0)
        name = np.zeros(self.SV_NAME_LEN, dtype="S")
        nl = min(self.SV_NAME_LEN, len(property_name))
        name[:nl] = np.asarray(list(property_name), dtype="S")[:nl]
        header = np.asarray([magic, vers, size, sn, sec, usec, cmd, dtype, rows, cols, blen, err, flags], dtype=np.uint32).tobytes()
        header += name.tobytes()
        return header

    def _listen(self, sock):
        head1 = sock.recv(12) # Read until size
        magic, vers, size = struct.unpack("IiI", head1)
        if vers < 4:
            raise Exception("Server respondend with protocol version {}. Need at least 4".format(vers))
        head2 = sock.recv(size-12)            
        res = Message(magic, vers, size, *struct.unpack("IIIiiIIIii80s{}x".format(size-132), head2), body=None)
        res = res._replace(name=res.name.decode("utf-8").rstrip('\x00'))
        #print(res)

        # Read the body in chunks of 4096 bits. Larger will cause the program to fail
        body = b''
        bleft = res.len
        while bleft > 0:
            body += sock.recv(min(4096, bleft))
            bleft -= 4096

        if res.type == DataTypes.SV_STRING:
            res = res._replace(body=body.decode("utf-8").rstrip('\x00'))
        else:
            res = res._replace(body=body)
        if self.debug:
            print("RECEIVED", res)
        return res

    def subscribe(self, prop, callback, nowait=False, timeout=1):
        """
        Subscribe to changes in a property.

        Parameters:
            prop (string): The name of the property
            callback (function): The function to be called when the event is received
            nowait (boolean): By default the function waits for the first event after registering to see if an error occurred. To skip that set True
            timeout (float): The timeout to wait for a response after subscribing. Function returns False when it runs out 

        Returns:
            True if successful, False when the property is invalid or timeout reached
        """
        if prop not in self._subscriptions.keys():
            self._subscriptions[prop] = [callback]

            # Register if this is the first listener for the prop
            with self._event_lock:
                self.event_sock.send(self._create_header(0, EventTypes.SV_REGISTER, 0, 0, prop))
                if nowait:
                    return True
                if self._event_available.wait(timeout=timeout):
                    self._event_available.clear()
                    if self._last_event.name == "error" and self._last_event.body != "No error":
                        del self._subscriptions[prop]
                        return False
                else:
                    return False

        else:
            if not callback in self._subscriptions[prop]:
                self._subscriptions[prop].append(callback)
        return True

    def unsubscribe(self, prop, callback):
        """
        Unsubscribe from changes in the property.

        Parameters:
            prop (string): To property to unsubscribe from
            callback (function): The callback function

        Returns:
            (boolean): True if the callback was removed, False if it didn't exist anyways
        """
        if prop in self._subscriptions and callback in self._subscriptions[prop]: 
            self._subscriptions[prop].remove(callback)

            # Unsubscribe if nothing is listening anymore
            if len(self._subscriptions[prop]) == 0:
                with self._event_lock:
                    self.event_sock.send(self._create_header(0, EventTypes.SV_UNREGISTER, 0, 0, prop))
                    del self._subscriptions[prop]
            return True
        return False

    def run(self, command, blocking=True, callback=None):
        """
        Execute a command like from the interactive shell

        Arguments:
            command (string): The command to execute
            blocking (boolean): When True, the function will block until it receives a response from SPEC
            callback (function): When blocking=False, the response will instead be send to the callback function. Expected to accept 2 positional arguments: data, console_output
        
        Returns:
            [Message, string]: If blocking, the response message from the server and what would be printed to console
        """
        event = EventTypes.SV_FUNC_WITH_RETURN if blocking or callback is not None else EventTypes.SV_FUNC

        if command[-1] != '\n':
            command += '\n'

        with self._lock:
            self._sn_counter += 1
            sn = self._sn_counter
            if blocking:
                self._reply_events[sn] = threading.Event()
            elif callback:
                self._reply_events[sn] = callback

            self._screen_print = ""
            self._send_data(event, DataTypes.SV_STRING, "", command, sn=sn)

        if blocking:
            self._reply_events[sn].wait()
            del self._reply_events[sn]
            data = Message(**self._reply_data[sn]._asdict()) # I'm not sure if I have to copy it since I am destroying the dict entry
            del self._reply_data[sn]
            return data, self._screen_print

    def get(self, prop):
        """
        Get a property.

        Attributes:
            prop_name (string): The name of the property

        Returns:
            None if property doesn't exist
        """
        with self._lock:
            self._sn_counter += 1
            sn = self._sn_counter
            self._reply_events[sn] = threading.Event()
            self._send_data(EventTypes.SV_CHAN_READ, 0, prop, sn=sn)
            self._reply_events[sn].wait()
            data = self._reply_data[sn]
            del self._reply_data[sn]
            if data.type == DataTypes.SV_ERROR:
                return None
            return data        

    def set(self, prop, val, wait_for_error=0, dtype=DataTypes.SV_STRING, cols=0, rows=0):
        """
        Set a property.

        Attributes:
            prop_name (string): The name of the property
            value: The value (will be converted to datatype before sending)
            wait_for_error (float): SPEC only sends a message back if the property doesn't exist. Set the number of seconds to wait for an error message (if there is one)

        Returns:
            False if there is an error message with the given time, else True
        """
        val = str(val)
        if dtype != DataTypes.SV_STRING:
            raise Exception("Only strings are currently supported")
        with self._lock:
            self._sn_counter += 1
            sn = self._sn_counter
            self._reply_events[sn] = threading.Event()
            self._send_data(EventTypes.SV_CHAN_SEND, dtype, prop, sn=sn, body=val)
            if self._reply_events[sn].wait(timeout=wait_for_error):
                data = self._reply_data[sn]
                del self._reply_data[sn]
                if data.type == DataTypes.SV_ERROR:
                    return False
            return True

    def motor(self, mne):
        """
        Get the motor as an object

        Parameters:
            mne (string): The mnemonic name of the motor

        Returns:
            (Motor): The motor
        """
        data = self.get("motor/{}/unusable".format(mne))
        if data is None or int(data.body) != 0:
            raise Exception("Motor '{}' couldn't be found or is unusable".format(mne))
        return Motor(mne, self)

    def var(self, name, dtype=str):
        """
        Get the variable as an object

        Parameters:
            name (string): The name of the variable
            dtype (Type): The type of the variable

        Returns:
            (Var): The variable
        """
        return Var(name, self, dtype=dtype)

    def _threaded_reply_listener(self): # For responses on self.sock
        while True:
            res = self._listen(self.sock)
            if res.name == "output/tty": # If screen output from command
                self._screen_print += res.body
                if self._screen_print[:-3] == "> \n": # Don't include 'SPEC> ' in the output
                    self._screen_print = "\n".join(self._screen_print.split("\n")[:-2])
                if len(self._screen_print) > self.MAX_SCREEN_PRINT_LEN: # Don't let it get too long
                    self._screen_print = self._screen_print[-self.MAX_SCREEN_PRINT_LEN:]
            elif res.sn in self._reply_events.keys():
                if (hasattr(threading, "_Event") and isinstance(self._reply_events[res.sn], threading._Event)) or isinstance(self._reply_events[res.sn], threading.Event):
                    self._reply_data[res.sn] = res
                    self._reply_events[res.sn].set()
                else:
                    threading.Thread(target=self._reply_events[res.sn], args=(res,self._screen_print)).start()

    def _threaded_event_listener(self): # For events on self.event_sock
        while True:
            res = self._listen(self.event_sock)
            self._last_event = res
            self._event_available.set()
            if res.name in self._subscriptions.keys():
                for sub in self._subscriptions[res.name]:
                    threading.Thread(target=sub, args=(res,)).start()

    def _send_data(self, event, dtype, prop, body="", sn=None, rows=0, cols=0):
        if dtype != DataTypes.SV_STRING and dtype != 0:
            raise Exception("Only strings are supported")
        with self._lock:
            bb = struct.pack("{}s".format(len(body)), body.encode('ascii'))
            if sn is None:
                self._sn_counter += 1
                sn = self._sn_counter
            self.sock.send(self._create_header(sn, event, dtype, len(bb), prop, rows=rows, cols=cols)+bb)
            return sn

    def _get_counter_names(self):
        """
        Refresh the counter names from the server
        """
        self.counter_names = collections.OrderedDict()
        for i in range(self.var("COUNTERS", dtype=int).value):
            self.counter_names[self.run("cnt_mne({})".format(i))[0].body] = self.run("cnt_name({})".format(i))[0].body 
        return self.counter_names       

    def count(self, time, callback=None, refresh_names=False):
        """
        Counts scalers for the time specified. This function is blocking. The callback function will receive occasional updates during counting and when counting is finished.

        Parameters:
            time (float): The time to count in seconds
            callback (function): Callback function for updates during counting
            refresh_names (boolean): If True, counter names will be refreshed before starting to count. Only necessary if a counter has been added or removed since the script started.

        Returns:
            (OrderedDict): Counter values
        """
        if refresh_names:
            self._get_counter_names()

        countvals = {key: 0.0 for key in self.counter_names.keys()}
        def count_callback(res):
            countvals[res.name.split("/")[1]] = float(res.body)
            if callback:
                threading.Thread(target=callback, args=(countvals,)).start()
        
        for counter in self.counter_names.keys():
            self.subscribe("scaler/{}/value".format(counter), count_callback)

        self.run("count {}".format(time))

        for counter in self.counter_names.keys():
            count_callback(self.get("scaler/{}/value".format(counter))) # Ensure that the final values are read. It says in the docs the callback does it, but it didn't seem reliable
            self.unsubscribe("scaler/{}/value".format(counter), count_callback)

        return countvals

    def stop_counting(self):
        """
        Stop counting immediately. Will also cause .count() call to return if started in different thread.
        """
        self.set("scaler/.all./count", 0)


    #def _pack_body(self, dtype, body, rows=0, cols=0):
    #    if dtype == 0:
    #        dtype = DataTypes.SV_STRING

    #    if dtype == DataTypes.SV_DOUBLE:
    #        return struct.pack("d", body)
    #    if dtype == DataTypes.SV_STRING:
    #        return struct.pack("{}s".format(len(body)), body.encode('ascii'))
    #    if dtype == DataTypes.SV_ERROR: # Shouldn't happen
    #        return body
    #    if dtype == DataTypes.SV_ASSOC:
    #        out = b''
    #        for name, value in body.items():
    #            out += struct.pack("{}s".format(len(str(name))), str(name).encode('ascii'))
    #            out += struct.pack("{}s".format(len(str(value))), str(value).encode('ascii'))
    #        return out
    #    if dtype == DataTypes.SV_ARR_STRING:
    #        return reduce(lambda acc, e : acc+e, [struct.pack("{}s".format(cols), s.encode('ascii')) for s in body])
        
    #    return np.ndarray.flatten(body).astype(DataTypes.NP_TYPES[dtype])

    def abort(self):
        """
        Abort all running commands
        """
        self._send_data(EventTypes.SV_ABORT, 0, "")

    @property
    def motors(self):
        """
        List of all available motor names
        """
        motors = []
        ms = self.var("A").value
        for m in ms.keys():
            motors.append(self.run("motor_name({})".format(m))[0].body)
        return motors
