#!/usr/bin/env python3
"""Canli yon-bulma dashboard'unu baslatir. Root/monitor-mode arayuzleri gerektirir."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wifidf.dashboard import run_dashboard

if __name__ == "__main__":
    run_dashboard()
