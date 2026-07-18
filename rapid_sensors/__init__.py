"""rapid_sensors - fast readers for RAPID and BDS fish-passage sensors.

Library use::

    import rapid_sensors

    rec = rapid_sensors.read("B38-0928141315.IMP")
    rec.data                       # pandas DataFrame, physical units
    rec.to_csv("out.csv")

Shell use::

    rapid-convert my_folder --plot
"""

from .formats import FORMATS, DetectionError, PacketFormat, detect_format
from .readers import Recording, read

__version__ = "1.0.0"

__all__ = ["read", "Recording", "detect_format", "PacketFormat",
           "FORMATS", "DetectionError", "__version__"]
