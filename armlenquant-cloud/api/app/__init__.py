"""ArmLenQuant API Application"""

# Compatibility shim for Python versions where importlib.metadata
# lacks packages_distributions (e.g., Python 3.9.0).
from typing import Dict, List
import importlib.metadata as metadata

if not hasattr(metadata, "packages_distributions"):
    def _packages_distributions() -> Dict[str, List[str]]:
        mapping: Dict[str, List[str]] = {}
        for dist in metadata.distributions():
            top_level = dist.read_text("top_level.txt") or ""
            # Some PathDistribution objects on older Python versions do not expose
            # a `name` attribute, so we resolve the package name defensively.
            dist_name = (
                dist.metadata.get("Name")
                or getattr(dist, "name", None)
                or getattr(dist, "project_name", None)
                or (getattr(dist, "_path", None).stem if getattr(dist, "_path", None) else None)
                or "unknown"
            )
            for package in top_level.splitlines():
                if package:
                    mapping.setdefault(package, []).append(dist_name)
        return mapping

    metadata.packages_distributions = _packages_distributions  # type: ignore[attr-defined]

