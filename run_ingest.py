import sys
from collections import Counter
from ingest.pipeline import collect_chunks

repo_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\M Sainandhan\OneDrive\Documents\Projects\newQRGenerator"

chunks, skipped = collect_chunks(repo_path)

print(f"Chunks: {len(chunks)}")
print("By kind:", dict(Counter(c.kind for c in chunks)))
print("By language:", dict(Counter(c.language for c in chunks)))

print(f"\nSkipped {len(skipped)} file(s):")
for path, reason in skipped:
    print(f"  - {path}: {reason}")

print("\nFirst chunks:")
for c in chunks[:10]:
    owner = f"{c.parent}." if c.parent else ""
    print(f"  [{c.kind}] {owner}{c.name}  {c.file_path}:{c.start_line}-{c.end_line}")

print("\n--- Sample chunk code ---\n" + chunks[0].code)