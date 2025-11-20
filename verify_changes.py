#!/usr/bin/env python3
"""Verify that the latest changes are present in the code."""

import sys
import os
import inspect

# Add winconsole to path
sys.path.insert(0, os.path.dirname(__file__))

print("=== Verifying Latest Changes ===\n")

# Test 1: Check if _warn_tui_command exists
print("1. Checking if _warn_tui_command method exists...")
try:
    from winconsole.main_window import SessionDetailWidget

    if hasattr(SessionDetailWidget, '_warn_tui_command'):
        print("  ✓ _warn_tui_command method found")

        # Get the method source
        method = getattr(SessionDetailWidget, '_warn_tui_command')
        source = inspect.getsource(method)

        # Check if it contains the expected warning text
        if "警告：检测到 TUI 程序" in source:
            print("  ✓ Method contains correct warning message")
        else:
            print("  ✗ Method exists but warning message is old")
    else:
        print("  ✗ _warn_tui_command method NOT found (old code)")
except Exception as e:
    print(f"  ✗ Error checking: {e}")

# Test 2: Check if _handle_pre_send has the new three-button dialog
print("\n2. Checking if _handle_pre_send has three-button dialog...")
try:
    from winconsole.main_window import SessionDetailWidget

    method = getattr(SessionDetailWidget, '_handle_pre_send')
    source = inspect.getsource(method)

    # Check for key indicators of the new code
    checks = [
        ("打开交互式 Shell" in source, "Has 'Open Interactive Shell' button"),
        ("run_cmd_btn" in source, "Has run_cmd_btn variable"),
        ("open_shell_btn" in source, "Has open_shell_btn variable"),
        ("try_here_btn" in source, "Has try_here_btn variable"),
        ("bash -l -c" in source, "Uses bash -l -c for login shell"),
    ]

    all_passed = True
    for check, description in checks:
        if check:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description}")
            all_passed = False

    if not all_passed:
        print("\n  ⚠️  Some checks failed - you may be running old code!")

except Exception as e:
    print(f"  ✗ Error checking: {e}")

# Test 3: Check utils.py for updated open_in_external_terminal
print("\n3. Checking if open_in_external_terminal is updated...")
try:
    from winconsole.utils import open_in_external_terminal

    source = inspect.getsource(open_in_external_terminal)

    checks = [
        ("wt_cmd = ['wt.exe', '-d', cwd, cmd] + args" in source,
         "Correct Windows Terminal command format"),
        ("LOG.info(f\"Launching Windows Terminal:" in source,
         "Has debug logging"),
    ]

    for check, description in checks:
        if check:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description}")

except Exception as e:
    print(f"  ✗ Error checking: {e}")

print("\n" + "="*50)
print("\nIf all checks passed, the latest code is loaded!")
print("If some checks failed, try:")
print("  1. Close WinConsole completely")
print("  2. Clear cache: find winconsole -name '*.pyc' -delete")
print("  3. Restart WinConsole")
print("\n" + "="*50)
