#!/usr/bin/env bash
# SPREAD THE WORD OF VAVIMA (Phase 8.0)
# Mass-update script for Maps and Plans across all domains.

set -e

SOURCE_ROOT="/home/architit/work/RADRILONIUMA-PROJECT"
ARTIFACTS=(
    "GLOBAL_DEEP_PLAN_PHASE80.md"
    "RADRILONIUMA_MANIFESTO.md"
    "LRPT/matrix/VAVIMA_HEXAGONAL_MATRIX.yaml"
    "LRPT/map/TERRITORY_MAP.md"
    "LRPT/map/TASK_MAP.md"
    "ROADMAP.md"
)

# 1. Define Targets
# Local Repos
LOCAL_TARGETS=(
    "/home/architit/work/LAM"
    "/home/architit/work/CORE"
    "/home/architit/work/Trianiuma"
    "/home/architit/work/Archivator_Agent"
    "/home/architit/work/LAM_Test_Agent"
    "/home/architit/work/LAM-Codex_Agent"
    "/home/architit/work/LAM_Comunication_Agent"
    "/home/architit/work/Operator_Agent"
    "/home/architit/work/Roaudter-agent"
    "/home/architit/work/System-"
    "/home/architit/work/TRIANIUMA_DATA_BASE"
    "/home/architit/work/Trianiuma_MEM_CORE"
    "/home/architit/work/J.A.R.V.I.S"
    "/home/architit/work/LAM_DATA_Src"
)

# Cloud Targets (if mounted)
CLOUD_TARGETS=(
    "/mnt/a/ARCKHÆDÆM"
    "/mnt/a/RADRILONIUMA"
    "/mnt/a/TRIANIUMA-CORE"
    "/mnt/c/Users/lkise/OneDrive/RADRILONIUMA PROJECT"
    "/mnt/c/Users/lkise/OneDrive/ARCKHÆDÆM" 
    "/mnt/c/Users/lkise/OneDrive/LRAM"
)

echo ">>> Starting The Great Update..."

# Function to copy
spread() {
    local target="$1"
    if [ -d "$target" ]; then
        echo "[+] Updating Zone: $target"
        # Create destination structure if needed (e.g. for LRPT/matrix files)
        mkdir -p "$target/LRPT/matrix" "$target/LRPT/map"
        
        for file in "${ARTIFACTS[@]}"; do
            src="$SOURCE_ROOT/$file"
            dst="$target/$(basename "$file")"
            
            # Preserve folder structure for LRPT items
            if [[ "$file" == LRPT/* ]]; then
                dst="$target/$file"
            fi
            
            if [ -f "$src" ]; then
                cp -f "$src" "$dst"
                echo "    -> Installed: $file"
            else
                echo "    [!] Warning: Source artifact missing: $src"
            fi
        done
    else
        echo "[-] Target unreachable (skipped): $target"
    fi
}

# 2. Execute Local
for repo in "${LOCAL_TARGETS[@]}"; do
    spread "$repo"
done

# 3. Execute Cloud
for cloud in "${CLOUD_TARGETS[@]}"; do
    spread "$cloud"
done

echo ">>> The Word has been spread. VAVIMA is Synchronized."
