from pathlib import Path

from .conftest import (
    TmuxEnvironment,
    get_window_name,
    get_worktree_path,
    run_workmux_add,
    run_workmux_remove,
    write_workmux_config,
)


def test_remove_cleans_up_worktree(
    isolated_tmux_server: TmuxEnvironment, workmux_exe_path: Path, repo_path: Path
):
    """Verifies that `workmux remove` removes the worktree, tmux window, and branch."""
    env = isolated_tmux_server
    branch_name = "feature-to-remove"
    window_name = get_window_name(branch_name)

    write_workmux_config(repo_path)

    # First, create a worktree
    run_workmux_add(env, workmux_exe_path, repo_path, branch_name)

    # Verify it was created
    worktree_path = get_worktree_path(repo_path, branch_name)
    assert worktree_path.is_dir(), "Worktree should exist after add"

    list_windows_result = env.tmux(["list-windows", "-F", "#{window_name}"])
    assert window_name in list_windows_result.stdout, (
        "Tmux window should exist after add"
    )

    branch_list_result = env.run_command(["git", "branch", "--list", branch_name])
    assert branch_name in branch_list_result.stdout, "Branch should exist after add"

    # Now remove it with force flag
    run_workmux_remove(env, workmux_exe_path, repo_path, branch_name, force=True)

    # Verify worktree directory was removed
    assert not worktree_path.exists(), "Worktree should be removed after remove"

    # Verify tmux window was removed
    list_windows_result = env.tmux(["list-windows", "-F", "#{window_name}"])
    assert window_name not in list_windows_result.stdout, (
        "Tmux window should be removed after remove"
    )

    # Verify branch was removed
    branch_list_result = env.run_command(["git", "branch", "--list", branch_name])
    assert branch_name not in branch_list_result.stdout, (
        "Branch should be removed after remove"
    )


def test_remove_with_force_flag(
    isolated_tmux_server: TmuxEnvironment, workmux_exe_path: Path, repo_path: Path
):
    """Verifies that `workmux remove -f` skips confirmation and removes successfully."""
    env = isolated_tmux_server
    branch_name = "feature-force-remove"

    write_workmux_config(repo_path)

    # Create a worktree
    run_workmux_add(env, workmux_exe_path, repo_path, branch_name)

    # Verify it was created
    worktree_path = get_worktree_path(repo_path, branch_name)
    assert worktree_path.is_dir(), "Worktree should exist after add"

    # Remove with force flag should succeed without any interaction
    run_workmux_remove(env, workmux_exe_path, repo_path, branch_name, force=True)

    # Verify cleanup completed
    assert not worktree_path.exists(), "Worktree should be removed after force remove"
