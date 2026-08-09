"""Run the fisis CLI, so ``python -m fisis`` matches the ``fisis`` console script.

Importing this module runs the CLI and terminates the process via ``SystemExit``.
"""

from .cli import main

raise SystemExit(main())
