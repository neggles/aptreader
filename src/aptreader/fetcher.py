"""Repository fetching and distribution discovery for APT repositories."""

import gzip
import logging
from enum import Enum
from html.parser import HTMLParser
from os import utime
from pathlib import Path
from collections.abc import Iterator
from urllib.parse import urljoin, urlparse

import aiofiles
import aiogzip
import httpx
from dateutil.parser import parse as parse_date
from debian import deb822

from aptreader.constants import REPOS_DIR
from aptreader.utils import try_parse_date

logger = logging.getLogger(__name__)


class _DirectoryListingParser(HTMLParser):
    """Extract directory names from a simple HTML index."""

    def __init__(self):
        super().__init__()
        self._entries: list[str] = []

    def handle_starttag(self, tag, attrs):  # noqa: D401 - HTMLParser hook
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href", "")
        if not href or href.startswith("?"):
            return
        if href in {"../", "/"}:
            return
        if not href.endswith("/"):
            return
        name = href.strip("/")
        if name and name not in self._entries:
            self._entries.append(name)

    def get_entries(self) -> list[str]:
        """Return discovered directory names preserving server order."""
        return list(self._entries)


def url_to_local_path(url: str) -> Path:
    """Convert a repository URL to a local file path that mirrors the source structure.

    Args:
        url: The full URL to a file (e.g., https://archive.kylinos.cn/dists/10.0/Release)

    Returns:
        Path relative to REPOS_DIR (e.g., archive.kylinos.cn/dists/10.0/Release)

    Examples:
        >>> url_to_local_path("https://archive.ubuntu.com/ubuntu/dists/jammy/Release")
        PosixPath('archive.ubuntu.com/ubuntu/dists/jammy/Release')
    """
    parsed = urlparse(url)
    # Combine netloc (domain) and path, strip leading slash
    local_path = Path(parsed.netloc) / parsed.path.lstrip("/")
    return REPOS_DIR / local_path


def get_repo_base_path(repo_url: str) -> Path:
    """Get the base directory for a repository's cached files.

    Args:
        repo_url: Base URL of the repository (e.g., https://archive.ubuntu.com/ubuntu/)

    Returns:
        Base path for this repository in the cache

    Examples:
        >>> get_repo_base_path("https://archive.ubuntu.com/ubuntu/")
        PosixPath('data/repos/archive.ubuntu.com/ubuntu')
    """
    parsed = urlparse(repo_url)
    return REPOS_DIR / parsed.netloc / parsed.path.strip("/")


class SkipMode(str, Enum):
    """File download skip modes.
    FAST: Skip download if local file exists.
    CHECK: Check Last-Modified and Content-Length headers to decide.
    NONE: Always download.
    """

    FAST = "fast"
    CHECK = "check"
    NONE = "none"


async def download_file(
    url: str,
    output_path: Path,
    skip_mode: SkipMode = SkipMode.CHECK,
) -> bool:
    """Download a file from a URL to a local path.

    Args:
        url: The URL to download from
        output_path: Where to save the downloaded file
        skip_mode: The mode for skipping downloads if the file exists

    Returns:
        True if successful, False if download failed
    """
    try:
        existing = output_path.is_file()
        if existing and skip_mode == SkipMode.FAST:
            logger.debug(f"Skipping download, file already exists: {output_path}")
            return True

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            if existing and skip_mode != SkipMode.NONE:
                try:
                    response = await client.head(url)
                    response.raise_for_status()
                    if last_modified := try_parse_date(response.headers.get("last-modified")):
                        # allow a second for fs granularity
                        if last_modified.timestamp() <= output_path.stat().st_mtime + 1:
                            logger.debug(f"Skipping download, local file mtime matches: {output_path}")
                            return True

                    elif remote_size := response.headers.get("content-length"):
                        if int(remote_size) == output_path.stat().st_size:
                            logger.debug(f"Skipping download, local file size matches remote: {output_path}")
                            return True

                except Exception as e:
                    logger.warning(f"Unable to check remote mtime or size for {url}: {e}")

            response = await client.get(url)
            response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            if last_modified := response.headers.get("last-modified"):
                remote_ts = parse_date(last_modified).timestamp()
                utime(output_path, (remote_ts, remote_ts))

        logger.debug(f"Downloaded {url} to {output_path}")
        return True

    except httpx.HTTPStatusError as e:
        msg = f"Failed to download {url}: {e}"
        if e.response.status_code == 404:
            logger.debug(msg)
        else:
            logger.warning(msg)
        return False
    except Exception as e:
        logger.exception(f"Unexpected error downloading {url}: {e}")
        return False


async def fetch_release_file(
    repo_url: str,
    dist: str,
) -> tuple[Path | None, dict | None]:
    """Download and parse a Release file for a distribution.

    Args:
        repo_url: Base URL of the repository
        dist: Distribution name (e.g., "jammy")

    Returns:
        Tuple of (local_path, parsed_data) or (None, None) if failed
    """
    if not repo_url.endswith("/"):
        repo_url += "/"

    release_url = urljoin(repo_url, f"dists/{dist}/Release")
    local_path = url_to_local_path(release_url)

    # Download the file
    success = await download_file(release_url, local_path)
    if not success:
        return None, None

    # Parse the Release file
    try:
        release_text = local_path.read_text(encoding="utf-8")
        release_data = deb822.Release(release_text)

        # Convert to dict for easier access
        parsed = dict(release_data)
        logger.debug(f"Parsed Release file for {dist}: {parsed.get('Codename', dist)}")
        return local_path, parsed

    except Exception as e:
        logger.error(f"Failed to parse Release file for {dist}: {e}")
        return local_path, None


async def discover_distributions(repo_url: str) -> list[str]:
    """Discover available distributions at a repository.

    Args:
        repo_url: Base URL of the repository (e.g., https://archive.ubuntu.com/ubuntu/)

    Returns:
        List of distribution names found (e.g., ["jammy", "focal", "bookworm"])
    """

    if not repo_url.endswith("/"):
        repo_url += "/"

    listing_url = urljoin(repo_url, "dists/")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(listing_url)
        response.raise_for_status()
        parser = _DirectoryListingParser()
        parser.feed(response.text)

    entries = parser.get_entries()
    if not entries:
        candidates: list[str] = []
        for line in response.text.splitlines():
            token = line.strip()
            if not token or token.startswith(".."):
                continue
            if token.endswith("/"):
                candidates.append(token.strip("/"))
        if candidates:
            entries = list(dict.fromkeys(candidates))
    num_found = len(entries)
    logger.info(f"Discovered {num_found} distributions at {repo_url}")
    return entries


async def fetch_distributions(
    repo_url: str,
    distributions: list[str] | None = None,
):
    """Discover and fetch Release files for all distributions at a repository.

    Args:
        repo_url: Base URL of the repository

    Returns:
        List of tuples: (dist_name, local_path, parsed_data)
    """
    if distributions is None:
        distributions = await discover_distributions(repo_url)

    for dist in distributions:
        try:
            local_path, parsed_data = await fetch_release_file(repo_url, dist)
            if local_path and parsed_data:
                yield (dist, local_path, parsed_data)
        except Exception as e:
            logger.error(f"Error fetching Release file for distribution '{dist}': {e}")
            continue


def build_packages_url(
    repo_url: str, dist: str, component: str, architecture: str, suffix: str = "Packages.gz"
) -> str:
    """Construct a Packages index URL for a component + architecture."""

    repo_prefix = repo_url if repo_url.endswith("/") else f"{repo_url}/"
    rel_path = f"dists/{dist}/{component}/binary-{architecture}/{suffix}"
    return urljoin(repo_prefix, rel_path)


async def download_packages_index(
    repo_url: str,
    dist: str,
    component: str,
    architecture: str,
    skip_mode: SkipMode = SkipMode.CHECK,
) -> tuple[str, Path] | None:
    """Download Packages[.gz] for the given component/architecture tuple."""

    for suffix in ("Packages.gz", "Packages"):
        packages_url = build_packages_url(repo_url, dist, component, architecture, suffix)
        local_path = url_to_local_path(packages_url)
        success = await download_file(packages_url, local_path, skip_mode=skip_mode)
        if success:
            return packages_url, local_path
    return None


def iter_packages_entries(local_path: Path) -> Iterator[dict]:
    """Stream package entries from a Packages or Packages.gz file."""

    def _open_text_stream():
        if local_path.suffix == ".gz":
            try:
                return gzip.open(local_path, "rt", encoding="utf-8", errors="ignore")
            except OSError:
                logger.warning("Falling back to plain-text read for %s", local_path)
        return local_path.open("rt", encoding="utf-8", errors="ignore")

    with _open_text_stream() as handle:
        for paragraph in deb822.Packages.iter_paragraphs(handle):
            yield dict(paragraph)


async def iter_packages_entries_async(local_path: Path):
    """Asynchronously stream package entries from a Packages or Packages.gz file."""

    async def _open_text_stream():
        if local_path.suffix == ".gz":
            try:
                async with aiogzip.AsyncGzipTextFile(local_path, encoding="utf-8", errors="ignore") as f:
                    async for line in f:
                        yield line
                return
            except OSError:
                logger.info("Falling back to plain-text read for %s", local_path, stacklevel=2)
        async with aiofiles.open(local_path, encoding="utf-8", errors="ignore") as f:
            async for line in f:
                yield line

    handle = _open_text_stream()
    paragraph_lines = []
    async for line in handle:
        if line.strip() == "":
            if paragraph_lines:
                paragraph_text = "".join(paragraph_lines)
                paragraph = deb822.Deb822(paragraph_text.splitlines())
                yield dict(paragraph)
                paragraph_lines = []
        else:
            paragraph_lines.append(line)
    if paragraph_lines:
        paragraph_text = "".join(paragraph_lines)
        paragraph = deb822.Deb822(paragraph_text.splitlines())
        yield dict(paragraph)
