"""Repository downloader and parser for APT repositories."""

import gzip
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from debian import deb822

from .models import Component, Package, Release, Repository


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
        safe_name = f"{parsed.netloc}{parsed.path}".replace("/", "_").replace(":", "_")
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
        self, repo_url: str, dist: str = "dists/", components: list[str] | None = None
    ) -> Repository:
        """Load and parse an APT repository.

        Args:
            repo_url: The base URL of the APT repository
            dist: The distribution path (e.g., 'jammy' or 'dists/jammy')
            components: List of components to load (e.g., ['main', 'universe']). If None, tries common ones.

        Returns:
            A Repository object with parsed data
        """
        if not repo_url.endswith("/"):
            repo_url += "/"

        # Create repository object
        repo = Repository(url=repo_url, name=urlparse(repo_url).netloc)
        cache_dir = self._get_repo_cache_dir(repo_url)

        # Default components to try
        if components is None:
            components = ["main", "restricted", "universe", "multiverse"]

        # Try to download and parse Release file for the distribution
        release_url = urljoin(repo_url, f"{dist}/Release")
        release_path = cache_dir / f"{dist.replace('/', '_')}Release"

        try:
            await self._download_file(release_url, release_path)
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to download Release file from {release_url}: {e}")

        # Parse Release file
        release_content = release_path.read_text(encoding="utf-8")
        release_data = next(deb822.Release.iter_paragraphs(release_content))

        release = Release(
            name=dist,
            codename=release_data.get("Codename"),
            suite=release_data.get("Suite"),
            version=release_data.get("Version"),
            architectures=release_data.get("Architectures", "").split(),
        )

        # For each component and architecture, download and parse Packages files
        for comp_name in components:
            component = Component(name=comp_name)

            for arch in release.architectures:
                if not arch or arch == "all":
                    continue

                # Try to download Packages file (prefer .gz)
                packages_url = urljoin(repo_url, f"{dist}/{comp_name}/binary-{arch}/Packages.gz")
                packages_path = cache_dir / f"{dist.replace('/', '_')}{comp_name}_binary-{arch}_Packages.gz"

                try:
                    await self._download_file(packages_url, packages_path)
                    packages = self._parse_packages_file(packages_path)
                    component.packages.update(packages)
                except httpx.HTTPError:
                    # Try without .gz
                    packages_url = urljoin(repo_url, f"{dist}/{comp_name}/binary-{arch}/Packages")
                    packages_path = cache_dir / f"{dist.replace('/', '_')}{comp_name}_binary-{arch}_Packages"
                    try:
                        await self._download_file(packages_url, packages_path)
                        packages = self._parse_packages_file(packages_path)
                        component.packages.update(packages)
                    except httpx.HTTPError:
                        continue  # Skip this component/architecture combination

            if component.packages:
                release.components[comp_name] = component

        repo.releases[release.name] = release
        return repo
