# Creality CFS Notes for Happy Hare

This document explains the current state of the Creality CFS adaptation in this
repository. It is written for users who are already comfortable editing Klipper
configuration files and restarting Klipper, but who do not necessarily want to
read the Python source before every change.

The CFS is being treated as a custom four-lane, Type-B-style MMU. The important
difference from a normal Happy Hare Type-B setup is that the CFS does not use a
stepper as the filament drive gear. It uses a BLDC gear motor, separate spool
rewind/assist motors, per-lane sensors, and a magnetic encoder. That means the
usual Happy Hare concepts still apply, but several of the calibration and safety
checks are CFS-specific.

## Current Scope

The repo currently has base feeding and retracting filament working. The
following CFS hardware is configured or partly implemented:

- Four gates, exposed as `num_gates: 4`.
- A virtual selector, because the CFS has fixed lanes instead of a normal
  moving selector carriage.
- A BLDC motor in place of the usual `stepper_mmu_gear`.
- Four respool motors and four assist motors through `[mmu_espooler]`.
- Four pre-gate sensors and four post-gear sensors.
- A shared tension/compression sync-feedback pair.
- An MT6826S magnetic encoder for filament movement feedback.

The following hardware is not yet implemented in this repo:

- CFS temperature and humidity sensor on I2C.
- Two CFS RFID readers on I2C.
- Four current feedback inputs for the espooler motors.
- Eight individual lane status LEDs.
- Front display communications and backlight control.

## What Changed from Base Happy Hare

### Hardware Profile

The CFS config lives primarily in:

- `printer_data/config/mmu/base/mmu_hardware.cfg`
- `printer_data/config/mmu/base/mmu_parameters.cfg`
- `printer_data/config/variables.cfg`

The CFS is configured as:

```ini
[mmu_machine]
num_gates: 4
mmu_vendor: Other
selector_type: VirtualSelector
variable_bowden_lengths: 1
variable_rotation_distances: 1
require_bowden_move: 1
filament_always_gripped: 1
display_name: Creality CFS
```

This is deliberately not pretending to be a stock ERCF, Box Turtle, or other
supported Happy Hare machine. The CFS has enough unique hardware that the
`Other` profile is clearer and safer.

### BLDC Gear Motor

Base Happy Hare normally drives filament with a stepper-backed `mmu_gear`. This
repo adds and uses `extras/mmu/mmu_gear_bldc.py` for the CFS gear motor.

The active CFS BLDC section is:

```ini
[mmu_gear_bldc]
dir_pin: mmu:PE3
pwm_pin: !mmu:PE13
enable_pin: !mmu:PE4
pwm_min: 0.85
pwm_max: 1.00
rotation_distance: 600.0
hardware_pwm: False
cycle_time: 0.00005
tachometer_pin: ^mmu:PE11
tachometer_ppr: 4119
kick_start_time: 0
```

Important behavior:

- `pwm_min` is intentionally high enough to start the BLDC reliably under load.
- `rotation_distance` is the BLDC equivalent of stepper gear
  `rotation_distance`, but it is much larger than a BMG-style stepper value
  because it represents the relationship between BLDC rotation and filament
  movement.
- The tachometer can be used for speed feedback and calibration, but some moves
  are bounded by the filament encoder instead of by a timed BLDC run.
- `mmu_bldc_map` in `variables.cfg` stores BLDC calibration data when available.

### Encoder-Bounded BLDC Moves

The CFS can overrun if the BLDC is treated as a simple timed motor. This repo
adds encoder-bounded BLDC movement controls in `extras/mmu/mmu.py`.

The main parameters are in `mmu_parameters.cfg`:

```ini
encoder_bounded_bldc: 1
bldc_encoder_stop_margin: 4.0
bldc_encoder_predict_time: 0.04
bldc_encoder_brake: 1
bldc_encoder_settle_time: 0.05
bldc_encoder_espooler_stop_time: 0.25
bldc_encoder_min_move: 1.0
bldc_encoder_overrun_guard: 100.0
```

When this mode is active, Happy Hare starts the BLDC move, watches encoder
distance, predicts stopping distance, stops or brakes the BLDC before the target,
and then validates the final encoder distance. This is one of the key CFS safety
adaptations.

### Espooler Support

The CFS has four DC spool motors for rewind and four for assist. These are
configured through `[mmu_espooler mmu_espooler]`:

```ini
[mmu_espooler mmu_espooler]
pwm: 0
scale: 1

respool_motor_pin_0: mmu:PD3
assist_motor_pin_0: mmu:PD2
respool_motor_pin_1: mmu:PD1
assist_motor_pin_1: mmu:PD0
respool_motor_pin_2: mmu:PD15
assist_motor_pin_2: mmu:PD14
respool_motor_pin_3: mmu:PD13
assist_motor_pin_3: mmu:PD12
```

Current behavior is open-loop. The configured `pwm: 0` means these outputs are
being used as digital on/off outputs rather than variable PWM. Future work should
use the CFS current feedback inputs to detect whether a spool motor is keeping
up during retracts.

### Sensors and Encoder

The CFS uses per-lane entry and post-gear sensors:

```ini
pre_gate_switch_pin_0: !mmu:PD7
pre_gate_switch_pin_1: !mmu:PD6
pre_gate_switch_pin_2: !mmu:PD5
pre_gate_switch_pin_3: !mmu:PD4

post_gear_switch_pin_0: !mmu:PE10
post_gear_switch_pin_1: !mmu:PE9
post_gear_switch_pin_2: !mmu:PE8
post_gear_switch_pin_3: !mmu:PE7

sync_feedback_tension_pin: !mmu:PD9
sync_feedback_compression_pin: !mmu:PD8
extruder_switch_pin: !toolhead:PC14
```

The magnetic encoder is configured as:

```ini
[angle mmu_encoder_angle]
sensor_type: mt6826s
cs_pin: mmu:PB12
spi_software_sclk_pin: mmu:PB13
spi_software_mosi_pin: mmu:PB15
spi_software_miso_pin: mmu:PB14

[mmu_encoder_mt6826s mmu_encoder]
encoder_angle: mmu_encoder_angle
encoder_reversed: True
rotation_distance: 4.0
desired_headroom: 5.0
average_samples: 40
flowrate_samples: 20
```

The saved live value in `variables.cfg` currently includes:

```ini
mmu_encoder_resolution = 0.00060363
mmu_gear_rotation_distances = [3616.7665, -1, -1, -1]
mmu_bldc_map = {}
```

Treat saved variables as live printer state. They may override or fill in values
that do not appear final in the static config files.

## CFS Mainboard Pinout

This table documents the pin usage known from the current CFS work. Items marked
`planned` are known hardware pins that are not yet implemented.

| Function | Lane | MCU pin | Current repo usage |
| --- | ---: | --- | --- |
| BLDC direction | shared | PE3 | `[mmu_gear_bldc] dir_pin` |
| BLDC PWM/speed | shared | PE13 | `[mmu_gear_bldc] pwm_pin`, inverted |
| BLDC enable/brake | shared | PE4 | `[mmu_gear_bldc] enable_pin`, inverted |
| BLDC tachometer | shared | PE11 | `[mmu_gear_bldc] tachometer_pin`, pullup |
| Pre-gate sensor | 0 | PD7 | `pre_gate_switch_pin_0`, inverted |
| Pre-gate sensor | 1 | PD6 | `pre_gate_switch_pin_1`, inverted |
| Pre-gate sensor | 2 | PD5 | `pre_gate_switch_pin_2`, inverted |
| Pre-gate sensor | 3 | PD4 | `pre_gate_switch_pin_3`, inverted |
| Post-gear sensor | 0 | PE10 | `post_gear_switch_pin_0`, inverted |
| Post-gear sensor | 1 | PE9 | `post_gear_switch_pin_1`, inverted |
| Post-gear sensor | 2 | PE8 | `post_gear_switch_pin_2`, inverted |
| Post-gear sensor | 3 | PE7 | `post_gear_switch_pin_3`, inverted |
| Sync-feedback tension | shared | PD9 | `sync_feedback_tension_pin`, inverted |
| Sync-feedback compression | shared | PD8 | `sync_feedback_compression_pin`, inverted |
| Magnetic encoder CS | shared | PB12 | MT6826S angle sensor |
| Magnetic encoder SCLK | shared | PB13 | software SPI |
| Magnetic encoder MOSI | shared | PB15 | software SPI |
| Magnetic encoder MISO | shared | PB14 | software SPI |
| Respool motor | 0 | PD3 | `respool_motor_pin_0` |
| Assist motor | 0 | PD2 | `assist_motor_pin_0` |
| Respool motor | 1 | PD1 | `respool_motor_pin_1` |
| Assist motor | 1 | PD0 | `assist_motor_pin_1` |
| Respool motor | 2 | PD15 | `respool_motor_pin_2` |
| Assist motor | 2 | PD14 | `assist_motor_pin_2` |
| Respool motor | 3 | PD13 | `respool_motor_pin_3` |
| Assist motor | 3 | PD12 | `assist_motor_pin_3` |
| Temperature/humidity I2C | shared | PC11, PC12 | planned |
| RFID reader 1 I2C | shared | PB11, PB10 | planned |
| RFID reader 2 I2C | shared | PB9, PB8 | planned |
| Espooler current feedback | 0 | PC5 | planned |
| Espooler current feedback | 1 | PC0 | planned |
| Espooler current feedback | 2 | PA1 | planned |
| Espooler current feedback | 3 | PA0 | planned |
| Front display comms | shared | PC1, PC2, PC3, PC4 | planned |
| Front display backlight | shared | PB0 | planned |

## Calibration and Tuning

### How CFS Calibration Differs from a Standard Type-B MMU

A conventional Type-B Happy Hare setup usually calibrates a stepper gear,
selector/gate geometry, encoder resolution, and bowden lengths. The CFS changes
that picture:

- There is no normal selector to calibrate. The CFS uses fixed lanes and a
  `VirtualSelector`.
- The gear drive is a BLDC motor, so `rotation_distance` and speed control are
  not stepper pulse math. BLDC startup PWM, tachometer behavior, and encoder
  stopping all matter.
- Each lane can have a different effective gear rotation distance, so
  `variable_rotation_distances: 1` is enabled.
- Rewinding depends on DC espoolers. A normal Type-B setup may not need spool
  motor coordination at all.
- Encoder feedback is not just a convenience; it is part of the safety strategy
  for stopping BLDC moves accurately.

### Recommended Order

1. Verify the static pin config.
   Confirm that every sensor reports correctly before moving filament at speed.
   Use the Happy Hare UI/status output and Klipper endstop/sensor tools.

2. Verify low-power manual movement.
   Use short `MMU_TEST_MOVE` moves first. Watch the active lane, BLDC gear,
   espooler, and encoder distance together.

3. Calibrate encoder direction and resolution.
   The current config uses `encoder_reversed: True`. If movement direction looks
   backwards in logs or status, fix this before trusting any BLDC stop behavior.

4. Calibrate gate 0 gear movement.
   Saved state currently shows gate 0 has a calibrated gear rotation distance
   and gates 1-3 do not. Do not assume the gate 0 value is correct for every
   lane.

5. Calibrate remaining gates.
   Because `variable_rotation_distances: 1` is enabled, tune each lane.

6. Tune BLDC startup and stopping.
   Start with conservative speeds. If the BLDC does not start reliably,
   investigate `pwm_min`, wiring, enable polarity, and tachometer data before
   changing movement distances.

7. Tune espooler behavior.
   Open-loop rewind can work, but it can also create tangles if the spool cannot
   keep up with the BLDC. Keep unload speeds conservative until current feedback
   control exists.

8. Run repeated load/unload tests.
   A single successful move is not enough. Test each gate repeatedly and inspect
   `mmu.log` for `BLDC_SET_PIN`, `BLDC_TACH`, `BLDC_ENCODER_POSITION`, and
   `ESPOOLER` messages.

### Useful Log Patterns

When diagnosing CFS movement, these are the log prefixes worth searching first:

- `BLDC_SET_PIN`: actual BLDC PWM, direction, or enable pin output.
- `BLDC_TACH`: tachometer frequency and RPM.
- `BLDC_CONTROL`: tachometer-based speed control state.
- `BLDC_POSITION`: tachometer-position move target or completion.
- `BLDC_ENCODER_POSITION`: encoder-bounded stopping result.
- `ESPOOLER`: spool assist/rewind operation.

The helper script `utils/plot_bldc_pwm.py` is useful when a log contains
`BLDC_SET_PIN` and `BLDC_TACH` lines.

## Practical Safety Notes

- Keep `mmu.log` at a high enough level while tuning. The current config uses
  `log_level: 4` and `log_file_level: 4`, which is appropriate for bring-up.
- Do not tune several variables at once. BLDC PWM, encoder calibration, and
  espooler timing interact.
- If the espooler moves but the BLDC gear does not, that does not prove Happy
  Hare issued a valid BLDC command. The espooler path is separate enough that it
  can still run during a BLDC-only failure.
- If the BLDC gear moves but the encoder does not report movement, stop tuning
  speed and fix encoder sensing first.
- Treat `printer_data/config/variables.cfg` as part of the active configuration.
  Saved variables can explain behavior that does not match the defaults in the
  Python code.

