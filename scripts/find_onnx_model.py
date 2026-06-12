from huggingface_hub import list_repo_files

for repo in [
    "Xenova/distilbert-base-uncased-finetuned-sst-2-english",
    "distilbert-base-uncased-finetuned-sst-2-english",
    "optimum/distilbert-base-uncased-finetuned-sst-2-english",
]:
    try:
        files = list(list_repo_files(repo))
        print(f"OK {repo}: {len(files)} files")
        for f in files[:12]:
            print(" ", f)
    except Exception as exc:
        print(f"FAIL {repo}: {exc}")
