import os
from pathlib import Path

from .conftest import (
    TmuxEnvironment,
    get_window_name,
    get_worktree_path,
    poll_until,
    run_workmux_add,
    write_workmux_config,
)


def test_add_creates_worktree(
    isolated_tmux_server: TmuxEnvironment, workmux_exe_path: Path, repo_path: Path
):
    """Verifies that `workmux add` creates a git worktree."""
    env = isolated_tmux_server
    branch_name = "feature-worktree"

    write_workmux_config(repo_path)

    run_workmux_add(env, workmux_exe_path, repo_path, branch_name)

    # Verify worktree in git's state
    worktree_list_result = env.run_command(["git", "worktree", "list"])
    assert branch_name in worktree_list_result.stdout

    # Verify worktree directory exists
    expected_worktree_dir = get_worktree_path(repo_path, branch_name)
    assert expected_worktree_dir.is_dir()


def test_add_creates_tmux_window(
    isolated_tmux_server: TmuxEnvironment, workmux_exe_path: Path, repo_path: Path
):
    """Verifies that `workmux add` creates a tmux window with the correct name."""
    env = isolated_tmux_server
    branch_name = "feature-window"
    window_name = get_window_name(branch_name)

    write_workmux_config(repo_path)

    run_workmux_add(env, workmux_exe_path, repo_path, branch_name)

    # Verify tmux window was created
    list_windows_result = env.tmux(["list-windows", "-F", "#{window_name}"])
    existing_windows = list_windows_result.stdout.strip().split("\n")
    assert window_name in existing_windows


def test_add_executes_post_create_hooks(
    isolated_tmux_server: TmuxEnvironment, workmux_exe_path: Path, repo_path: Path
):
    """Verifies that `workmux add` executes post_create hooks in the worktree directory."""
    env = isolated_tmux_server
    branch_name = "feature-hooks"
    hook_file = "hook_was_executed.txt"

    write_workmux_config(repo_path, post_create=[f"touch {hook_file}"])

    run_workmux_add(env, workmux_exe_path, repo_path, branch_name)

    # Verify hook file was created in the worktree directory
    expected_worktree_dir = get_worktree_path(repo_path, branch_name)
    assert (expected_worktree_dir / hook_file).exists()


def test_add_executes_pane_commands(
    isolated_tmux_server: TmuxEnvironment, workmux_exe_path: Path, repo_path: Path
):
    """Verifies that `workmux add` executes commands in configured panes."""
    env = isolated_tmux_server
    branch_name = "feature-panes"
    window_name = get_window_name(branch_name)
    expected_output = "test pane command output"

    write_workmux_config(
        repo_path, panes=[{"command": f"echo '{expected_output}'; sleep 0.5"}]
    )

    run_workmux_add(env, workmux_exe_path, repo_path, branch_name)

    # Verify pane command output appears in the pane
    def check_pane_output():
        capture_result = env.tmux(["capture-pane", "-p", "-t", window_name])
        return expected_output in capture_result.stdout

    assert poll_until(check_pane_output, timeout=2.0), (
        f"Expected output '{expected_output}' not found in pane"
    )


def test_add_sources_shell_rc_files(
    isolated_tmux_server: TmuxEnvironment, workmux_exe_path: Path, repo_path: Path
):
    """Verifies that shell rc files (.zshrc) are sourced and aliases work in pane commands."""
    env = isolated_tmux_server
    branch_name = "feature-aliases"
    window_name = get_window_name(branch_name)
    alias_output = "custom_alias_worked_correctly"

    # Create a custom HOME directory with a .zshrc that defines an alias
    test_home = env.tmp_path / "test_home"
    test_home.mkdir()
    zshrc_content = f"""
# Test alias
alias testcmd='echo "{alias_output}"'
"""
    (test_home / ".zshrc").write_text(zshrc_content)

    write_workmux_config(repo_path, panes=[{"command": "testcmd; sleep 0.5"}])

    # Define pre-run commands to set the environment inside tmux
    shell_path = os.environ.get("SHELL", "/bin/zsh")
    pre_cmds = [
        ["setenv", "HOME", str(test_home)],
        ["setenv", "SHELL", shell_path],
    ]

    # Run workmux add using the generalized helper
    run_workmux_add(
        env, workmux_exe_path, repo_path, branch_name, pre_run_tmux_cmds=pre_cmds
    )

    # Verify the alias output appears in the pane
    def check_alias_output():
        capture_result = env.tmux(["capture-pane", "-p", "-t", window_name])
        return alias_output in capture_result.stdout

    assert poll_until(check_alias_output, timeout=2.0), (
        f"Alias output '{alias_output}' not found in pane - shell rc file not sourced"
    )
