from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

# Minimum majors whose JavaScript runtime is Node 24 compatible for the
# first-party Actions used by this repository.
MINIMUM_MAJORS = {
    "actions/checkout": 7,
    "actions/upload-artifact": 7,
    "actions/setup-python": 7,
    "actions/setup-node": 6,
}

USES_RE = re.compile(
    r"^\s*-?\s*uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@v(\d+)(?:\b|\.)",
    re.MULTILINE,
)


def main() -> None:
    violations: list[str] = []
    checked: list[str] = []

    for path in sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        for action, major_text in USES_RE.findall(text):
            if action not in MINIMUM_MAJORS:
                continue
            major = int(major_text)
            minimum = MINIMUM_MAJORS[action]
            checked.append(f"{path.relative_to(ROOT)}: {action}@v{major}")
            if major < minimum:
                violations.append(
                    f"{path.relative_to(ROOT)} uses {action}@v{major}; "
                    f"minimum allowed major is v{minimum} (Node 24 runtime)."
                )

    if not checked:
        raise SystemExit("No monitored first-party GitHub Actions were found.")

    if violations:
        print("GitHub Actions runtime compatibility check FAILED:")
        for item in violations:
            print(f"- {item}")
        raise SystemExit(1)

    print(
        "GITHUB ACTIONS RUNTIME CHECK PASSED: "
        f"{len(checked)} monitored action references are Node 24 compatible"
    )
    for item in checked:
        print(f"- {item}")


if __name__ == "__main__":
    main()
