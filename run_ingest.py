import os
import sys
from collections import Counter
from ingest.pipeline import collect_chunks
from ingest.git_history import attach_history

default = r"C:\Users\M Sainandhan\OneDrive\Documents\Projects\newQRGenerator"
repo_path = sys.argv[1] if len(sys.argv) > 1 else default

if not os.path.isdir(repo_path):
    sys.exit(f"Error: '{repo_path}' is not a folder")

chunks, skipped = collect_chunks(repo_path)
files_looked_up = attach_history(chunks, repo_path)

print(f"Chunks: {len(chunks)}")
print("By kind:", dict(Counter(c.kind for c in chunks)))
print("By language:", dict(Counter(c.language for c in chunks)))
print(f"Git history looked up for {files_looked_up} file(s)")

print(f"\nSkipped {len(skipped)} file(s):")
for path, reason in skipped:
    print(f"  - {path}: {reason}")

print("\nFirst chunks:")
for c in chunks[:8]:
    owner = f"{c.parent}." if c.parent else ""
    print(f"  [{c.kind}] {owner}{c.name}  {c.file_path}:{c.start_line}-{c.end_line}")
    for commit in c.commits[:2]:
        print(f"    {commit['hash']} {commit['date']} {commit['message']}")