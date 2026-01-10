#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
import secrets
from argparse import ArgumentParser
from base64 import b64encode, urlsafe_b64encode
from enum import StrEnum
from pathlib import Path


class SecretFormat(StrEnum):
    HEX = "hex"
    BASE64 = "base64"
    URLSAFE = "urlsafe"


parser = ArgumentParser(
    prog="gensecret",
    description="Generate a random secret key.",
)
parser.add_argument(
    "-f",
    "--format",
    type=SecretFormat,
    choices=list(SecretFormat),
    default=SecretFormat.URLSAFE,
    help="Generated secret string type. (default: urlsafe base64)",
    dest="format",
)
parser.add_argument(
    "-o",
    "--out",
    type=Path,
    default=None,
    help="Output file path. If not specified, prints to stdout.",
    dest="output",
)
parser.add_argument(
    "-l",
    "--len",
    type=int,
    default=32,
    help="Length of the generated string, must be divisible by 4. (default: 32).",
    dest="length",
)


def main() -> None:
    args = parser.parse_args()
    n_char = args.length
    secret_fmt: SecretFormat = args.format
    out_path: Path | None = args.output

    # work out the byte length needed to generate the requested character length
    match secret_fmt:
        case SecretFormat.HEX:
            n_bytes = (n_char + 1) // 2  # 1 byte = 2 hex chars
            secret = secrets.token_hex(n_bytes)[:n_char]
        case SecretFormat.BASE64:
            n_bytes = (n_char * 3 + 3) // 4  # 3 bytes = 4 base64 chars
            secret = secrets.token_bytes(n_bytes)
            secret = b64encode(secret).decode("ascii")[:n_char]
        case SecretFormat.URLSAFE:
            n_bytes = (n_char * 3 + 3) // 4  # 3 bytes = 4 base64 chars
            secret = secrets.token_bytes(n_bytes)
            secret = urlsafe_b64encode(secret).decode("ascii")[:n_char]
        case _:
            raise ValueError(f"Unknown or unsupported secret format: {secret_fmt}")

    if out_path:
        if not out_path.exists():
            out_path.write_text(secret)
        else:
            raise FileExistsError(f"Output path {out_path} already exists, will not overwrite.")
    else:
        print(secret)


if __name__ == "__main__":
    main()
