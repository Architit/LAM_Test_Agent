# GATEWAY DEPLOYMENT & CIRCULATION PROTOCOL V1

## Purpose
Standardize the deployment and operation of data export/import gateways across internal and external environments.

## Security & Deployment Architecture
- **DMZ (Demilitarized Zone):** Внешние шлюзы (External Gateways) развертываются исключительно в изолированной DMZ.
- **mTLS & Tokenization:** Для всех соединений обязательна взаимная аутентификация (mTLS) и токенизация доступа.
- **Internal Bridges (gRPC):** Внутренние мосты между подсистемами используют gRPC для обеспечения Low-Latency (минуя внешние периметры безопасности, но сохраняя мониторинг аномалий).

## Конвейеры Валидации (ETL)
Любые данные, пересекающие периметр шлюза, должны проходить через ETL-модули:
1.  **Validation:** Проверка соответствия входящей нагрузки (Payload) заданным JSON-схемам.
2.  **Sanitization:** Очистка от потенциально вредоносного кода или неформатированных структур.
3.  **Transformation:** Приведение данных к стандарту целевой среды.

### Internal Gateway (Bridge-to-Hub)
- **Target:** `.gateway/bridge/captain/`
- **Config:** `GATEWAY_CIRCULATION_POLICY_TEMPLATE.json`
- **Steps:**
  1.  Allocate `node_id` for the target system (e.g., `linux_host_01`).
  2.  Initialize outbox: `mkdir -p .gateway/circulation/inversion/outbox/<node_id>`.
  3.  Verify HMAC signing key from `mobile_tokens`.
  4.  Enable `lam_realtime_circulation.sh` daemon.

### External Gateway (Hub-to-Public)
- **Target:** `EXTERNAL_FEEDBACK_GATEWAY`
- **Config:** `EXTERNAL_FEEDBACK_GATEWAY_PROTOCOL_V1.md`
- **Steps:**
  1.  Verify provider credentials in `provider-secrets.env`.
  2.  Set `LAM_HUB_SANITIZATION_LEVEL=high` (removes internal paths/IDs).
  3.  Execute `scripts/lam_feedback_gateway.sh`.
  4.  Monitor `receipts/` for acknowledgement.

## Circulation Rules
- **No Direct Agent Export:** Agents are forbidden from making direct network calls to external environments. All exports *must* pass through the Hub Gateway.
- **Sanitization First:** Data entering or leaving the ecosystem must be processed by a `Model Armor` template or `gws --sanitize`.
- **Inversion of Control:** External systems do not pull from the ecosystem; the ecosystem's gateways "push" to approved endpoints.

## Operational Control
- **Circulation Kill-Switch:** `scripts/lam_gateway.sh circulation-kill-switch on` immediately halts all non-essential data movement between zones.
- **Quota Management:** Gateways must enforce `LAM_GATEWAY_EXPORT_QUOTA_MB_PER_H` to prevent data exfiltration.
