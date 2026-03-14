#!/usr/bin/env bash
# [MASS PUBLISH PROTOCOL: VAVIMA PHASE 8.1]
# Synchronizes all Sovereign Trees with their respective remotes.

set -e

# Dynamically find all git repos in the work directory
REPOS=($(find /home/architit/work -maxdepth 1 -type d))


COMMIT_MSG="Phase 8.1: Sovereign Materialization & Awakening Protocol Sync (M48)"

echo ">>> Starting Global Mass Publish..."

for repo in "${REPOS[@]}"; do
    if [ -d "$repo/.git" ]; then
        echo "[+] Processing: $repo"
        cd "$repo"
        
        # 1. Check for changes
        if [[ -n $(git status --porcelain) ]]; then
            echo "    -> Changes detected. Staging and committing..."
            git add .
            git commit -m "$COMMIT_MSG" || echo "    [!] Warning: Commit failed (might be no changes after add)."
        else
            echo "    -> No changes to commit."
        fi
        
        # 2. Push to origin
        BRANCH=$(git rev-parse --abbrev-ref HEAD)
        echo "    -> Pushing branch '$BRANCH' to origin..."
        git push origin "$BRANCH" || echo "    [!] Error: Push failed for $repo"
    else
        echo "[-] Skipped (not a git repo): $repo"
    fi
done

echo ">>> Global Mass Publish Complete. The Living Forest is synchronized."
