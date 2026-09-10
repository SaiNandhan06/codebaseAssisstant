from git import Repo
import os

REPO_URL = "https://github.com/SaiNandhan06/QR-CodeGenerator.git"
CLONE_PATH = r"C:\Users\M Sainandhan\OneDrive\Documents\Projects\newQRGenerator"

if not os.path.exists(CLONE_PATH):
    print("Cloning...")
    Repo.clone_from(REPO_URL,CLONE_PATH)
    print("Done.")
else:
    print("Already cloned.")

py_files = []
for root, dirs, files in os.walk(CLONE_PATH):
    dirs[:] = [d for d in dirs if d != ".git"]
    for file in files:
        if file.endswith(".py"):
            py_files.append(os.path.join(root,file))

print(f"\nFound {len(py_files)} Python files:")
for f in py_files:
    print(f)