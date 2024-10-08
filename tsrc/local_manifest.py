from pathlib import Path
from typing import Optional

from tsrc.git import get_current_branch, run_git
from tsrc.manifest import Manifest, load_manifest, load_manifest_safe_mode
from tsrc.manifest_common_data import ManifestsTypeOfData


class LocalManifest:
    """Represent a manifest repository that has been cloned locally
    inside `<workspace>/.tsrc/manifest`.

    Usage:

    >>> local_manifest = LocalManifest(Path(workspace / ".tsrc/manifest")

    # First, update the cloned repository using a remote git URL and a
    # branch:
    >>> manifest.update("git@acme.com/manifest.git", branch="devel")

    # Then, read the `manifest.yml` file from the clone repository:
    >>> manifest = local_manifest.get_manifest()

    """

    def __init__(self, clone_path: Path) -> None:
        self.clone_path = clone_path

    def current_branch(self) -> str:
        return get_current_branch(self.clone_path)

    def init(
        self,
        url: str,
        *,
        branch: Optional[str],
        show_output: bool = True,
        show_cmd: bool = True,
    ) -> None:
        parent = self.clone_path.parent
        name = self.clone_path.name
        parent.mkdir(parents=True, exist_ok=True)
        cmd = ["clone", url]
        if branch:
            cmd += ["--branch", branch]
        cmd += [name]
        run_git(
            self.clone_path.parent, *cmd, show_output=show_output, show_cmd=show_cmd
        )

    def get_manifest(self) -> Manifest:
        return load_manifest(self.clone_path / "manifest.yml")

    def get_manifest_safe_mode(self, mtod: ManifestsTypeOfData) -> Manifest:
        return load_manifest_safe_mode(self.clone_path / "manifest.yml", mtod)

    def update(
        self, url: str, *, branch: str, show_output: bool = True, show_cmd: bool = True
    ) -> None:
        run_git(
            self.clone_path,
            "remote",
            "set-url",
            "origin",
            url,
            show_output=show_output,
            show_cmd=show_cmd,
        )
        run_git(self.clone_path, "fetch", show_output=show_output, show_cmd=show_cmd)
        run_git(
            self.clone_path,
            "checkout",
            "-B",
            branch,
            show_output=show_output,
            show_cmd=show_cmd,
        )
        run_git(
            self.clone_path,
            "branch",
            branch,
            "--set-upstream-to",
            f"origin/{branch}",
            show_output=show_output,
            show_cmd=show_cmd,
        )
        ref = f"origin/{branch}"
        run_git(
            self.clone_path,
            "reset",
            "--hard",
            ref,
            show_output=show_output,
            show_cmd=show_cmd,
        )
