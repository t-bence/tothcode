---
name: python-docstring
description: Defines how to write Python docstrings
---

# python-docstring

Always write docstrings for functions, classes and modules. Use the formats below.

## Function

```python
def calculate_velocity(distance, time):
    """Calculates the average velocity of an object.

    Args:
        distance (float): The total distance traveled in meters.
        time (float): The total time taken in seconds. Must be non-zero.

    Returns:
        float: The average velocity in meters per second (m/s).

    Raises:
        ValueError: If time is less than or equal to zero.
    """
    if time <= 0:
        raise ValueError("Time must be a positive value.")
    return distance / time
```

## Class

```python
class Satellite:
    """Represents a communication satellite in orbit.

    Attributes:
        name (str): The unique identifier for the satellite.
        altitude (float): Current altitude above sea level in kilometers.
        is_active (bool): The operational status of the satellite.
    """

    def __init__(self, name, altitude):
        """Initializes the Satellite with name and altitude.

        Args:
            name (str): The name of the satellite.
            altitude (float): Starting altitude in kilometers.
        """
        self.name = name
        self.altitude = altitude
        self.is_active = True

    def toggle_status(self):
        """Switches the operational status of the satellite."""
        self.is_active = not self.is_active
```