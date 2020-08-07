# pycertifspec

## Installation

```bash
pip install git+https://github.com/SEBv15/pycertifspec.git
```

## Basic Usage

Start SPEC with `-S 6510` flag (or any other port number)

```python
from pycertifspec import Client, Motor, Var, ArrayVar
from pycertifspec.bluesky import Motor as BlueskyMotor
from pycertifspec.bluesky import Counter as BlueskyCounter

# Client
client = Client(host="localhost", port=6510)

# Var
A = client.var("A") # dict of motor positions
# Currently all variable types (string, int, arrays, etc.) can be read
# and written, although you have to be careful when writing arrays
print(A.value)

#ArrayVar
client.run("array test[10][10]") # Create array variable
av = ArrayVar("test", client)
av[5][2] = 5 # this gets pushed to SPEC
print(av[5])

print("SPEC has {} counters".format(client.var("COUNTERS", dtype=int).value))

# Motor
motor = client.motor("m0")

print("Motor {} is currently at position {}".format(motor.name, motor.position))

def print_position_update(spec_response):
    print("Motor at {}".format(float(spec_response.body)))

motor.subscribe("position", print_position_update)

# Properties are automatically updated and passed to SPEC when set
motor.step_size = 0.1

print(motor.position)
motor.moveto(100)
print(motor.position)
motor.move(-10.3)
print(motor.position)

### Bluesky
from bluesky import RunEngine
from bluesky.plans import scan
RE = RunEngine({})

# This motor should be compatible with bluesky
m = BlueskyMotor(client.motor("m0"))

# And this detector counts all the scalers like the `ct [seconds]` macro
det = BlueskyCounter(client, name="SPEC", visualize_counters=["sec"])

RE(scan([det], m, -1, 1, 10))
```
