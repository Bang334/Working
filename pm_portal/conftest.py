# -*- coding: utf-8 -*-
"""Pytest root configuration and path setup."""

import os
import sys

# Ensure pm_portal directory is in sys.path
pm_portal_dir = os.path.abspath(os.path.dirname(__file__))
if pm_portal_dir not in sys.path:
    sys.path.insert(0, pm_portal_dir)
