#!/usr/bin/env python3
"""S.A.R.A. Sound Forge local studio server — loads full module from part0+part1."""
from pathlib import Path
_p = Path(__file__).resolve().parent
_code = (_p / "studio_server.part0").read_text() + (_p / "studio_server.part1").read_text()
exec(compile(_code, str(_p / "studio_server.py"), "exec"), globals())
