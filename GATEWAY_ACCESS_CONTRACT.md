# Gateway Access Contract

## Scope
This contract defines mandatory gateway interfaces for:
- GitHub (source control sync)
- OneDrive (external file exchange)
- Google Workspace (external docs/data exchange)

## Required Environment Variables
- `GATEWAY_GITHUB_REMOTE` (default: `origin`)
- `GATEWAY_ONEDRIVE_ROOT` (example: `/mnt/c/Users/<user>/OneDrive`)
- `GATEWAY_GWORKSPACE_ROOT` (example: `/mnt/c/Users/<user>/GoogleDrive` or mounted workspace path)
- `GATEWAY_EXPORT_DIR` (default: `<repo>/.gateway/export`)
- `GATEWAY_IMPORT_DIR` (default: `<repo>/.gateway/import`)
- `LAM_EXTERNAL_DEBUG_LOG_DIR` (default: `<repo>/.gateway/external_debug`)
- `LAM_EXTERNAL_DEBUG_FILE` (default: `codex_openai_codefix_debug.jsonl`)
- `OPENAI_DEBUG_UPLOAD_URL` (required for direct upload mode)
- `OPENAI_API_KEY` (optional bearer auth for direct upload mode)
- `OPENAI_DEBUG_RECEIPTS_DIR` (default: `<repo>/.gateway/receipts`)

## Mandatory Operations
1. Verify GitHub gateway reachability by validating configured git remote.
2. Verify OneDrive gateway by checking configured directory path.
3. Verify Google Workspace gateway by checking configured directory path.
4. Export repository package to gateway export directory.
5. Import package from gateway import directory into a staged location.
6. Export Codex/OpenAI code-fix debug stream as an archive for external transfer.
7. Send Codex/OpenAI debug stream to configured external endpoint and persist delivery receipt.

## Safety Rules
- No destructive overwrite during import.
- Imports must go to `./.gateway/import_staging` first.
- Export/import operations must emit explicit logs and non-zero exits on failure.
- Direct debug upload is explicit/manual only (`send-openai-debug`) and is never implicit on normal runtime logging.
- Delivery to OpenAI is considered confirmed only when `send-openai-debug` returns `2xx` and writes a receipt in `OPENAI_DEBUG_RECEIPTS_DIR`.
- Training/improvement effect is outside this contract; this contract guarantees only transport evidence (request + response receipt).

## Implementation
- Script: `scripts/gateway_io.sh`
- Verification mode: `scripts/gateway_io.sh verify`
- Export mode: `scripts/gateway_io.sh export`
- Import mode: `scripts/gateway_io.sh import <archive>`
- Debug export mode: `scripts/gateway_io.sh export-debug [log_file]`
- Debug send mode: `scripts/gateway_io.sh send-openai-debug [log_file]`
