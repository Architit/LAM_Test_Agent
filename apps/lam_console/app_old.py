#!/usr/bin/env python3
from __future__ import annotations

import curses
import json
import os
import sys
import time
from pathlib import Path

from apps.lam_console.core import LocalHubCore


PANES = ["LOG", "AGENTS", "QUEUE", "MODELS", "BRIDGE", "GATES", "DEVICES", "POWER", "MESH", "ACTIVITY"]


class LamConsoleUI:
    def __init__(self, stdscr, repo_root: Path) -> None:
        self.stdscr = stdscr
        self.hub = LocalHubCore(repo_root)
        self.repo_root = repo_root
        self.ui_brand = os.getenv("LAM_UI_BRAND", "LAM Captain Bridge")
        self.ui_theme_words = os.getenv("LAM_UI_THEME_WORDS", "").strip().lower()
        self.ui_profile = os.getenv("LAM_UI_PROFILE", "standard").strip().lower()
        self.glass_mode = any(
            token in self.ui_theme_words
            for token in ("liquid", "glass", "shadow", "blur", "light", "core")
        )
        self.activity_wallpaper_enabled = os.getenv("LAM_UI_ACTIVITY_WALLPAPER", "1") in {"1", "true", "True"}
        self.input_buffer = ""
        self.logs: list[str] = []
        self.status = "booting"
        self.last_health_poll = 0.0
        self.running = True
        self.pane_index = 0
        self.pane_scroll = 0
        self.hovered_tab_index: int | None = None
        self.hover_enter_ts: float = 0.0
        self.tab_ranges: list[tuple[int, int, int]] = []
        self.pane_cache: dict[str, list[str]] = {}
        self.pane_cache_ts: dict[str, float] = {}
        self.frame_interval_sec = float(os.getenv("LAM_CONSOLE_FRAME_INTERVAL_SEC", "0.08"))
        self.idle_frame_interval_sec = float(os.getenv("LAM_CONSOLE_IDLE_FRAME_INTERVAL_SEC", "0.35"))
        self.activity_anim_window_sec = float(os.getenv("LAM_CONSOLE_ACTIVITY_ANIM_WINDOW_SEC", "1.5"))
        self.input_timeout_ms = int(os.getenv("LAM_CONSOLE_INPUT_TIMEOUT_MS", "60"))
        self.health_poll_interval_sec = float(os.getenv("LAM_CONSOLE_HEALTH_POLL_SEC", "12"))
        self.pane_refresh_interval_sec = float(os.getenv("LAM_CONSOLE_PANE_REFRESH_SEC", "0.35"))
        self.last_render_ts = 0.0
        self.last_activity_ts = time.time()
        self.last_input_ts = time.time()
        self.last_input_kind = "boot"
        self.last_physics_ts = time.time()
        self.scroll_velocity = 0.0
        self.zone_flow: dict[str, float] = {p: 0.0 for p in PANES}
        self.mirror_flow_strength = float(os.getenv("LAM_UI_MIRROR_FLOW_STRENGTH", "0.35"))
        self.zone_flow_decay = float(os.getenv("LAM_UI_ZONE_FLOW_DECAY", "1.6"))
        self.zone_flow_inject = float(os.getenv("LAM_UI_ZONE_FLOW_INJECT", "1.0"))
        self.audio_feedback_enabled = os.getenv("LAM_UI_AUDIO_FEEDBACK", "1") in {"1", "true", "True"}
        self.haptic_feedback_enabled = os.getenv("LAM_UI_HAPTIC_FEEDBACK", "1") in {"1", "true", "True"}
        self.feedback_flow_threshold = float(os.getenv("LAM_UI_FEEDBACK_FLOW_THRESHOLD", "2.6"))
        self.feedback_min_interval_sec = float(os.getenv("LAM_UI_FEEDBACK_MIN_INTERVAL_SEC", "0.35"))
        self.last_feedback_ts = 0.0
        self.last_feedback_mode = "idle"
        self.ambient_light_enabled = os.getenv("LAM_UI_AMBIENT_LIGHT_ENABLED", "1") in {"1", "true", "True"}
        self.ambient_light_interval_sec = float(os.getenv("LAM_UI_AMBIENT_LIGHT_INTERVAL_SEC", "0.22"))
        self.ambient_light_max_brightness = int(os.getenv("LAM_UI_AMBIENT_LIGHT_MAX_BRIGHTNESS", "100"))
        self.last_ambient_emit_ts = 0.0
        self.dirty = True
        self.use_color = False
        self.tab_color_pairs: list[int] = []
        default_hover = "0.55" if self.ui_profile == "touch" else "0.35"
        default_zoom1 = "0.9" if self.ui_profile == "touch" else "0.7"
        default_zoom2 = "1.7" if self.ui_profile == "touch" else "1.4"
        default_hit = "2" if self.ui_profile == "touch" else "0"
        self.hover_expand_delay_sec = float(os.getenv("LAM_UI_HOVER_EXPAND_DELAY_SEC", default_hover))
        self.zoom_step1_delay_sec = float(os.getenv("LAM_UI_ZOOM_STEP1_DELAY_SEC", default_zoom1))
        self.zoom_step2_delay_sec = float(os.getenv("LAM_UI_ZOOM_STEP2_DELAY_SEC", default_zoom2))
        self.max_tab_expand = int(os.getenv("LAM_UI_MAX_TAB_EXPAND", "3"))
        self.touch_hit_zone_extra_rows = int(os.getenv("LAM_UI_TOUCH_HIT_EXTRA_ROWS", default_hit))
        self.inertia_decay = float(os.getenv("LAM_UI_SCROLL_INERTIA_DECAY", "5.4"))
        self.inertia_gain = float(os.getenv("LAM_UI_SCROLL_INERTIA_GAIN", "40"))
        self.activity_state_file = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub"))) / "activity_telemetry_state.json"
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.haptic_queue_file = self.bridge_root / "haptic_feedback_queue.jsonl"
        self.ambient_vector_file = self.bridge_root / "ambient_light_vector.json"
        self.ambient_vector_queue_file = self.bridge_root / "ambient_light_vectors.jsonl"
        self.activity_wallpaper_score = 0
        self.last_activity_wallpaper_poll = 0.0
        self.activity_wallpaper_poll_sec = float(os.getenv("LAM_UI_ACTIVITY_WALLPAPER_POLL_SEC", "1.5"))
        self.add_log(f"{self.ui_brand} ready. Keys: 1..10 panes, Enter run command.")
        if self.glass_mode:
            self.add_log("Theme active: shadow/blur/light/liquid-glass core face.")
        self._init_colors()

    @property
    def pane(self) -> str:
        return PANES[self.pane_index]

    def _mirror_pane(self, pane: str) -> str | None:
        pairs = {
            "LOG": "ACTIVITY",
            "ACTIVITY": "LOG",
            "AGENTS": "DEVICES",
            "DEVICES": "AGENTS",
            "QUEUE": "MESH",
            "MESH": "QUEUE",
            "MODELS": "POWER",
            "POWER": "MODELS",
            "BRIDGE": "GATES",
            "GATES": "BRIDGE",
        }
        return pairs.get(pane)

    def _inject_zone_flow(self, pane: str, amount: float) -> None:
        self.zone_flow[pane] = float(self.zone_flow.get(pane, 0.0)) + (amount * self.zone_flow_inject)
        mirrored = self._mirror_pane(pane)
        if mirrored:
            # Mirror coupling: opposite zone gets anti-phase response.
            self.zone_flow[mirrored] = float(self.zone_flow.get(mirrored, 0.0)) - (amount * self.mirror_flow_strength)

    def _zone_energy(self, pane: str) -> float:
        return abs(float(self.zone_flow.get(pane, 0.0)))

    def _mirror_energy(self, pane: str) -> float:
        mirrored = self._mirror_pane(pane)
        if not mirrored:
            return 0.0
        return abs(float(self.zone_flow.get(mirrored, 0.0)))

    def add_log(self, text: str) -> None:
        for line in text.splitlines():
            self.logs.append(line)
        self.logs = self.logs[-500:]
        self.dirty = True

    def _init_colors(self) -> None:
        if not curses.has_colors():
            return
        try:
            curses.start_color()
            curses.use_default_colors()
            spectrum = [
                curses.COLOR_CYAN,
                curses.COLOR_GREEN,
                curses.COLOR_YELLOW,
                curses.COLOR_MAGENTA,
                curses.COLOR_BLUE,
                curses.COLOR_RED,
                curses.COLOR_WHITE,
            ]
            for idx, color in enumerate(spectrum, start=1):
                curses.init_pair(idx, color, -1)
                self.tab_color_pairs.append(idx)
            self.use_color = True
        except curses.error:
            self.use_color = False

    def _poll_health(self) -> None:
        now = time.time()
        if now - self.last_health_poll < self.health_poll_interval_sec:
            return
        self.last_health_poll = now
        result = self.hub.health()
        if result.ok:
            providers = result.payload.get("providers", [])
            up = sum(1 for p in providers if p.get("configured") and p.get("reachable"))
            self.status = f"providers_up={up}/{len(providers)}"
        else:
            self.status = "health_error"
        self.dirty = True

    def _poll_activity_wallpaper(self) -> None:
        if not self.activity_wallpaper_enabled:
            return
        now = time.time()
        if now - self.last_activity_wallpaper_poll < self.activity_wallpaper_poll_sec:
            return
        self.last_activity_wallpaper_poll = now
        if not self.activity_state_file.exists():
            self.activity_wallpaper_score = 0
            return
        try:
            payload = json.loads(self.activity_state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self.activity_wallpaper_score = 0
            return
        signals = payload.get("signals", {}) if isinstance(payload, dict) else {}
        score = int(signals.get("activity_score", 0)) if isinstance(signals, dict) else 0
        self.activity_wallpaper_score = max(0, score)

    def _pane_lines(self) -> list[str]:
        if self.pane == "LOG":
            return self.logs[-200:]
        now = time.time()
        if now - self.pane_cache_ts.get(self.pane, 0.0) <= self.pane_refresh_interval_sec:
            return self.pane_cache.get(self.pane, [])
        lines = self.hub.pane_snapshot(self.pane)
        self.pane_cache[self.pane] = lines
        self.pane_cache_ts[self.pane] = now
        return lines

    def _tabline(self) -> str:
        self.tab_ranges = []
        chunks: list[str] = []
        x = 0
        for idx, name in enumerate(PANES):
            token = f"[{idx + 1}:{name}]"
            chunks.append(token)
            start = x
            end = x + len(token)
            self.tab_ranges.append((start, end, idx))
            x = end + 1
        return " ".join(chunks)

    def _render(self) -> None:
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        if h < 3 or w < 8:
            try:
                self.stdscr.addnstr(0, 0, "Resize terminal...", max(1, w))
                self.stdscr.refresh()
            except curses.error:
                pass
            return

        def add_line(y: int, text: str, attr: int = 0) -> None:
            if y < 0 or y >= h:
                return
            try:
                if self.activity_wallpaper_enabled and self.glass_mode and y > 1:
                    fill = self._wallpaper_fill(y, w)
                    rendered = (text + fill)[:w]
                else:
                    rendered = text.ljust(w)
                if attr:
                    self.stdscr.addnstr(y, 0, rendered, w, attr)
                else:
                    self.stdscr.addnstr(y, 0, rendered, w)
            except curses.error:
                return

        zoom_level = self._surface_zoom_level()
        zone_energy = round(self._zone_energy(self.pane), 2)
        mirror_energy = round(self._mirror_energy(self.pane), 2)
        header = (
            f"{self.ui_brand} | pane={self.pane} | {self.status} | zoom={zoom_level} "
            f"| input={self.last_input_kind} | flow={zone_energy}/{mirror_energy}"
        )
        add_line(0, header, curses.A_REVERSE)
        if zoom_level < 2:
            add_line(1, " " * w)
        if self.glass_mode and h > 4:
            try:
                self.stdscr.addnstr(1, 0, ("." * max(1, w)), w, curses.A_DIM)
            except curses.error:
                pass
        self._draw_tabs(w)
        if zoom_level < 2:
            add_line(2, "-" * max(1, w))

        top = 2 if zoom_level >= 2 else 3
        bottom = max(top + 1, h - 3)
        usable = max(1, bottom - top)
        all_lines = self._pane_lines()
        max_scroll = max(0, len(all_lines) - usable)
        self.pane_scroll = max(0, min(self.pane_scroll, max_scroll))
        start = max(0, len(all_lines) - usable - self.pane_scroll)
        lines = all_lines[start : start + usable]
        row = top
        for line in lines:
            if row >= bottom:
                break
            add_line(row, line)
            row += 1
        if self.glass_mode:
            self._draw_core_face(h, w, top, bottom)
        self._draw_scrollbar(h, w, top, bottom, len(all_lines), usable)

        add_line(h - 2, "-" * max(1, w))
        prompt = f"{self.pane}> {self.input_buffer}"
        add_line(h - 1, prompt)
        cursor_x = max(0, min(w - 1, len(self.pane) + 2 + len(self.input_buffer)))
        try:
            self.stdscr.move(h - 1, cursor_x)
        except curses.error:
            pass
        try:
            self.stdscr.refresh()
        except curses.error:
            pass
        self.last_render_ts = time.time()
        self.dirty = False

    def _draw_tabs(self, w: int) -> None:
        self.tab_ranges = []
        x = 0
        anim_active = (time.time() - self.last_activity_ts) <= self.activity_anim_window_sec
        phase = int(time.time() * 8) if anim_active else 0
        for idx, name in enumerate(PANES):
            token = self._tab_token(idx, name)
            start = x
            end = x + len(token)
            self.tab_ranges.append((start, end, idx))
            if x >= w:
                break
            attr = 0
            if self.use_color and self.tab_color_pairs:
                pair_idx = self.tab_color_pairs[idx % len(self.tab_color_pairs)]
                if idx == self.pane_index:
                    pair_idx = self.tab_color_pairs[(idx + phase) % len(self.tab_color_pairs)]
                attr |= curses.color_pair(pair_idx)
            if idx == self.pane_index:
                attr |= curses.A_BOLD | curses.A_REVERSE
            elif self.hovered_tab_index == idx:
                attr |= curses.A_STANDOUT
                if self.glass_mode:
                    attr |= curses.A_BOLD
            try:
                self.stdscr.addnstr(1, x, token, max(0, w - x), attr)
            except curses.error:
                return
            x = end + 1

    def _tab_token(self, idx: int, name: str) -> str:
        base_label = f"{idx + 1}:{name}"
        if idx == 9:
            base_label = f"0:{name}"
        base = f"[{base_label}]"
        if self.hovered_tab_index != idx:
            if self.ui_profile == "touch":
                return f" {base} "
            return base
        dwell = max(0.0, time.time() - self.hover_enter_ts)
        if dwell < self.hover_expand_delay_sec:
            return base if self.ui_profile != "touch" else f" {base} "
        scale = 1 + int((dwell - self.hover_expand_delay_sec) / 0.25)
        scale = max(1, min(self.max_tab_expand, scale))
        pad = " " * scale
        if self.glass_mode:
            pulse = int((time.time() - self.hover_enter_ts) * 10) % 4
            wave = "~" if pulse in {1, 2} else " "
            return f"[{wave}{pad}{base_label}{pad}{wave}]"
        return f"[{pad}{base_label}{pad}]"

    def _draw_core_face(self, h: int, w: int, top: int, bottom: int) -> None:
        if bottom - top < 4 or w < 40:
            return
        mirror = self._mirror_pane(self.pane) or "-"
        core = f"< core face :: {self.pane.lower()} <> {mirror.lower()} :: {self.status} >"
        y = top + max(0, (bottom - top) // 3)
        x = max(0, (w - len(core)) // 2)
        try:
            self.stdscr.addnstr(y, x, core, max(1, w - x), curses.A_DIM)
        except curses.error:
            return

    def _wallpaper_fill(self, y: int, w: int) -> str:
        palette = [".", ":", ";", "~"]
        intensity = min(3, max(0, self.activity_wallpaper_score // 5))
        ch = palette[intensity]
        phase = int(time.time() * 3)
        if (y + phase) % 3 == 0:
            ch = palette[min(3, intensity + 1)]
        return ch * max(0, w)

    def _surface_zoom_level(self) -> int:
        idle = max(0.0, time.time() - self.last_input_ts)
        mirror_boost = self._mirror_energy(self.pane)
        if mirror_boost > 2.5:
            return 2
        if mirror_boost > 1.2:
            return 1
        if idle >= self.zoom_step2_delay_sec:
            return 2
        if idle >= self.zoom_step1_delay_sec:
            return 1
        return 0

    def _apply_scroll_inertia(self) -> None:
        now = time.time()
        dt = max(0.0, now - self.last_physics_ts)
        self.last_physics_ts = now
        # Zone-flow decay + coupling drift.
        for pane in PANES:
            cur = float(self.zone_flow.get(pane, 0.0))
            if cur > 0:
                cur = max(0.0, cur - self.zone_flow_decay * dt)
            elif cur < 0:
                cur = min(0.0, cur + self.zone_flow_decay * dt)
            self.zone_flow[pane] = cur

        mirror = self._mirror_pane(self.pane)
        if mirror:
            # Mirror inertia influences local flow and scroll speed.
            self.zone_flow[self.pane] = float(self.zone_flow.get(self.pane, 0.0)) + (
                float(self.zone_flow.get(mirror, 0.0)) * self.mirror_flow_strength * dt
            )

        if abs(self.scroll_velocity) < 0.05:
            self.scroll_velocity = 0.0
            return
        flow_amp = 1.0 + min(1.5, self._zone_energy(self.pane) * 0.2)
        self.pane_scroll += int(self.scroll_velocity * dt * flow_amp)
        if self.pane_scroll < 0:
            self.pane_scroll = 0
            self.scroll_velocity = 0.0
        if self.scroll_velocity > 0:
            self.scroll_velocity = max(0.0, self.scroll_velocity - self.inertia_decay * dt * 10)
        else:
            self.scroll_velocity = min(0.0, self.scroll_velocity + self.inertia_decay * dt * 10)
        self.dirty = True

    def _feedback_mode(self) -> str:
        local = float(self.zone_flow.get(self.pane, 0.0))
        mirror = 0.0
        mirrored = self._mirror_pane(self.pane)
        if mirrored:
            mirror = float(self.zone_flow.get(mirrored, 0.0))
        flow_energy = abs(local) + abs(mirror)
        if flow_energy < self.feedback_flow_threshold:
            return "idle"
        if (local > 0 and mirror < 0) or (local < 0 and mirror > 0):
            return "inversion"
        return "surge"

    def _emit_audio_feedback(self, mode: str) -> None:
        if not self.audio_feedback_enabled:
            return
        try:
            # Frequency-like response: inversion emits 2 pulses, surge emits 1.
            if mode == "inversion":
                curses.beep()
                time.sleep(0.015)
                curses.beep()
            elif mode == "surge":
                curses.beep()
            else:
                return
        except curses.error:
            try:
                curses.flash()
            except curses.error:
                return

    def _emit_haptic_feedback(self, mode: str) -> None:
        if not self.haptic_feedback_enabled or mode == "idle":
            return
        now = time.time()
        event = {
            "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "pane": self.pane,
            "mode": mode,
            "local_flow": round(float(self.zone_flow.get(self.pane, 0.0)), 3),
            "mirror_flow": round(float(self.zone_flow.get(self._mirror_pane(self.pane) or "", 0.0)), 3),
            "pattern": "dual_pulse" if mode == "inversion" else "single_pulse",
        }
        try:
            self.bridge_root.mkdir(parents=True, exist_ok=True)
            with self.haptic_queue_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, ensure_ascii=True) + "\n")
        except OSError:
            return

    def _emit_mirror_feedback(self) -> None:
        now = time.time()
        if now - self.last_feedback_ts < self.feedback_min_interval_sec:
            return
        mode = self._feedback_mode()
        if mode == "idle":
            self.last_feedback_mode = mode
            return
        if mode == self.last_feedback_mode and (now - self.last_feedback_ts) < (self.feedback_min_interval_sec * 2):
            return
        self._emit_audio_feedback(mode)
        self._emit_haptic_feedback(mode)
        self.last_feedback_ts = now
        self.last_feedback_mode = mode

    def _ambient_color(self, mode: str, local: float, mirror: float) -> list[int]:
        # Palette approximates ambient mirror states for external RGB devices.
        if mode == "inversion":
            return [40, 180, 255]
        if mode == "surge":
            return [255, 130, 40]
        if local >= 0 and mirror >= 0:
            return [80, 220, 110]
        return [180, 80, 255]

    def _emit_ambient_vector(self) -> None:
        if not self.ambient_light_enabled:
            return
        now = time.time()
        if now - self.last_ambient_emit_ts < self.ambient_light_interval_sec:
            return
        local = float(self.zone_flow.get(self.pane, 0.0))
        mirrored_pane = self._mirror_pane(self.pane)
        mirror = float(self.zone_flow.get(mirrored_pane or "", 0.0))
        mode = self._feedback_mode()
        energy = abs(local) + abs(mirror)
        brightness = int(min(max(12, energy * 28), max(16, self.ambient_light_max_brightness)))
        payload = {
            "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "profile": "aura_ambient_mirror",
            "pane": self.pane,
            "mirror_pane": mirrored_pane or "",
            "mode": mode,
            "vector": {
                "rgb": self._ambient_color(mode, local, mirror),
                "brightness_pct": brightness,
                "wave_hz": round(0.35 + min(3.2, energy * 0.55), 3),
                "phase": "anti" if ((local > 0 > mirror) or (local < 0 < mirror)) else "aligned",
                "flow_energy": round(energy, 3),
            },
            "mirrored": {
                "local_flow": round(local, 3),
                "mirror_flow": round(mirror, 3),
            },
            "source": "interactionface",
        }
        try:
            self.bridge_root.mkdir(parents=True, exist_ok=True)
            self.ambient_vector_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
            with self.ambient_vector_queue_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=True) + "\n")
        except OSError:
            return
        self.last_ambient_emit_ts = now

    def _draw_scrollbar(self, h: int, w: int, top: int, bottom: int, total_lines: int, usable: int) -> None:
        if w < 20 or total_lines <= usable:
            return
        track_top = top
        track_bottom = bottom - 1
        track_h = max(1, track_bottom - track_top + 1)
        thumb_h = max(1, int(track_h * (usable / max(1, total_lines))))
        max_scroll = max(1, total_lines - usable)
        scroll = max(0, min(max_scroll, self.pane_scroll))
        thumb_offset = int((track_h - thumb_h) * (scroll / max_scroll))
        col = w - 1
        for y in range(track_top, track_bottom + 1):
            ch = "|" if not (thumb_offset <= (y - track_top) < thumb_offset + thumb_h) else "#"
            try:
                self.stdscr.addch(y, col, ch)
            except curses.error:
                break

    def _submit(self) -> None:
        line = self.input_buffer.strip()
        self.input_buffer = ""
        if not line:
            return
        self.add_log(f"> {line}")
        result = self.hub.execute(line)
        if result.payload.get("quit"):
            self.running = False
            return
        prefix = "ok" if result.ok else "err"
        self.add_log(f"[{prefix}] {result.title}")
        self.add_log(json.dumps(result.payload, ensure_ascii=True, indent=2))
        self.pane_scroll = 0
        self.pane_cache.clear()
        self.pane_cache_ts.clear()
        self.last_activity_ts = time.time()

    def _on_mouse(self) -> None:
        try:
            _, mx, my, _, bstate = curses.getmouse()
        except curses.error:
            return

        new_hover: int | None = None
        if my >= (1 - self.touch_hit_zone_extra_rows) and my <= (1 + self.touch_hit_zone_extra_rows):
            for start, end, idx in self.tab_ranges:
                if start <= mx < end:
                    new_hover = idx
                    break
        if new_hover != self.hovered_tab_index:
            self.hovered_tab_index = new_hover
            self.hover_enter_ts = time.time() if new_hover is not None else 0.0
            self.dirty = True
            self.last_activity_ts = time.time()

        if (my >= (1 - self.touch_hit_zone_extra_rows) and my <= (1 + self.touch_hit_zone_extra_rows)) and new_hover is not None:
            btn1_click = getattr(curses, "BUTTON1_CLICKED", 0)
            btn1_press = getattr(curses, "BUTTON1_PRESSED", 0)
            if bstate & (btn1_click | btn1_press):
                self.pane_index = new_hover
                self.pane_scroll = 0
                self.dirty = True
                self.last_activity_ts = time.time()
                self.last_input_ts = time.time()
                self.last_input_kind = "mouse_click"
                return

        if bstate & curses.BUTTON4_PRESSED:  # wheel up
            self.pane_scroll += 2
            self.scroll_velocity += self.inertia_gain
            self._inject_zone_flow(self.pane, 0.8)
            self.dirty = True
            self.last_activity_ts = time.time()
            self.last_input_ts = time.time()
            self.last_input_kind = "mouse_wheel"
            return
        if bstate & curses.BUTTON5_PRESSED:  # wheel down
            self.pane_scroll -= 2
            self.scroll_velocity -= self.inertia_gain
            self._inject_zone_flow(self.pane, -0.8)
            if self.pane_scroll < 0:
                self.pane_scroll = 0
            self.dirty = True
            self.last_activity_ts = time.time()
            self.last_input_ts = time.time()
            self.last_input_kind = "mouse_wheel"
            return

    def run(self) -> int:
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        self.stdscr.nodelay(False)
        self.stdscr.timeout(self.input_timeout_ms)
        self.stdscr.keypad(True)
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

        while self.running:
            self._poll_health()
            self._poll_activity_wallpaper()
            self._apply_scroll_inertia()
            self._emit_mirror_feedback()
            self._emit_ambient_vector()
            now = time.time()
            has_recent_activity = (now - self.last_activity_ts) <= self.activity_anim_window_sec
            zone_intensity = self._zone_energy(self.pane) + self._mirror_energy(self.pane)
            base_interval = self.frame_interval_sec if has_recent_activity else self.idle_frame_interval_sec
            accel_factor = 1.0 / (1.0 + min(2.0, zone_intensity * 0.35))
            target_interval = max(0.03, base_interval * accel_factor)
            if self.dirty or (now - self.last_render_ts) >= target_interval:
                try:
                    self._render()
                except curses.error:
                    time.sleep(0.03)
                    continue
            ch = self.stdscr.getch()
            if ch == -1:
                continue
            if ch in (3, 4):  # Ctrl-C / Ctrl-D
                break
            if ch in (10, 13):
                self._submit()
                self._inject_zone_flow(self.pane, 0.25)
                self.last_input_ts = time.time()
                self.last_input_kind = "keyboard_enter"
                continue
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                self.input_buffer = self.input_buffer[:-1]
                self._inject_zone_flow(self.pane, -0.05)
                self.dirty = True
                self.last_activity_ts = time.time()
                self.last_input_ts = time.time()
                self.last_input_kind = "keyboard"
                continue
            if ch == 9:  # Tab
                self.pane_index = (self.pane_index + 1) % len(PANES)
                self._inject_zone_flow(self.pane, 0.5)
                self.dirty = True
                self.last_activity_ts = time.time()
                self.last_input_ts = time.time()
                self.last_input_kind = "keyboard_nav"
                continue
            if ch in (ord("1"), ord("2"), ord("3"), ord("4"), ord("5"), ord("6"), ord("7"), ord("8"), ord("9"), ord("0")):
                pane = 9 if ch == ord("0") else int(chr(ch)) - 1
                if pane >= len(PANES):
                    continue
                self.pane_index = pane
                self.pane_scroll = 0
                self._inject_zone_flow(self.pane, 0.7)
                self.dirty = True
                self.last_activity_ts = time.time()
                self.last_input_ts = time.time()
                self.last_input_kind = "keyboard_hotkey"
                continue
            if ch == curses.KEY_MOUSE:
                self._on_mouse()
                self.last_input_ts = time.time()
                self.last_input_kind = "mouse"
                continue
            if ch == curses.KEY_PPAGE:
                self.pane_scroll += 10
                self.scroll_velocity += self.inertia_gain * 1.5
                self._inject_zone_flow(self.pane, 1.1)
                self.dirty = True
                self.last_activity_ts = time.time()
                self.last_input_ts = time.time()
                self.last_input_kind = "keyboard_scroll"
                continue
            if ch == curses.KEY_NPAGE:
                self.pane_scroll = max(0, self.pane_scroll - 10)
                self.scroll_velocity -= self.inertia_gain * 1.5
                self._inject_zone_flow(self.pane, -1.1)
                self.dirty = True
                self.last_activity_ts = time.time()
                self.last_input_ts = time.time()
                self.last_input_kind = "keyboard_scroll"
                continue
            if ch == curses.KEY_UP:
                self.pane_scroll += 2
                self.scroll_velocity += self.inertia_gain * 0.35
                self._inject_zone_flow(self.pane, 0.35)
                self.dirty = True
                self.last_activity_ts = time.time()
                self.last_input_ts = time.time()
                self.last_input_kind = "keyboard_scroll"
                continue
            if ch == curses.KEY_DOWN:
                self.pane_scroll = max(0, self.pane_scroll - 2)
                self.scroll_velocity -= self.inertia_gain * 0.35
                self._inject_zone_flow(self.pane, -0.35)
                self.dirty = True
                self.last_activity_ts = time.time()
                self.last_input_ts = time.time()
                self.last_input_kind = "keyboard_scroll"
                continue
            if ch == curses.KEY_RIGHT:
                self.pane_index = (self.pane_index + 1) % len(PANES)
                self.pane_scroll = 0
                self._inject_zone_flow(self.pane, 0.45)
                self.dirty = True
                self.last_activity_ts = time.time()
                self.last_input_ts = time.time()
                self.last_input_kind = "keyboard_nav"
                continue
            if ch == curses.KEY_LEFT:
                self.pane_index = (self.pane_index - 1 + len(PANES)) % len(PANES)
                self.pane_scroll = 0
                self._inject_zone_flow(self.pane, -0.45)
                self.dirty = True
                self.last_activity_ts = time.time()
                self.last_input_ts = time.time()
                self.last_input_kind = "keyboard_nav"
                continue
            if ch == 27:  # ESC clears input
                self.input_buffer = ""
                self.dirty = True
                self.last_activity_ts = time.time()
                self.last_input_ts = time.time()
                self.last_input_kind = "keyboard"
                continue
            if 32 <= ch <= 126:
                self.input_buffer += chr(ch)
                self._inject_zone_flow(self.pane, 0.08)
                self.dirty = True
                self.last_activity_ts = time.time()
                self.last_input_ts = time.time()
                self.last_input_kind = "keyboard"
        return 0


def _main(stdscr) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    app = LamConsoleUI(stdscr, repo_root=repo_root)
    return app.run()


def main() -> int:
    return int(curses.wrapper(_main))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        sys.exit(130)
