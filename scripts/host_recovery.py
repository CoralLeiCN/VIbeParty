"""Show the local Word by Word recovery code on the host laptop only."""

from backend.shared.config import Settings


def main() -> None:
    settings = Settings()
    if not settings.local_mode:
        raise SystemExit("Use the configured host passcode to recover host access.")
    path = settings.media_dir("word-by-word").parent / "host-recovery.txt"
    try:
        code = path.read_text().strip()
    except FileNotFoundError:
        raise SystemExit(
            "No local Word by Word recovery code. Check the running project and settings."
        )
    print(code)


if __name__ == "__main__":
    main()
