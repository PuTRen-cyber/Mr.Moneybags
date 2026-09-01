import sys

from mr_moneybags.cli import main


if __name__ == "__main__":
    raise SystemExit(main(debug='--debug' in sys.argv[1:]))
