"""Resource root shared by the launcher and extracted UI modules."""
from pathlib import Path
import sys

PROJECT_ROOT = str(Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False)
                   else Path(__file__).resolve().parent.parent)
