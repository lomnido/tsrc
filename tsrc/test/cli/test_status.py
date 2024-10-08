import shutil
from pathlib import Path

from cli_ui.tests import MessageRecorder

# import pytest
from tsrc.git import run_git
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer


def test_status_happy(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Scenario:
    * Create a workspace with two clean repos in
      foo/bar and spam/eggs
    * Run `tsrc status`
    * Check that both paths are printed and properly aligned
    """
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    git_server.push_file("foo/bar", "CMakeLists.txt")
    git_server.push_file("spam/eggs", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    run_git(workspace_path / "spam/eggs", "checkout", "-b", "fish")

    tsrc_cli.run("status")

    assert message_recorder.find(r"\* foo/bar   master")
    assert message_recorder.find(r"\* spam/eggs fish")


def test_status_dirty(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Scenario:
    * Create a workspace with one repo
    * Create an untracked modifications
    * Run `tsrc status`
    * Check that the repo is shown as dirty
    """
    git_server.add_repo("foo")
    git_server.push_file("foo", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    (workspace_path / "foo/CMakeLists.txt").write_text("DIRTY FILE")

    tsrc_cli.run("status")

    assert message_recorder.find(r"\* foo master \(dirty\)")


def test_status_incorrect_branch(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Scenario:
    * Create a workspace with  one repo
    * Create and checkout an 'other' branch
    * Run `tsrc status`
    * Check that the repo is shown as not being
      on the correct branch
    """
    git_server.add_repo("foo")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    foo_path = workspace_path / "foo"
    run_git(foo_path, "checkout", "-b", "other")
    run_git(foo_path, "push", "--set-upstream", "origin", "other:other")

    tsrc_cli.run("status")

    assert message_recorder.find(r"\* foo\s+other\s+\(expected: master\)")


def test_status_not_on_any_branch(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Scenario:
    * Create a workspace with one repo
    * Make sure the repo is not an any branch
    * Run `tsrc status`
    * Check that the output contains a sha1
    """
    git_server.add_repo("foo")
    # we need more that one commit
    # to be in 'detached HEAD':
    git_server.push_file("foo", "new.txt")

    git_server.add_repo("bar")

    tsrc_cli.run("init", git_server.manifest_url)

    # detach HEAD on foo repo
    foo_path = workspace_path / "foo"
    run_git(foo_path, "checkout", "HEAD~1")

    tsrc_cli.run("status")

    assert message_recorder.find(r"\* foo [a-f0-9]{7}")


def test_status_on_tag(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Scenario:
    * Create a workspace with one repo
    * Create a tag on the repo
    * Run `tsrc status`
    * Check that the output contains the tag name
    """
    git_server.add_repo("foo")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    foo_path = workspace_path / "foo"
    run_git(foo_path, "tag", "v1.0")

    tsrc_cli.run("status")

    assert message_recorder.find(r"\* foo master on v1.0")


def test_status_with_missing_repos(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Scenario:
    * Create a manifest with two repos, foo and bar
    * Initialize a workspace from this manifest
    * Remove the `foo` clone
    * Run `tsrc status`
    * Check that it does not crash
    """
    git_server.add_repo("foo")
    git_server.add_repo("bar")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    # shutil.rmtree has trouble removing read-only
    # files in the .git repo, but this won't affect
    # the outcome of the test anyway
    shutil.rmtree(workspace_path / "foo", ignore_errors=True)

    tsrc_cli.run("status")


def test_use_given_group(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Scenario:
    * Create a manifest with two disjoint groups,
      group1 and group2
    * Initialize a workspace from this manifest using
      the two groups
    * Run `tsrc status --group group1`
    * Check that the output contains repos from group1, but not
      from group2
    """
    git_server.add_group("group1", ["foo"])
    git_server.add_group("group2", ["bar"])

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "--groups", "group1", "group2")

    message_recorder.reset()
    tsrc_cli.run("status", "--group", "group1")
    assert message_recorder.find(r"\* foo"), "foo status have been read"
    assert not message_recorder.find(r"\* bar"), "bar should have been skipped"


def test_use_non_cloned_group(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Scenario:
    * Create a manifest with two disjoint groups,
      group1 and group2
    * Initialize a workspace from this manifest using
      the group 'group1'
    * Run `tsrc status --group group2`
    * Check that it does not crash
    """
    git_server.add_group("group1", ["foo"])
    git_server.add_group("group2", ["bar"])

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "--groups", "group1")

    message_recorder.reset()
    tsrc_cli.run("status", "--group", "group2")


def test_correct_missing_upstream(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Scenario:

    * 1st: create single repo1
    * 2nd: init Workspace
    * 3rd: switch to branch 'dev'
    * 4th: create tag with same name 'dev'
    * 5th: push such branch 'dev' to 'origin'
    * 6th: no (missing upstream) should be present now
    """
    # 1st: create single repo1
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")

    # 2nd: init Workspace
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", "--branch", "master", manifest_url)

    # 3rd: switch to branch 'dev'
    repo1_path = workspace_path / "repo1"
    run_git(repo1_path, "checkout", "-b", "dev")

    # 4th: create tag with same name 'dev'
    run_git(repo1_path, "tag", "-a", "dev", "-m", "hunting bugs")

    # 5th: push such branch 'dev' to 'origin'
    run_git(repo1_path, "push", "-u", "origin", "heads/dev")
    tsrc_cli.run("status")

    # 6th: no (missing upstream) should be present now
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo1 heads/dev on dev \(expected: master\)")
    assert not message_recorder.find(r"\(missing upstream\)")
