"""Repository downloader and parser for APT repositories."""

import gzip
import hashlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from debian import deb822

from aptreader.models import Component, Package, Release, Repository


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


class RepositoryManager:
    """Manages downloading and parsing APT repositories."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize the repository manager.

        Args:
            cache_dir: Directory to cache downloaded repository files. Defaults to ~/.cache/aptreader
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "aptreader"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_repo_cache_dir(self, repo_url: str) -> Path:
        """Get the cache directory for a specific repository.

        Args:
            repo_url: The repository URL

        Returns:
            Path to the repository-specific cache directory
        """
        # Create a unique directory name based on the repo URL
        url_hash = hashlib.sha256(repo_url.encode()).hexdigest()[:16]
        parsed = urlparse(repo_url)
        safe_name = f"{parsed.netloc}_{parsed.path}".replace("/", "_").replace(":", "_")
        repo_dir = self.cache_dir / f"{safe_name}_{url_hash}"
        repo_dir.mkdir(parents=True, exist_ok=True)
        return repo_dir

    async def _download_file(self, url: str, output_path: Path) -> None:
        """Download a file from a URL to a local path.

        Args:
            url: The URL to download from
            output_path: Where to save the downloaded file
        """
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            output_path.write_bytes(response.content)

    async def _discover_distributions(self, repo_url: str) -> list[str]:
        """Return distribution names exposed under repo_url/dists/."""
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

        if not entries:
            raise ValueError(f"No distributions found at {listing_url}")

        return entries

    async def _load_release(
        self,
        repo_url: str,
        dist_name: str,
        component_filter: list[str] | None,
        architecture_filter: list[str] | None,
        cache_dir: Path,
    ) -> Release:
        """Download release metadata and packages for a single distribution."""

        dist_name = dist_name.strip().strip("/")
        dist_path = f"dists/{dist_name}"
        release_url = urljoin(repo_url, f"{dist_path}/Release")
        release_path = cache_dir / f"{dist_path.replace('/', '_')}_Release"

        try:
            await self._download_file(release_url, release_path)
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to download Release file from {release_url}") from e

        release_content = release_path.read_text(encoding="utf-8")
        release_data = next(deb822.Release.iter_paragraphs(release_content))

        release = Release(
            name=dist_name,
            codename=release_data.get("Codename"),
            suite=release_data.get("Suite"),
            version=release_data.get("Version"),
            architectures=release_data.get("Architectures", "").split(),
            available_components=release_data.get("Components", "").split(),
        )

        declared_components = release.available_components
        if component_filter:
            filter_set = [comp for comp in component_filter if comp]
            target_components = [comp for comp in declared_components if comp in filter_set]
            if not target_components:
                target_components = filter_set or ["main"]
        else:
            target_components = declared_components or ["main"]

        filtered_architectures = [arch for arch in release.architectures if arch not in {"all", "source"}]
        if architecture_filter:
            filter_arches = [arch for arch in architecture_filter if arch]
            target_arches = [arch for arch in filtered_architectures if arch in filter_arches]
            if not target_arches:
                target_arches = [arch for arch in filter_arches if arch not in {"all", "source"}]
        else:
            target_arches = filtered_architectures

        if not target_arches:
            target_arches = filtered_architectures

        for comp_name in target_components:
            component = Component(name=comp_name)

            for arch in target_arches:
                if not arch:
                    continue

                packages_url = urljoin(repo_url, f"{dist_path}/{comp_name}/binary-{arch}/Packages.gz")
                packages_path = (
                    cache_dir / f"{dist_path.replace('/', '_')}{comp_name}_binary-{arch}_Packages.gz"
                )

                try:
                    await self._download_file(packages_url, packages_path)
                    packages = self._parse_packages_file(packages_path)
                    component.packages.update(packages)
                except httpx.HTTPError:
                    packages_url = urljoin(repo_url, f"{dist_path}/{comp_name}/binary-{arch}/Packages")
                    packages_path = (
                        cache_dir / f"{dist_path.replace('/', '_')}{comp_name}_binary-{arch}_Packages"
                    )
                    try:
                        await self._download_file(packages_url, packages_path)
                        packages = self._parse_packages_file(packages_path)
                        component.packages.update(packages)
                    except httpx.HTTPError:
                        continue

            if component.packages:
                release.components[comp_name] = component

        return release

    def _parse_packages_file(self, packages_path: Path) -> dict[str, Package]:
        """Parse a Packages file into Package objects.

        Args:
            packages_path: Path to the Packages file (may be gzipped)

        Returns:
            Dictionary mapping package names to Package objects
        """
        packages = {}

        # Handle gzipped files
        if packages_path.suffix == ".gz":
            with gzip.open(packages_path, "rt", encoding="utf-8") as f:
                content = f.read()
        else:
            content = packages_path.read_text(encoding="utf-8")

        # Parse using python-debian
        for pkg_data in deb822.Packages.iter_paragraphs(content):
            # Extract dependencies
            depends = []
            if "Depends" in pkg_data:
                depends = [dep.strip() for dep in pkg_data["Depends"].split(",")]

            recommends = []
            if "Recommends" in pkg_data:
                recommends = [dep.strip() for dep in pkg_data["Recommends"].split(",")]

            suggests = []
            if "Suggests" in pkg_data:
                suggests = [dep.strip() for dep in pkg_data["Suggests"].split(",")]

            conflicts = []
            if "Conflicts" in pkg_data:
                conflicts = [dep.strip() for dep in pkg_data["Conflicts"].split(",")]

            package = Package(
                name=pkg_data.get("Package", ""),
                version=pkg_data.get("Version", ""),
                architecture=pkg_data.get("Architecture", ""),
                filename=pkg_data.get("Filename", ""),
                size=int(pkg_data.get("Size", 0)),
                sha256=pkg_data.get("SHA256"),
                description=pkg_data.get("Description"),
                depends=depends,
                recommends=recommends,
                suggests=suggests,
                conflicts=conflicts,
                section=pkg_data.get("Section"),
                priority=pkg_data.get("Priority"),
                maintainer=pkg_data.get("Maintainer"),
                homepage=pkg_data.get("Homepage"),
            )
            packages[package.name] = package

        return packages

    async def load_repository(
        self,
        repo_url: str,
        dists: list[str] | None = None,
        components: list[str] | None = None,
        architectures: list[str] | None = None,
    ) -> Repository:
        """Load and parse an APT repository.

        Args:
            repo_url: The base URL of the APT repository
            dists: Specific distributions to load. If None, all available dists are discovered automatically.
            components: Optional list of components to prioritize/filter (e.g., ['main', 'universe']).
            architectures: Optional list of architectures to load (e.g., ['amd64', 'arm64']).

        Returns:
            A Repository object with parsed data
        """
        if not repo_url.endswith("/"):
            repo_url += "/"

        # Create repository object
        repo = Repository(url=repo_url, name=urlparse(repo_url).netloc)
        cache_dir = self._get_repo_cache_dir(repo_url)

        discovered_dists = dists or await self._discover_distributions(repo_url)

        errors: list[str] = []
        for dist_name in discovered_dists:
            dist_cache_dir = cache_dir / dist_name.replace("/", "_")
            dist_cache_dir.mkdir(parents=True, exist_ok=True)
            try:
                release = await self._load_release(
                    repo_url,
                    dist_name,
                    component_filter=components,
                    architecture_filter=architectures,
                    cache_dir=dist_cache_dir,
                )
            except ValueError as exc:
                errors.append(str(exc))
                continue

            repo.releases[release.name] = release

        if not repo.releases:
            if errors:
                raise ValueError("Unable to load any distributions: " + "; ".join(errors))
            raise ValueError("Unable to load any distributions from repository")

        return repo
