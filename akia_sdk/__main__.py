"""Allow ``python -m akia_sdk`` to behave like the headless CLI."""

from akia_sdk.cli import main

raise SystemExit(main())
