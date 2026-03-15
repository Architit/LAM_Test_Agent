# DYNAMIC STORAGE BALANCING & DECENTRALIZATION PROTOCOL V1

## Purpose
Optimize the distribution of the ecosystem's Active Directory and data volumes across physical media based on real-time metrics of capacity, performance, and usage.

## Core Mechanisms

### 1. Active Directory Sharding
The Ecosystem's Active Directory (the registry of all agents, nodes, and keys) is no longer a single monolithic structure. It is sharded across physical носители:
- **Hot Tier (Primary SSD/NVMe):** Active locks, high-frequency telemetry, and session states.
- **Warm Tier (Secondary SSD/Cloud):** Contracts, policies, and recently accessed archives.
- **Cold Tier (HDD/External Media):** Historical logs (`chronolog`), forensic snapshots, and deep backups.

### 2. Space-Aware Distribution Logic (Weighted Balance)
Приоритет или вероятность записи на конкретный физический носитель (узел $n$) вычисляется по формуле:
$$P_n = \frac{S_{free}^{(n)}}{\sum_{i=1}^{N} S_{free}^{(i)}} \times R_n$$
Где $S_{free}^{(n)}$ — свободный объем, а $R_n$ — исторический коэффициент надежности (uptime) узла.

### 3. Консенсус и Синхронизация
- **DHT (Distributed Hash Table):** Используется для локализации записей Active Directory (AD) в распределенной среде.
- **Adaptive Raft:** Облегченный алгоритм консенсуса для поддержания целостности состояния директорий при их фрагментации по сети физических устройств.
- **Threshold Migration:** При заполнении носителя >85%, инициируется миграция Cold Data сегментов AD на узлы с большей свободной емкостью.

## Metrics Tracking
The `STORAGE_STATUS_MAP.json` is maintained in `.gateway/hub/`:
```json
{
  "carriers": [
    {"id": "disk_0_nvme", "total_gb": 512, "free_gb": 42, "tier": "hot"},
    {"id": "disk_1_hdd", "total_gb": 2048, "free_gb": 890, "tier": "cold"}
  ],
  "shards": [
    {"path": "memory/chronolog/2025", "current_carrier": "disk_1_hdd", "priority": "low"}
  ]
}
```

## Safety Gates
- **Halt on Drift:** If mirroring parity is lost, the storage agent must signal `HOLD` to all writing agents.
- **Atomic Migration:** No directory is deleted from the source carrier until the destination's SHA256 integrity check is passed.
