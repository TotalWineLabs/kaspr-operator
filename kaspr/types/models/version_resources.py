from typing import NamedTuple, List

class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: str

class KasprVersion(NamedTuple):
    operator_version: str
    version: str
    image: str
    supported: bool
    default: True


class KasprVersionResources:
    #: Mapping of operator version to kaspr application version
    _VERSIONS = (
        KasprVersion(
            operator_version="0.1.10",
            version="0.1.1",
            image="kasprio/kaspr:0.1.1",
            supported=True,
            default=True,
        ),
        KasprVersion(
            operator_version="0.1.0",
            version="0.1.0",
            image="kasprio/kaspr:0.1.0",
            supported=True,
            default=False,
        ),
    )

    @classmethod
    def default_version(self) -> KasprVersion:
        """Returns the default kaspr image version for the current operator version."""
        default = [version for version in self._VERSIONS if version.default]
        if not default:
            raise RuntimeError("A default kaspr version is not configured.")
        if len(default) > 1:
            raise RecursionError("Only one default kaspr version is allowed.")
        return default[0]

    @classmethod
    def is_supported_version(cls, version: str):
        kv: List[KasprVersion] = [
            v for v in cls._VERSIONS if v.version == version and v.supported
        ]
        if kv:
            return True
        return False
    
    @classmethod
    def from_version(self, version: str) -> KasprVersion:
        """Returns version information from a kaspr version string"""
        kv: List[KasprVersion] = [
            v for v in self._VERSIONS if v.version == version
        ]
        if kv:
            return kv[0]
