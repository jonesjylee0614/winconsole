#!/usr/bin/env python3
"""Test external terminal launch logic."""

import sys
import os

# Add winconsole to path
sys.path.insert(0, os.path.dirname(__file__))

from winconsole.utils import is_tui_program, open_in_external_terminal

print("=== Testing TUI Detection and External Terminal Launch ===\n")

# Test 1: TUI Detection
print("1. Testing TUI detection:")
test_commands = ["codex", "vim", "ls", "git"]
for cmd in test_commands:
    result = is_tui_program(cmd)
    print(f"  {cmd}: {result}")

print("\n2. Testing external terminal launch:")
print("  Attempting to launch WSL with codex command...")

# Test the actual launch with WSL
cmd = "wsl"
args = ["bash", "-l", "-c", "echo 'Testing: codex would run here'"]
cwd = os.getcwd()

print(f"\n  Command: {cmd}")
print(f"  Args: {args}")
print(f"  CWD: {cwd}")

# Construct what would be sent to Windows Terminal
wt_cmd = ['wt.exe', '-d', cwd, cmd] + args
print(f"\n  Windows Terminal command:")
print(f"  {' '.join(wt_cmd)}")

print("\n3. Attempting actual launch...")
success = open_in_external_terminal(cmd, args, cwd)
print(f"  Launch result: {success}")

if success:
    print("\n✓ External terminal should have opened!")
    print("  Check if a Windows Terminal window appeared.")
else:
    print("\n✗ Failed to launch external terminal")
    print("  This might be expected if wt.exe is not in PATH")

print("\n=== Test complete ===")
