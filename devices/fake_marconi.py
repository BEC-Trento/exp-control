#!/usr/bin/python3
import argparse

p = argparse.ArgumentParser()
p.add_argument('--freq', type=float)
p.add_argument('--amp', type=float)

args = p.parse_args()

hello = "Fake marconi script running"
if args.freq is not None:
    hello += f" with set freq {args.freq:.9f}"
if args.amp is not None:
    hello += f" with set amp {args.amp:.3f}"

print(hello)
