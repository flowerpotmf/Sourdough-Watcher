# Sourdough Watcher — Home Assistant Integration

A Home Assistant custom integration (installable via HACS) that helps you monitor and manage your sourdough starter. Track feeding schedules, weights, discard amounts, and get plain-text instructions for each stage of the recipe.

> Forked from [Matt's Baps' ha-sourdough](https://github.com/Matts-Baps/ha-sourdough) and customised — most notably with a **configurable maintenance feeding interval** so the integration supports both daily room-temperature feeding and fridge-stored, weekly-fed routines such as Hendrik Kleinwächter's [*The Sourdough Framework*](https://www.the-sourdough-framework.com/).

---

## Features

- **Recipe-aware schedule** — automatically tracks Days 1–7 and switches between 24-hour and 12-hour feeding intervals at the right time.
- **Configurable maintenance interval** — once the starter is mature (Day 8+), feed it as often as your routine demands. Keep the default 12h for a room-temperature starter, or set 168h (7 days) for a fridge-stored starter fed weekly. Changeable any time via **Configure**, or switch presets straight from the dashboard with the **Maintenance Cadence** selector.
- **Optional maintenance discard** — turn discarding off during maintenance (via the **Discard During Maintenance** switch or options) if you keep a small amount of starter instead, as fridge/weekly routines often do.
- **"Feeding Due" binary sensor** — a ready-made `binary_sensor` (device class *problem*) so notifications and dashboards don't need to template attributes.
- **Peak / rise-time tracking** — log when the starter peaks (via the **Log Peak** button or the `sourdough.log_peak` service, which can be back-dated) and the integration records how long it took to rise since the last feeding. **Last Rise Time** and **Average Rise Time** sensors keep long-term history so you can watch how lively your starter is over time.
- **Starter & flour type** — tag each starter as **liquid** or **stiff** (per *The Sourdough Framework*) and record the flour it's maintained on (wheat, rye, spelt…). Descriptive metadata that makes multiple starters easy to tell apart.
- **Multiple starters** — add the integration more than once to track several starters (e.g. a wheat and a rye starter) side by side; each gets its own name, device, entities, and history.
- **Skip / snooze** — a **Skip Feeding** button (and `sourdough.skip_feeding` service) pushes the next feeding forward one interval without logging a feeding.
- **Feeding calendar** — past feedings, logged peaks, and the next due feeding appear as a Home Assistant calendar entity.
- **Vessel/jar tare tracking** — enter your empty jar weight so the integration can calculate starter-only weight from a scale reading.
- **Metric & Imperial** — configure in either system; all data is stored in grams and converted for display.
- **Custom ratios** — override the default flour/water amounts and discard ratio to match your own recipe.
- **Persistent storage** — feeding history survives Home Assistant restarts.
- **Services** — record feedings, log a peak, skip a feeding, and reset the process from automations or the UI.

---

## Installation via HACS

1. Open HACS → **Integrations** → click the three-dot menu → **Custom repositories**.
2. Add `https://github.com/flowerpotmf/Sourdough-Watcher` as an **Integration**.
3. Search for **Sourdough Monitor** and install it.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration** and search for **Sourdough Monitor**.

### Updating

New versions are published as GitHub releases. When one is available, HACS shows
an update for **Sourdough Monitor** and it appears under **Settings → Updates** in
Home Assistant — update from there and restart. No manual file copying required.

---

## Configuration

During setup you will be asked for:

| Field | Description | Default |
|-------|-------------|---------|
| Starter name | A name for this starter (e.g. "Rye Starter"); used as the device name | Sourdough Starter |
| Unit System | Metric (g) or Imperial (oz) for display | Metric |
| Flour per feeding | Amount of flour added at each feeding | 60 g (½ cup) |
| Water per feeding | Amount of water added at each feeding | 60 g (¼ cup) |
| Vessel tare weight | Weight of your empty jar/container | 0 (disabled) |
| Discard ratio | Fraction discarded before feeding on Day 3+ | 0.5 (50%) |
| Maintenance feeding interval | How often to feed once mature (Day 8+), in hours | 12 h |
| Discard during maintenance | Whether to discard before each maintenance feeding | On |
| Starter type | Liquid (≈100% hydration) or stiff (≈50-60%) — descriptive | Liquid |
| Flour type | Wheat, whole wheat, rye, spelt… — descriptive | Wheat / White |

Everything except the name can be changed later via **Configure** on the integration card.

### Tracking multiple starters

Keep more than one starter (e.g. a wheat and a rye starter)? Just **Add Integration → Sourdough Monitor** again and give it a different name. Each entry becomes its own device with its own entities and feeding/peak history. Services accept an optional `entry_id` to target a specific starter.

### Maintenance feeding interval

For the first week the schedule is fixed by the establishment recipe (Days 1–7).
From **Day 8** onward the starter is "mature" and the **maintenance feeding
interval** takes over. This is fully configurable (1–720 hours):

- **12 h** (default) — a starter kept at room temperature and fed twice a day.
- **24 h** — once-daily room-temperature feeding.
- **168 h** — a fridge-stored starter fed **once a week**, as recommended by
  Hendrik Kleinwächter's *The Sourdough Framework*.

The `Next Feeding Due` sensor, overdue logic, and instructions all follow this
value, so weekly feeders no longer get spurious "feeding overdue" alerts.

### Peak / rise-time tracking

When your starter has fully risen ("peaked"), tap the **Log Peak** button or call
`sourdough.log_peak`. The integration measures the **rise time** — the hours
between the most recent feeding and the peak — and stores it. The
`sensor.sourdough_last_rise_time` and `sensor.sourdough_average_rise_time` sensors
expose this with long-term statistics, so you can chart how your starter's vigour
changes with temperature, flour, or season. Missed the exact moment? Call the
service with a `timestamp` to back-date the peak. Logged peaks also appear on the
feeding calendar.

---

## Sensors

| Entity | Description |
|--------|-------------|
| `sensor.sourdough_current_day` | Recipe day number |
| `sensor.sourdough_phase` | Initialization / Establishment / Activation / Maintenance |
| `sensor.sourdough_next_feeding_due` | Timestamp when the next feeding is due |
| `sensor.sourdough_last_fed` | Timestamp of the most recent recorded feeding |
| `sensor.sourdough_starter_weight` | Estimated starter weight (excluding vessel) |
| `sensor.sourdough_total_weight_with_vessel` | Starter + vessel tare weight |
| `sensor.sourdough_vessel_tare_weight` | Configured empty vessel weight |
| `sensor.sourdough_flour_to_add` | Flour amount for the next feeding |
| `sensor.sourdough_water_to_add` | Water amount for the next feeding |
| `sensor.sourdough_discard_amount` | How much starter to discard before feeding |
| `sensor.sourdough_hydration` | Water/flour ratio as a percentage (with `starter_type` / `flour_type` attributes) |
| `sensor.sourdough_total_feedings` | Count of feedings recorded |
| `sensor.sourdough_last_peak` | Timestamp of the most recent logged peak |
| `sensor.sourdough_last_rise_time` | Rise time (hours) of the most recent peak — long-term history enabled |
| `sensor.sourdough_average_rise_time` | Average rise time across all logged peaks |
| `sensor.sourdough_instructions` | Plain-text instructions for the current step |

Weight sensors include both grams and ounces as extra attributes, regardless of the configured unit system. Flour/water sensors also include a `volume_hint` attribute (e.g., `"1/2 cup"`) for convenience. The rise-time sensors carry the `measurement` state class, so Home Assistant keeps long-term statistics you can graph with a History or Statistics card.

### Other entities

| Entity | Description |
|--------|-------------|
| `binary_sensor.sourdough_feeding_due` | On when a feeding is due/overdue (device class *problem*) |
| `select.sourdough_maintenance_cadence` | Quick preset switch for the Day 8+ interval (12h / 24h / 48h / weekly) |
| `switch.sourdough_discard_during_maintenance` | Toggle discarding during the maintenance phase |
| `button.sourdough_record_feeding` | Record a feeding using the configured amounts |
| `button.sourdough_log_peak` | Log that the starter has reached its peak (records rise time) |
| `button.sourdough_skip_feeding` | Skip (snooze) the next feeding by one interval |
| `button.sourdough_reset_process` | Reset the process back to Day 1 |
| `number.sourdough_current_day` | Set the current recipe day (for mid-recipe setup) |
| `number.sourdough_current_weight_with_vessel` | Record the measured weight as a baseline |
| `calendar.sourdough_feeding_schedule` | Past feedings, logged peaks, and the next due feeding |

---

## Services

### `sourdough.record_feeding`

Record that you have fed your starter. Call this after each feeding.

```yaml
service: sourdough.record_feeding
data:
  # All fields are optional — omit to use configured defaults
  flour: 60       # grams (or oz if configured for imperial)
  water: 60       # grams (or oz if configured for imperial)
  discarded: 60   # grams (or oz) — omit on Days 1 & 2
```

### `sourdough.log_peak`

Record that the starter has reached its peak (fully risen). The rise time —
hours since the last feeding — is calculated and stored, building a history of
how quickly your starter rises. Provide a `timestamp` to log a peak you noticed
after the fact (so you don't have to catch the exact moment).

```yaml
service: sourdough.log_peak
data:
  # Optional — omit to log "now". Back-date if you noticed it had already peaked.
  timestamp: "2026-03-08 14:30:00"
```

### `sourdough.skip_feeding`

Skip (snooze) the upcoming feeding by one interval without logging a feeding.
The skip is cleared automatically the next time a feeding is recorded.

```yaml
service: sourdough.skip_feeding
```

### `sourdough.reset_process`

Restart from Day 1 with an empty feeding log.

```yaml
service: sourdough.reset_process
```

If you have multiple sourdough trackers, add `entry_id` to target a specific one.

---

## Automation Examples

### Notify when a feeding is due

Triggers at the exact moment the next feeding time is reached.

```yaml
automation:
  - alias: "Sourdough — feeding due"
    trigger:
      - platform: time
        at: sensor.sourdough_next_feeding_due
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🍞 Sourdough needs feeding"
          message: "{{ states('sensor.sourdough_instructions') }}"
```

### Escalating alert when a feeding is overdue

Reminds you every 30 minutes once the feeding window has passed.

```yaml
automation:
  - alias: "Sourdough — feeding overdue reminder"
    trigger:
      - platform: template
        value_template: "{{ state_attr('sensor.sourdough_phase', 'is_overdue') }}"
        for:
          minutes: 30
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⚠️ Sourdough overdue"
          message: >
            Feeding overdue by
            {{ (state_attr('sensor.sourdough_phase', 'overdue_minutes') | int) // 60 }}h
            {{ (state_attr('sensor.sourdough_phase', 'overdue_minutes') | int) % 60 }}m.
            {{ states('sensor.sourdough_instructions') }}
```

### Announce on a smart speaker when feeding is due

```yaml
automation:
  - alias: "Sourdough — speaker announcement"
    trigger:
      - platform: time
        at: sensor.sourdough_next_feeding_due
    action:
      - service: tts.speak
        target:
          entity_id: media_player.kitchen_speaker
        data:
          message: "Time to feed your sourdough starter. {{ states('sensor.sourdough_instructions') }}"
```

### Record a feeding from a dashboard button

Use alongside the built-in **Record Feeding** button entity, or call the service directly from a script.

```yaml
script:
  feed_sourdough:
    alias: "Feed Sourdough"
    sequence:
      - service: sourdough.record_feeding
        data:
          discarded: "{{ states('sensor.sourdough_discard_amount') | float }}"
```

### Flash a light when feeding is due

Handy if you want a physical reminder without your phone.

```yaml
automation:
  - alias: "Sourdough — light reminder"
    trigger:
      - platform: time
        at: sensor.sourdough_next_feeding_due
    action:
      - repeat:
          count: 3
          sequence:
            - service: light.turn_on
              target:
                entity_id: light.kitchen
              data:
                color_name: orange
            - delay: "00:00:02"
            - service: light.turn_off
              target:
                entity_id: light.kitchen
            - delay: "00:00:02"
```

### Daily summary notification

Get a morning briefing on your starter's status.

```yaml
automation:
  - alias: "Sourdough — daily summary"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🍞 Sourdough update"
          message: >
            Day {{ states('sensor.sourdough_current_day') }}
            ({{ states('sensor.sourdough_phase') }}).
            Next feeding: {{ states('sensor.sourdough_next_feeding_due') | as_timestamp | timestamp_custom('%H:%M') }}.
            Starter weight: {{ states('sensor.sourdough_starter_weight') }}{{ state_attr('sensor.sourdough_starter_weight', 'unit_of_measurement') }}.
```

### Log feedings to a helper for history tracking

Create a **Text** helper (`input_text.sourdough_log`) in HA, then append to it on every feeding.

```yaml
automation:
  - alias: "Sourdough — log feeding"
    trigger:
      - platform: state
        entity_id: sensor.sourdough_total_feedings
    action:
      - service: input_text.set_value
        target:
          entity_id: input_text.sourdough_log
        data:
          value: >
            Last fed {{ now().strftime('%d %b %H:%M') }},
            Day {{ states('sensor.sourdough_current_day') }},
            {{ states('sensor.sourdough_starter_weight') }}g starter.
```

---

## Recipe Reference

The default schedule follows this recipe:

| Days | Interval | Discard? | Action |
|------|----------|----------|--------|
| 1–2  | 24 h     | No       | Mix flour + water |
| 3–5  | 24 h     | Yes (50%)| Discard half, then feed |
| 6–7  | 12 h     | Yes (50%)| Discard half, then feed twice per day |
| 8+   | **Configurable** (default 12 h) | Yes (50%)| Maintenance — feed on your chosen interval |

The Day 8+ interval is set by the **maintenance feeding interval** option (see
[Configuration](#maintenance-feeding-interval)). Set it to 168 h for a
fridge-stored, weekly-fed starter.

**Signs your starter is active:** bubbly, doubled or tripled in size, and floats in water.

Default amounts: **½ cup flour (60 g)** + **¼ cup water (60 g)** = 100% hydration.

---

## Unit Conversion Reference

| Volume | Flour (AP) | Water |
|--------|-----------|-------|
| 1 cup | ~120 g / 4.2 oz | 240 g / 8.5 oz |
| ½ cup | ~60 g / 2.1 oz | 120 g / 4.2 oz |
| ¼ cup | ~30 g / 1.1 oz | 60 g / 2.1 oz |
| 1 tbsp | ~7.5 g | 15 g |

*Flour weight varies slightly by type and scooping method. AP flour is used as the reference.*

---

## Recipe Credit

The default feeding schedule is based on the sourdough starter recipe by
[@anabelle.vangiller](https://www.instagram.com/anabelle.vangiller/) on Instagram:
[https://www.instagram.com/p/DSxZ-QKDi7W/](https://www.instagram.com/p/DSxZ-QKDi7W/)

---

## Contributing

Issues and pull requests welcome at `https://github.com/flowerpotmf/Sourdough-Watcher`.

---

## Disclaimer

This integration was written using [Claude Code](https://claude.com/claude-code) (Anthropic's AI coding assistant) and has been reviewed and approved by human maintainers before publication. All logic, schedules, and defaults have been checked for correctness, but as with any community integration, use it at your own discretion.
