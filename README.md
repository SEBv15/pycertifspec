# pycertifspec

## Installation

```bash
pip install git+https://github.com/SEBv15/pycertifspec.git
```

## Basic Usage

Start SPEC with `-S 6510` flag (or any other port number)

```python
from pycertifspec import Client, Motor, Var

# Client
client = Client(host="localhost", port=6510)

# Var
A = client.var("A")
# Currently all variable types (string, int, arrays, etc.) can be read 
# and formatted, but only non-arrays can be written
print(A.value)

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
```