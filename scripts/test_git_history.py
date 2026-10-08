from git import Repo

repo = Repo(r"C:\Users\M Sainandhan\OneDrive\Documents\Projects\codebase-assistant")

commits = list(repo.iter_commits(max_count=5))

for commit in commits:
    print(f"Commit: {commit.hexsha[:7]}")
    print(f"Date: {commit.committed_datetime}")
    print(f"Author:{commit.author.name}")
    print(f"Message: {commit.message.strip()}")
    print(f"Files changed: {list(commit.stats.files.keys())}")
    print("-----")