#!/usr/bin/env python
import sys
from pathlib import Path
import os
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.core.management import execute_from_command_line
if __name__ == '__main__': execute_from_command_line(sys.argv)
