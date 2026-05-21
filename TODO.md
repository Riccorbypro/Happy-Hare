# CFS Feature Plan and To-Do List

This plan starts from the current milestone: basic feeding and retracting
filament works. The next work should preserve that baseline while adding CFS
hardware features in small, testable steps.

## Guiding Principles

- Keep filament movement safe while adding features.
- Add observability before automatic control.
- Prefer Klipper-native primitives where they fit.
- Treat CFS-specific hardware as optional until it is proven on the printer.
- Update `docs/cfs.md` whenever a planned hardware feature becomes real.

## 1. Temperature and Humidity Sensor

Pins: `PC11`, `PC12` on I2C.

Goal: read the CFS internal temperature and humidity and expose it through Happy
Hare as the MMU environment sensor.

Tasks:

- Identify the actual sensor IC used by the CFS.
- Confirm I2C bus mapping and whether `PC11` is SDA or SCL on the CFS MCU.
- Check whether Klipper already supports the sensor.
- Add a Klipper config section for the sensor if native support exists.
- If native support does not exist, add or port a small Klipper extra module.
- Set `[mmu_machine] environment_sensor` to the new sensor object.
- Verify readings in Klipper status and Happy Hare UI/status output.
- Document calibration offsets, polling rate, and failure behavior.

Acceptance criteria:

- Temperature and humidity update without blocking MMU movement.
- Sensor failure does not prevent filament movement unless explicitly configured
  to do so.
- Values appear in Happy Hare status as the CFS environment reading.

## 2. RFID Filament Identification

Pins:

- RFID reader 1 I2C: `PB11`, `PB10`
- RFID reader 2 I2C: `PB9`, `PB8`

Goal: read CFS RFID tags and map tag data to Happy Hare gate metadata such as
material, color, temperature, and spool identity.

Tasks:

- Identify the RFID reader IC and protocol.
- Confirm which lanes each reader physically covers.
- Determine whether tags are read continuously, on insertion, or through a
  reader-select mechanism.
- Build a read-only proof of concept that logs raw tag IDs/data.
- Define a mapping layer from tag data to Happy Hare gate fields.
- Decide whether mapping belongs in Happy Hare, Moonraker/Spoolman integration,
  or a separate helper module.
- Add commands or status fields for "last tag seen" per reader/lane.
- Add debouncing and stale-tag handling.
- Document how users pair unknown tags with filament metadata.

Acceptance criteria:

- Both RFID readers can be queried independently.
- Tag data is visible in logs/status without changing gate state unexpectedly.
- A user can map a known tag to a gate's filament metadata.

## 3. Espooler Current Feedback and Active Rewind Control

Pins:

- Lane 0 current feedback: `PC5`
- Lane 1 current feedback: `PC0`
- Lane 2 current feedback: `PA1`
- Lane 3 current feedback: `PA0`

Goal: use espooler current feedback to keep rewinding fast enough during BLDC
unloads without pulling so hard or so slowly that filament tangles inside the
CFS.

Tasks:

- Confirm whether the current feedback pins are analog ADC inputs or digital
  threshold outputs.
- Add read-only current telemetry per lane.
- Log current readings alongside `ESPOOLER` and `BLDC_ENCODER_POSITION` events.
- Characterize normal current during idle, assist, rewind, stall, and empty
  spool conditions.
- Change `[mmu_espooler]` to proportional PWM mode only after the hardware path
  is proven safe.
- Add per-lane feedback parameters:
  - minimum current for active motor detection
  - high-current/stall threshold
  - low-current/freewheel threshold
  - speed increase/decrease step
  - maximum rewind power
- Implement a closed-loop rewind controller that can slow the BLDC or increase
  espooler power when the spool cannot keep up.
- Add a hard safety stop when current feedback suggests a jam or runaway.
- Add test commands for telemetry and controlled rewind tuning.

Acceptance criteria:

- Current feedback is visible per lane.
- Rewind control can detect "not keeping up" before a tangle forms.
- The BLDC unload path can reduce speed or pause when respooling is unsafe.
- Failure modes stop movement and leave a clear message in `mmu.log`.

## 4. Filament Status LEDs

Hardware: eight discrete outputs, four red and four white LEDs, one of each
color per lane.

Goal: provide useful lane status indication even though Happy Hare's current LED
mapping expects neopixel-style addressable LEDs.

Tasks:

- Identify the eight LED pins and active polarity.
- Add simple Klipper `output_pin` definitions for each LED as a proof of
  concept.
- Decide whether to implement a CFS-specific LED manager or extend Happy Hare's
  LED abstraction for discrete two-color LEDs.
- Define lane states:
  - empty
  - filament present
  - selected
  - loading/unloading
  - error
- Map each state to red/white behavior.
- Add a config option to enable/disable CFS discrete LED control.
- Avoid pretending these LEDs are neopixels unless an adapter abstraction is
  added intentionally.

Acceptance criteria:

- Each red and white LED can be controlled independently.
- Happy Hare lane state changes can update the LEDs.
- LED errors do not affect filament movement.

## 5. Front Display Communication

Pins:

- Display comms: `PC1`, `PC2`, `PC3`, `PC4`
- Backlight: `PB0`

Goal: restore the stock-style exterior display behavior, starting with
temperature and humidity display.

Tasks:

- Identify the display controller and physical protocol.
- Determine what `PC1`-`PC4` represent: SPI, parallel, bit-banged serial, custom
  protocol, or control lines.
- Confirm `PB0` backlight polarity and safe PWM range.
- Create a standalone display probe that can turn the backlight on/off without
  touching filament movement.
- Capture or infer the stock display protocol if needed.
- Implement a minimal display driver that shows temperature and humidity.
- Add optional status pages only after the basic display is reliable.
- Document what is supported and what remains stock-firmware-only.

Acceptance criteria:

- Backlight can be controlled safely.
- Display can show CFS temperature and humidity.
- Display failure does not prevent the MMU from operating.

## Suggested Milestone Order

1. Read-only sensor work: temperature/humidity, RFID raw reads, current feedback
   telemetry.
2. User-visible but low-risk outputs: LEDs and display backlight.
3. Display temperature/humidity once the environment sensor is stable.
4. RFID-to-gate metadata mapping.
5. Closed-loop espooler rewind control.

## Test Matrix

Run these after each movement-affecting change:

- Gate 0 short load and unload.
- Gate 1 short load and unload.
- Gate 2 short load and unload.
- Gate 3 short load and unload.
- One longer bowden load/unload on the most reliable gate.
- `mmu.log` review for `BLDC_*`, `ESPOOLER`, encoder, and sensor errors.

Run these after each non-movement hardware feature:

- Klipper config restart.
- Status query for the new object.
- Hardware unplug/failure behavior where practical.
- Confirm no change to known-good feed/retract behavior.

