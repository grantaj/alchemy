from alchemy.config import load_settings
from alchemy.services import run_checks


def main() -> None:
    settings = load_settings()
    checks = run_checks(settings)

    for check in checks:
        status = "OK" if check.ok else "FAIL"
        print(f"[{status}] {check.name}: {check.detail}")
        if check.fix:
            print(f"      Fix: {check.fix}")

    if not all(check.ok for check in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
