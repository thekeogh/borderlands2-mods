"""Build a reproducible .sdkmod ZIP from the source folder."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "op_inflation_buster"
ARTIFACT = ROOT / "dist" / "op_inflation_buster.sdkmod"


def main() -> None:
    ARTIFACT.parent.mkdir(exist_ok=True)
    with ZipFile(ARTIFACT, "w", compression=ZIP_DEFLATED) as archive:
        for source in sorted(SOURCE.rglob("*")):
            if source.is_file() and source.suffix != ".pyc":
                archive.write(source, source.relative_to(ROOT))
    print(ARTIFACT)


if __name__ == "__main__":
    main()
