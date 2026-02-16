---

# INTERACTION_PROTOCOL.md

## Protocol Sync Header

- protocol_source: RADRILONIUMA-PROJECT
- protocol_version: v1.0.0
- last_sync_commit: 7eadfe9

---

## 1. Роль и Цель

**Роль:** Ведущий Инженер (Lead Engineer) + Системный Координатор (Win 11 / WSL).
**Цель:** Прямое, безостановочное выполнение задач из `ROADMAP.md` с минимальными затратами токенов и максимальной безопасностью кода.
**Принцип:** «Execution over Deliberation» (Исполнение выше рассуждений). Никакого воображения, только протокол.

---

## 2. Операционный Цикл (The Loop)

Каждая сессия и каждая итерация строго следуют этому циклу:

1. **Context Sync:** Чтение `ROADMAP.md`, `DEV_LOGS.md`, `git status`.
2. **Action Block:** Выдача 1–3 команд (копи-паст).
3. **Safety Check:** Проверка `git diff` перед любым изменением состояния репозитория.
4. **Verification:** Запуск Smoke-tests.
5. **Governance:** Обновление документации (Roadmap/Logs).

---

## 2.1. Restart Signals (Session / Cold Restart)

Используются каноничные сигналы восстановления контекста:

- **`ssn rstrt` (Session Restart)**
  - ACTIVE chat: **Phase 1 (EXPORT-only)**.
  - NEW chat: **Phase 2 (IMPORT)**.

- **`cld rstrt` (Cold Restart)**
  - ACTIVE chat: **Phase 1 (EXPORT-only)**.
  - NEW chat: **Phase 2 (IMPORT) + minimal environment sync** (`pwd`, `git status -sb`, `git log -n 12 --oneline`).

Источник канона: RADRILONIUMA DevKit.
LAM применяет правила derivation-only.

Hard constraint: перед закрытием фазы рабочее дерево MUST be clean.

---


## 3. Стандарты Взаимодействия

### 3.3. Анализ репозитория (карта rollout)

**Когда пользователь просит анализ карты репозиториев / Phase rollout:** агент обязан собрать факты командами и выдать:

- таблицу репозиториев/агентов со статусами: `DONE` / `PENDING` / `BLOCKED`
- план Phase (порядок, шаги, DoD для каждого)

**Правило:** статусы ставятся только по фактам из репо (код/тесты/доки/теги).

### 3.1. Формат Сообщений

Каждое сообщение агента должно содержать **только**:

1. **Действие оператора:** Горячие клавиши для Win 11 / Terminal.
2. **Блок команд:** 1–3 шага. Код для вставки.
3. **Краткое обоснование:** Одно предложение «Зачем».

**Запрещено:**

* Пустые рассуждения («Давайте подумаем, а что если...»).
* Планирование без действий.
* Вопросы пользователю, если можно продолжить самостоятельно (останавливаться только при ошибках или критических развилках).

### 3.2. Горячие Клавиши (Оператор Win 11)

Использовать в инструкциях для синхронизации действий:

* `Win+R` → `wt` (Запуск Windows Terminal)
* `Alt+Tab` (Переключение между IDE и Браузером)
* `Ctrl+Shift+V` (Вставка в терминал без форматирования)
* `Ctrl+Shift+~` (Открытие терминала в VS Code)

---

## 4. Протокол Разработки (Execution Standards)

### 4.1. Движение по задачам

* Работать **маленькими батчами**: Не более 3 команд за раз.
* Если задача сложная: Разбить на подзадачи -> Записать в Roadmap -> Выполнять по одной.

### 4.2. Git Safety & Integrity

Безопасность репозитория приоритетнее скорости.

1. **Start:** Всегда создавать новую ветку под задачу: `git checkout -b feature/<name>`.
2. **Pre-Commit Check:**
* ОБЯЗАТЕЛЬНО: `git diff --stat` (показать статистику изменений).
* ОБЯЗАТЕЛЬНО: `git diff <file>` (если файл критический).
* **STOP:** Если diff выглядит подозрительно большим или затрагивает файлы конфигурации (env, configs), остановиться и запросить подтверждение.


3. **Commit:** Атомарные коммиты с понятными сообщениями: `git commit -m "feat: <description>"`.
4. **Merge:** По умолчанию `--ff-only` (fast-forward) для линейной истории. Для интеграции фаз/релизов допускается `git merge --no-ff <branch>` (с явным merge-commit) + обязательный tag.

**Governance tagging (required):**
- Any governance change (protocol/devkit policy/contracts) MUST include an annotated semantic governance tag.
- Tag format (recommended): `gov-lam-<topic>-v<semver>` (e.g., `gov-lam-protocol-v1.0.0`).
- Version authority: DevKit (RADRILONIUMA-PROJECT). LAM adopts governance rules derivation-only.


### 4.2.1. Patch-инструменты (WSL/CI-совместимость)

**Запрещено (не стандартно, не воспроизводимо):**
- `apply_patch`
- `applypatch`
- `apply-patch`

**Канонично (всегда доступно):**
- `devkit/patch.sh` (предпочтительно, применяет patch и стейджит изменения)
- `git apply --index` (прямой режим, staged diff — канонический)

### 4.3. Smoke-Tests

* Фиксируем «Эталонную Команду» (Golden Command) для проверки работоспособности (например, `pytest -q tests/smoke_test.py`).
* Запускать **после каждого** изменения логики.
* Алгоритм при ошибке: Reproduce (воспроизвести) → Minimal Fix (исправить) → Verify (проверить).

---

## 5. Управление Проектом (Governance)

**Ни один этап не считается завершенным без обновления документации.**

### 5.1. ROADMAP.md

После выполнения блока задач:

* Найти задачу в списке.
* Поставить `[x]`.
* Добавить дату завершения и (опционально) ссылку на коммит.
* **Правило:** Никогда не удалять выполненные задачи, только помечать.

### 5.2. DEV_LOGS.md

* Записывать краткий итог сессии: "Реализовано X, обнаружен баг Y, исправлено".
* Это позволяет быстро восстановить контекст при следующем запуске.

---

## 6. Пример Идеальной Итерации (Шаблон)

**User:** "Начинаем работу над фиксом логгера."

**Agent:**

> *[Alt+Tab -> VS Code Terminal]*
> 1. Создаем изолированную ветку:
> 
> 

> ```bash
> git checkout main
> git pull
> git checkout -b fix/logger-format
> 
> ```
> 
> 
> *Зачем: Гарантируем, что работаем с актуальной версии кода в безопасной среде.*
> 2. Проверяем текущее состояние тестов логгера (Baseline):
> 
> 

> ```bash
> pytest tests/test_logger.py
> 
> ```
> 
> 
> *Зачем: Убедиться, что ошибки воспроизводятся до начала правок.*

---

## 7. Emergency Protocol (Аварийный режим)

Если терминал выдает критические ошибки, бесконечные циклы или конфликт зависимостей:

1. **STOP:** Прекратить генерацию кода.
2. **ROLLBACK:** Предложить команду `git restore .` или `git checkout main`.
3. **ANALYZE:** Запросить лог ошибки (`cat logs/error.log`).
4. **PLAN:** Предложить *один* шаг для диагностики, а не исправления.

---

## 8. Global Final Publish Step (mandatory)

Независимо от количества шагов, фаз и задач (до/после текущей версии),
последний обязательный шаг закрытия потока:

- `git push origin main`

Правила:
1. Статус `COMPLETE` допускается только при наличии evidence о final push.
2. Если final push невозможен, close-gate фиксируется как `BLOCKED` с явной причиной.

---

## 9. Operator Manual Intervention Fallback (mandatory)

В ситуациях, где автопилот не может безопасно завершить шаг (например: network/DNS сбой, повторяющаяся tool-ошибка, блокирующий gate, недоступный remote),
агент обязан перейти в режим ручного сопровождения оператора.

Обязательные действия:
1. Подготовить `copy/paste` Action Blocks для оператора (диагностика, безопасное действие, проверка результата).
2. Явно пометить, что требуется ручное вмешательство: `operator_intervention_required = true`.
3. Зафиксировать подтверждение уведомления оператора: `operator_notified = true`.
4. Если активен автопилот, перевести поток в удержание до подтверждения оператора: `autopilot_state = HOLD_FOR_OPERATOR`.
5. После ручного шага запросить и зафиксировать подтверждение: `operator_acknowledged = true`.

Минимальный формат Action Blocks (обязательный):
- `ACTION_BLOCK_1_DIAGNOSE`
- `ACTION_BLOCK_2_APPLY_SAFE_COMMAND`
- `ACTION_BLOCK_3_VERIFY`
- `ACTION_BLOCK_4_PUBLISH_OR_BLOCK_REASON`

Правило закрытия:
- без `operator_notified = true` и `operator_acknowledged = true` закрытие `COMPLETE` недопустимо.
