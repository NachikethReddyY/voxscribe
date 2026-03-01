"""Entry point for VoxScribe."""

import sys


def main() -> None:
    """Launch the VoxScribe application."""
    # PySide6 QApplication must be created before any QWidget.
    # We import here to keep module-level side-effect-free.
    from voxscribe.app import VoxScribeApp

    app = VoxScribeApp(sys.argv)
    sys.exit(app.run())


if __name__ == "__main__":
    main()