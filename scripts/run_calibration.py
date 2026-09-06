#!/usr/bin/env python3
"""Anten kazanc paterni kalibrasyonunu baslatir. Ayrintili kullanim icin -h."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wifidf.calibrate import main

if __name__ == "__main__":
    main()
