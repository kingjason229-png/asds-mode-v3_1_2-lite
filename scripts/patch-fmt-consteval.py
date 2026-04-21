#!/usr/bin/env python3
"""
Patch fmt 11.0.2 for Apple Clang 21 C++20 consteval incompatibility.

Symptom: xcodebuild fails with:
  error: call to consteval function is not a constant expression

Root cause: fmt 11.0.2 uses C++20 consteval which Apple Clang 21 doesn't support.

Fix: Replace FMT_STRING() calls with plain format strings.
"""
import sys
import re

def patch_fmt_file(filepath: str) -> bool:
    with open(filepath, 'r') as f:
        content = f.read()

    original = content

    # Patterns to replace (old → new)
    replacements = [
        # format-inl.h line 59
        (r'fmt::format_to\(it, FMT_STRING\("\{\}\{\}"\), message, SEP\);',
         'fmt::format_to(it, "{}{}", message, SEP);'),
        # format-inl.h line 60
        (r'fmt::format_to\(it, FMT_STRING\("\{\}\{\}"\), ERROR_STR, error_code\);',
         'fmt::format_to(it, "{}{}", ERROR_STR, error_code);'),
        # format-inl.h line ~1387
        (r'out = fmt::format_to\(out, FMT_STRING\("\{:x\}"\), value\);',
         'out = fmt::format_to(out, "{:x}", value);'),
        # format-inl.h line ~1391
        (r'out = fmt::format_to\(out, FMT_STRING\("\{:08x\}"\), value\);',
         'out = fmt::format_to(out, "{:08x}", value);'),
        # format-inl.h line ~1394
        (r'out = fmt::format_to\(out, FMT_STRING\("p\{\}"\),',
         'out = fmt::format_to(out, "p{}",'),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    if content == original:
        print(f"  No changes needed in {filepath}")
        return True

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"  Patched {filepath}")
    return True


def main():
    ios_pods_fmt = "ios/Pods/fmt/include/fmt/format-inl.h"

    try:
        patch_fmt_file(ios_pods_fmt)
        print("fmt patch applied successfully")
    except FileNotFoundError:
        print(f"  File not found: {ios_pods_fmt} (already patched or not found)")
        sys.exit(0)
    except Exception as e:
        print(f"  Patch failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
