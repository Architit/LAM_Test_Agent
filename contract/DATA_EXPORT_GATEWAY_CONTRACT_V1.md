# DATA EXPORT GATEWAY CONTRACT V1

contract_type: infrastructure_governance
version: v1
status: ACTIVE
mode: contracts-first, derivation-only
effective_utc: 2026-03-14T20:30:00Z

## Objective
Establish a synchronized multi-layer data export infrastructure ("Pipes") between WSL (Linux) and Windows Host (C:\data) for external cloud delivery.

## 1. Export Topology (The Sovereign Organs)
Each of the 24 Sovereign Trees (Organs) MUST have a dedicated export slot:
- Internal Source: `/home/architit/work/LAM/data/export/<OrganName>/`
- External Gateway: `C:\data\gateways\<OrganName>\`

## 2. Routing Channels (Cloud Delivery)
Primary export routes from `C:\data` are defined as:
- `C:\data\cloud\google\` — For GDrive/Workspace synchronization.
- `C:\data\cloud\microsoft\` — For OneDrive/SharePoint.
- `C:\data\cloud\ollama\` — For local LLM model feeding.
- `C:\data\cloud\shinkai\` — For decentralized network storage.

## 3. Data Circulation Rules
- **One-Way Primary:** Movement is primarily Outbound (Internal -> External).
- **Atomic Movement:** Only completed files/reports are moved to `export`.
- **Integrity:** Every exported file must be logged in `DEV_LOGS.md` or the gateway audit stream.

## 4. Maintenance
- Cleanup of exported data older than 30 days is mandatory.
- The BIOS Boot Manager MUST verify the presence of these pipes on every start.

---
*Signed by GUARD-01 (Sentinel-Guard)* ⚜️
