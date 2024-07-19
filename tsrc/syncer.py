from pathlib import Path
from typing import List, Optional, Tuple

import cli_ui as ui

from tsrc.errors import Error
from tsrc.executor import Outcome, Task
from tsrc.git import get_current_branch, get_git_status, run_git_captured
from tsrc.repo import Remote, Repo


class IncorrectBranch(Error):
    def __init__(self, *, actual: Optional[str], expected: str):
        self.actual = actual
        if actual:
            self.message = (
                f"Current branch: '{actual}' "
                f"does not match expected branch: '{expected}'"
            )
        else:
            self.message = f"Not on any branch. Expected branch: '{expected}'"


class Syncer(Task[Repo]):
    def __init__(
        self,
        workspace_path: Path,
        *,
        force: bool = False,
        remote_name: Optional[str] = None,
        correct_branch: bool = False,
    ) -> None:
        self.workspace_path = workspace_path
        self.force = force
        self.remote_name = remote_name
        self.correct_branch = correct_branch

    def describe_item(self, item: Repo) -> str:
        return item.dest

    def describe_process_start(self, item: Repo) -> List[ui.Token]:
        return ["Syncing", item.dest]

    def describe_process_end(self, item: Repo) -> List[ui.Token]:
        return [ui.green, "ok", ui.reset, item.dest]

    def process(self, index: int, count: int, repo: Repo) -> Outcome:
        """Synchronize a repo given its configuration in the manifest.

        Always start by running `git fetch`, then either:

        * try resetting the repo to the given tag or sha1 (abort
          if the repo is dirty)

        * or try merging the local branch with its upstream (abort if not
          on on the correct branch, or if the merge is not fast-forward).
        """
        error = None
        self.info_count(index, count, "Synchronizing", repo.dest)
        self.fetch(repo)

        summary_lines = []
        ref = None
        if repo.tag:
            ref = repo.tag
        elif repo.sha1:
            ref = repo.sha1

        if ref:
            self.info_3("Resetting to", ref)
            self.sync_repo_to_ref(repo, ref)
            summary_lines += [repo.dest, "-" * len(repo.dest)]
            summary_lines += [f"Reset to {ref}"]
        else:
            error, current_branch = self.check_or_change_branch(repo)

            self.info_3("Updating branch:", current_branch)
            sync_summary = self.sync_repo_to_branch(repo, current_branch=current_branch)
            if sync_summary:
                title = f"{repo.dest} on {current_branch}"
                summary_lines += [title, "-" * len(title), sync_summary]

        if not repo.ignore_submodules:
            submodule_line = self.update_submodules(repo)
            if submodule_line:
                summary_lines.append(submodule_line)

        summary = "\n".join(summary_lines)
        return Outcome(error=error, summary=summary)

    def check_or_change_branch(self, repo: Repo) -> Tuple[Optional[Error], str]:
        """Check that the current branch:
            * exists
            * matches the one in the manifest

        If it does, do nothing.

        If not but the repo is clean and the correct_branch flag is set,
        switch to the configured branch."""
        error = None
        current_branch = None

        try:
            current_branch = self.check_branch(repo)
        except IncorrectBranch as e:
            current_branch = e.actual

            if self.correct_branch:
                self.checkout_branch(repo)
                current_branch = repo.branch
            else:
                error = e

            if not current_branch:
                raise

        return error, current_branch

    def check_branch(self, repo: Repo) -> str:
        """Check that the current branch:
            * exists
            * matches the one in the manifest

        Return the current branch.
        """
        repo_path = self.workspace_path / repo.dest
        current_branch = None
        try:
            current_branch = get_current_branch(repo_path)
        except Error:
            raise IncorrectBranch(actual=None, expected=repo.branch)

        if current_branch and current_branch != repo.branch:
            raise IncorrectBranch(actual=current_branch, expected=repo.branch)

        return current_branch

    def _pick_remotes(self, repo: Repo) -> List[Remote]:
        if self.remote_name:
            for remote in repo.remotes:
                if remote.name == self.remote_name:
                    return [remote]
            message = f"Remote {self.remote_name} not found for repository {repo.dest}"
            raise Error(message)

        return repo.remotes

    def fetch(self, repo: Repo) -> None:
        repo_path = self.workspace_path / repo.dest
        for remote in self._pick_remotes(repo):
            try:
                self.info_3("Fetching", remote.name)
                cmd = ["fetch", "--tags", "--prune", remote.name]
                if self.force:
                    cmd.append("--force")
                self.run_git(repo_path, *cmd)
            except Error:
                raise Error(f"fetch from '{remote.name}' failed")

    def sync_repo_to_ref(self, repo: Repo, ref: str) -> None:
        repo_path = self.workspace_path / repo.dest
        status = get_git_status(repo_path)
        if status.dirty:
            raise Error(f"git repo is dirty: cannot sync to ref: {ref}")
        try:
            if repo.want_branch:
                self.sync_repo_to_ref_and_branch(repo, ref, repo.want_branch)
            else:
                self.run_git(repo_path, "reset", "--hard", ref)
        except Error:
            raise Error("updating ref failed")

    def sync_repo_to_ref_and_branch(
        self, repo: Repo, ref: str, want_branch: str
    ) -> None:
        # check branches related to 'ref'
        self.info_3("Taking care of ref while respecting branch:", want_branch)
        repo_path = self.workspace_path / repo.dest
        if repo.tag:
            rc, ret = run_git_captured(repo_path, "rev-list", "-n", "1", repo.tag)
            if rc == 0:
                ref = ret
            else:
                raise Error(f"cannot determine commit for tag: {repo.tag}")

        # 'ref' now contains SHA1 hash to required commit
        self.sync_repo_to_sha1_and_branch(repo, ref, want_branch)

    def sync_repo_to_sha1_and_branch(
        self, repo: Repo, ref: str, want_branch: str
    ) -> None:
        repo_path = self.workspace_path / repo.dest

        # obtain all branches that points to SHA1 ref
        rc, ret = run_git_captured(
            repo_path, "for-each-ref", "--format=%(refname)", "--points-at", ref
        )
        rets: List[str] = ret.splitlines()
        sel_ref: str = ""
        for i in rets:
            # filter only remote refs
            if i.startswith("refs/remotes/") is True:
                rps: List[str] = i.split("/")
                if want_branch == rps[-1]:
                    sel_ref = i
                    break  # no need to search any further

        # check if SHA1 and branch are found
        if not sel_ref:
            raise Error(
                f"configured branch: {want_branch} does not contain configured reference: {ref}"
            )

        # check if we have local branch pointing to remote ref
        rc, ret = run_git_captured(
            repo_path, "branch", "--format=%(refname) %(upstream)", "--points-at", ref
        )
        ret_lines: List[str] = ret.splitlines()
        lb_found: str = ""  # local branch (is) found (here)
        for rl in ret_lines:
            rfs: List[str] = rl.split()
            if len(rfs) == 2 and rfs[1] == sel_ref:
                lb_found = rfs[0].split("/")[-1]

        # determine if we need to checkout remote
        if not lb_found:
            self.info_3("Checking out remote branch", want_branch)
            self.run_git(repo_path, "checkout", "--track", "-b", want_branch, sel_ref)
        else:
            _, c_branch = run_git_captured(
                repo_path, "branch", "--show-current", "--format=%(refname)"
            )
            if c_branch != lb_found:
                self.info_3("Checking out branch", want_branch)
                self.run_git(repo_path, "checkout", lb_found)

        # now we are ready to reset
        self.run_git(repo_path, "reset", "--hard", ref)

    def checkout_branch(self, repo: Repo) -> None:
        repo_path = self.workspace_path / repo.dest
        status = get_git_status(repo_path)
        if status.dirty:
            raise Error(f"git repo is dirty: cannot checkout: {repo.branch}")
        try:
            self.run_git(repo_path, "checkout", repo.branch)
        except Error:
            raise Error("checking out failed")

    def update_submodules(self, repo: Repo) -> str:
        repo_path = self.workspace_path / repo.dest
        cmd = ("submodule", "update", "--init", "--recursive")
        if self.parallel:
            _, out = run_git_captured(repo_path, *cmd, check=True)
            return out
        else:
            self.run_git(repo_path, *cmd)
            return ""

    def sync_repo_to_branch(self, repo: Repo, *, current_branch: str) -> str:
        repo_path = self.workspace_path / repo.dest
        if self.parallel:
            # Note: we want the summary to:
            # * be empty if the repo was already up-to-date
            # * contain the diffstat if the merge with upstream succeeds
            rc, out = run_git_captured(
                repo_path, "log", "--oneline", "HEAD..@{upstream}", check=False
            )
            if rc == 0 and not out:
                return ""
            _, merge_output = run_git_captured(
                repo_path, "merge", "--ff-only", "@{upstream}", check=True
            )
            return merge_output
        else:
            # Note: no summary here, because the output of `git merge`
            # is not captured, so the diffstat or the "Already up to
            # date"  message are directly shown to the user
            try:
                self.run_git(repo_path, "merge", "--ff-only", "@{upstream}")
            except Error:
                raise Error("updating branch failed")
            return ""
