# AI Agent Onboarding

This repository is a CFS-focused Happy Hare fork. The current working goal is to
make the Creality CFS operate as a custom four-lane Type-B-style MMU under
Klipper/Happy Hare.

Start with these files:

1. `docs/cfs.md`
2. `TODO.md`
3. `printer_data/config/mmu/base/mmu_hardware.cfg`
4. `printer_data/config/mmu/base/mmu_parameters.cfg`
5. `printer_data/config/variables.cfg`
6. `extras/mmu/mmu.py`
7. `extras/mmu/mmu_gear_bldc.py`
8. `extras/mmu_espooler.py`

## Ground Rules

- Prefer source and log evidence over guesses.
- Treat `printer_data/config/` as the current printer-side snapshot when it is
  present.
- Treat `printer_data/config/variables.cfg` as live saved state, not as an
  optional artifact.
- Do not assume base Happy Hare defaults explain CFS behavior. The active config
  and saved variables often override constructor defaults.
- Keep changes small and tied to CFS behavior unless the user explicitly asks
  for a broader Happy Hare refactor.

## Current CFS Mental Model

The CFS currently behaves like:

- Four gates.
- No mechanical selector, represented by `VirtualSelector`.
- BLDC filament drive instead of `stepper_mmu_gear`.
- MT6826S encoder for filament movement feedback.
- Four independent respool motors and four assist motors.
- Per-lane pre-gate and post-gear sensors.
- Shared sync-feedback tension/compression sensors.

## Most Important Code Paths

### BLDC Gear

`extras/mmu/mmu_gear_bldc.py` owns the BLDC controller. It handles:

- PWM, direction, and enable pin writes.
- Tachometer sampling.
- PID-style tachometer speed correction.
- Motion queues for standalone BLDC moves.
- Syncing BLDC speed to extruder movement.
- Braking and stopping.

Search terms:

- `MmuGearBldc`
- `BldcTachometer`
- `start_move`
- `_motion_timer_callback`
- `BLDC_SET_PIN`
- `BLDC_TACH`
- `BLDC_CONTROL`

### Movement Integration

`extras/mmu/mmu.py` integrates the BLDC into Happy Hare movement. The most useful
areas are:

- `VARS_MMU_BLDC_MAP`
- `encoder_bounded_bldc`
- `bldc_encoder_*`
- `_wrap_espooler`
- `_stop_wrapped_espooler`
- `trace_filament_move`
- `MMU_TEST_MOVE`
- `MMU_TEST_CONFIG`
- `MMU_ESPOOLER`

The encoder-bounded BLDC path starts a BLDC move, polls encoder distance, stops
or brakes early, waits for settling, and validates the final encoder distance.

### Espooler

`extras/mmu_espooler.py` controls the CFS spool motors. It supports:

- Rewind and assist outputs per gate.
- Burst assist/rewind.
- In-print assist mode.
- Optional assist trigger pins.

Current CFS config uses digital on/off output mode (`pwm: 0`), not proportional
PWM.

## Config Files

`printer_data/config/mmu/base/mmu_hardware.cfg`

- CFS machine profile.
- BLDC gear pins.
- CFS pre-gate/post-gear sensors.
- MT6826S encoder config.
- Espooler motor pins.

`printer_data/config/mmu/base/mmu_parameters.cfg`

- Movement speeds.
- calibration and autotune toggles.
- Encoder-bounded BLDC controls.
- Espooler behavior parameters.
- Macro hook names.

`printer_data/config/variables.cfg`

- Saved calibration and state.
- `mmu_gear_rotation_distances`
- `mmu_encoder_resolution`
- `mmu_bldc_map`
- Current gate state.

## Log-First Debugging

For movement issues, inspect `printer_data/logs/mmu.log` before changing code.
Useful commands:

```powershell
rg -n "BLDC_|ESPOOLER|MMU_TEST_MOVE|encoder|rotation_distance|sync_feedback" printer_data\logs\mmu.log
python utils\plot_bldc_pwm.py printer_data\logs\mmu.log
```

If a test says the espooler moved but the BLDC gear did not, verify whether
`BLDC_SET_PIN` lines were emitted. Espooler motion and BLDC motion are related
at the Happy Hare movement level, but their pin-output paths are separate.

## Planned Feature Areas

Use `TODO.md` as the planning source for future work. The next big areas are:

- CFS temperature/humidity sensor on I2C.
- Two RFID readers on I2C.
- Espooler current feedback and closed-loop rewind control.
- Eight discrete status LEDs.
- Front display communication and backlight control.

## Verification Expectations

For documentation-only changes, a Markdown/link review is enough.

For code or config changes, prefer at least one of:

- Targeted unit/static test if available.
- Klipper config load validation on the printer environment.
- A short controlled `MMU_TEST_MOVE`.
- Log correlation from `mmu.log`.

For BLDC or espooler changes, always inspect logs for the corresponding
`BLDC_*` and `ESPOOLER` lines after testing.

