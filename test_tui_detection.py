#!/usr/bin/env python3
"""Test TUI program detection."""

from winconsole.utils import is_tui_program

# Test cases
test_commands = [
    # TUI programs (should return True)
    ("codex", True),
    ("vim", True),
    ("nvim", True),
    ("htop", True),
    ("ranger", True),
    ("tmux", True),
    ("lazygit", True),

    # Regular commands (should return False)
    ("ls", False),
    ("cat", False),
    ("echo", False),
    ("git", False),
    ("python", False),
    ("node", False),

    # Edge cases
    ("vim.exe", True),  # Windows executable
    ("VIM", True),      # Case insensitive
    ("HTOP", True),     # Case insensitive
    ("/usr/bin/vim", True),  # Full path
]

print("Testing TUI detection:\n")
all_passed = True

for cmd, expected in test_commands:
    result = is_tui_program(cmd)
    status = "✓" if result == expected else "✗"

    if result != expected:
        all_passed = False

    print(f"{status} {cmd:20s} -> {str(result):5s} (expected {expected})")

print("\n" + "="*50)
if all_passed:
    print("✓ All tests passed!")
else:
    print("✗ Some tests failed!")
    exit(1)
