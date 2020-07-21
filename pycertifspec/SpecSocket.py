import struct
import collections
import socket
from .DataTypes import DataTypes
from .EventTypes import EventTypes
import time
from functools import reduce

SpecMessage = collections.namedtuple('SpecMessage', 'magic vers size sn sec usec cmd type rows cols len err flags name body')

class SpecSocket(socket.socket):
    """
    Socket like a regular socket.socket, but with extra methods for sending and receiving data from a SPEC server.
    """
    SV_VERSION = 4
    SV_NAME_LEN = 80
    SV_SPEC_MAGIC = 4277009102

    def __init__(self, *args, **kwargs):
        super(SpecSocket, self).__init__(*args, **kwargs)

    def connect_spec(self, host, port=None, port_range=(6510, 6530), ports=[], timeout=0.1):
        """
        Scan ports for a SPEC server and connect when found. If port is already known .connect() can be used instead

        Attributes:
            host (string): The address of the host computer
            port (int): If exact port is known, the port to connect to
            port_range (tuple): Range of ports to scan (end is inclusive)
            ports (list): List of ports to scan
            timeout (float): Time to wait for answer before trying the next port

        Returns:
            (int): The port connected to
        """
        to_scan = ports + list(range(port_range[0], port_range[1]+1))
        if port is not None:
            to_scan.insert(0, port)

        self.settimeout(timeout)
        for p in to_scan:
            try:
                self.connect((host, p))
                self.send_spec(0, EventTypes.SV_HELLO, 0, "pycertifspec")
                res = self.recv_spec()
            except:
                continue

            if res and res.cmd == EventTypes.SV_HELLO_REPLY:
                self.settimeout(None)
                return p
        else:
            self.settimeout(None)
            raise Exception("No SPEC server found")

    def send_spec(self, serial_number, command, data_type, property_name="", body=b'', error=False, flags=[], rows=0, cols=0):
        """
        Send a message to the SPEC server

        Attributes:
            serial_number (int): Serial number of message. Will be the same in server reply
            command (int): The command/event from EventTypes to execute
            data_type (int): The data type of the body
            property_name (string): The name of the property to do work on
            body (bytes): The body of the message
            error (int): Error if != 0
            flags (int): Set a flag (isn't used yet)
            rows (int): The number of rows of the body (if array)
            cols (int): The number of cols of the body (if array)
        """
        if not isinstance(body, bytes):
            raise ValueError("body needs to be bytes")

        header = struct.pack("IiIIIIiiIIIii80s", 
            self.SV_SPEC_MAGIC,
            self.SV_VERSION,
            132,
            serial_number,
            int(time.time()),
            int(time.time()*(10**6)) & 2**32-1,
            command,
            data_type,
            rows,
            cols,
            len(body),
            error,
            reduce(lambda acc, f : acc | f, flags) if flags else 0,
            property_name.encode("ascii")
        )
        data = header + body
        self.send(data)

    def recv_spec(self):
        """
        Receive a SPEC message

        Returns:
            (Message): The message from the SPEC server
        """
        head1 = self.recv(12) # Read until size so we know how long the header will be
        magic, vers, size = struct.unpack("IiI", head1)

        if magic != self.SV_SPEC_MAGIC:
            raise ValueError("Response didn't contain the correct SPEC magic number")

        if vers < 4:
            raise Exception("Server respondend with protocol version {}. Need at least 4".format(vers))

        # Receive the rest of the header
        head2 = self.recv(size-12)            
        res = SpecMessage(magic, vers, size, *struct.unpack("IIIiiIIIii{}x80s".format(size-132), head2), body=None)
        res = res._replace(name=res.name.decode("utf-8").rstrip('\x00')) # Convert name to string

        # Read the body in chunks of 4096 bits. Larger will cause the program to fail
        body = b''
        bleft = res.len
        while bleft > 0:
            body += self.recv(min(4096, bleft))
            bleft -= 4096

        if res.type == DataTypes.SV_STRING:
            res = res._replace(body=body.decode("utf-8").rstrip('\x00'))
        else:
            res = res._replace(body=body)

        return res
