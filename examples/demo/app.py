"""Tiny deterministic program for the EnvBisect showcase."""

import os
import sys


def main() -> int:
    if os.environ.get("TZ") == "UTC" and os.environ.get("FEATURE_CACHE") == "1":
        print("FAIL: cache and UTC interact in this demo")
        return 1
    print("PASS: demo command succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
