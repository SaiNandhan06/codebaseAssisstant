import os
from git import Repo
from git.exc import InvalidGitRepositoryError


def open_repo(path):
    try:
        return Repo(path, search_parent_directories=True)
    except InvalidGitRepositoryError:
        return None


def file_history(repo, git_path, max_commits=5):
    commits = []
    for c in repo.iter_commits(paths=git_path, max_count=max_commits):
        commits.append({
            "hash": c.hexsha[:7],
            "author": c.author.name,
            "date": c.committed_datetime.date().isoformat(),
            "message": c.message.strip().split("\n")[0],  # first line only
        })
    return commits


def attach_history(chunks, repo_path, max_commits=5):
    """Adds the recent commits touching each chunk's file. Returns number of files looked up."""
    repo = open_repo(repo_path)
    if repo is None:
        return 0

    # If we scan a subfolder of a repo, git paths need that folder as a prefix
    prefix = os.path.relpath(repo_path, repo.working_tree_dir).replace("\\", "/")

    cache = {}  # many chunks share a file, so look each file up once
    for chunk in chunks:
        if chunk.file_path not in cache:
            git_path = chunk.file_path if prefix == "." else f"{prefix}/{chunk.file_path}"
            cache[chunk.file_path] = file_history(repo, git_path, max_commits)
        chunk.commits = cache[chunk.file_path]
    return len(cache)