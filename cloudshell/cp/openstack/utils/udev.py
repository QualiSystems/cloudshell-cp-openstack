from pathlib import Path


def get_udev_rules() -> str:
    file_path = Path(__file__).parent / "udev_rules.sh"
    with file_path.open() as f:
        data = f.read()
    return data
