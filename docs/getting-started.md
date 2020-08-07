# Getting Started

## Installation

With python `>=3.4`
```
pip install git+https://github.com/SEBv15/pycertifspec.git
```

## Usage

### Starting SPEC

The library needs a SPEC session to communicate with. To start SPEC in server mode simply start the shell with the `-S [port]` flag. When the port is not specified, one off `6510 - 6530` will be used.

Example:
```
spec -S 6510
```
This also works for specfe:
```
specfe fourc -S
```
More on the [official documentation](https://www.certif.com/spec_help/server.html#starting-the-server)

### Connecting to SPEC

Connections to SPEC are made with the [Client](https://pycertifspec.readthedocs.io/en/latest/docs/api-documentation/client/) class
```python
from pycertifspec import Client

client = Client()
```
This will create a connection to the SPEC server and use `localhost` and ports `6510-6530` by default. 

### Running SPEC console commands

Now you can run commands like in a regular SPEC console, but from python

For example to list all defined variables:
```python
print(client.run("syms")[1])
```

The [`Client.run`](https://pycertifspec.readthedocs.io/en/latest/docs/api-documentation/client/#run) method returns the [response from the SPEC server](https://pycertifspec.readthedocs.io/en/latest/docs/api-documentation/specsocket/#specmessage) as well as the console output as a tuple

### Controlling motors

```python
motor = client.motor(client.motors[0])

print(motor.position)
motor.move(-10)
print(motor.position)
```

This will take the first motor it finds and move it `-10` units

### Reading and writing variables

```python
print("Motor positions:", client.var("A").value)

client.run("array test[10][10]") # Create array variable
av = client.var("test")
av[5][2] = 5 # this gets pushed to SPEC
print(av[5])
```

### Taking data

```python
print(client.count(30))
```

This will take data for 30 seconds and return the values