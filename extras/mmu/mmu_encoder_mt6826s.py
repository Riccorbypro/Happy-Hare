# Happy Hare MMU Software
# MT6826S-backed encoder wrapper for Happy Hare's mmu encoder API
#
# Copyright (C) 2022-2026  moggieuk#6538 (discord)
#                          moggieuk@hotmail.com
#
# This file may be distributed under the terms of the GNU GPLv3 license.
#
from ..mmu_encoder import MmuEncoder


class MmuEncoderMt6826s(MmuEncoder):
    def __init__(self, config):
        self.encoder_angle = config.get('encoder_angle')
        pwm_pin = config.get('pwm_pin', None)
        if pwm_pin is None:
            raise config.error("[mmu_encoder_mt6826s] requires 'pwm_pin'")

        # Calculate encoder_resolution from MT6826S-specific parameters if provided
        pwm_pulses = config.getfloat('pwm_pulses_per_revolution', None, above=0.)
        rotation_dist = config.getfloat('rotation_distance', None, above=0.)
        if pwm_pulses is not None and rotation_dist is not None:
            # encoder_resolution = distance per pulse (mm/pulse)
            calculated_resolution = rotation_dist / pwm_pulses
            section_name = config.get_name()
            if not config.fileconfig.has_option(section_name, 'encoder_resolution'):
                config.fileconfig.set(section_name, 'encoder_resolution', str(calculated_resolution))

        # Reuse the existing mmu encoder implementation by mapping pwm_pin onto
        # the expected encoder_pin field if it is not explicitly supplied.
        section_name = config.get_name()
        if not config.fileconfig.has_option(section_name, 'encoder_pin'):
            config.fileconfig.set(section_name, 'encoder_pin', pwm_pin)

        super(MmuEncoderMt6826s, self).__init__(config)

        self.angle_sensor = self.printer.lookup_object('angle %s' % self.encoder_angle, None)
        if self.angle_sensor is None:
            raise config.error("Missing [angle %s] section referenced by [mmu_encoder_mt6826s %s]"
                               % (self.encoder_angle, self.name))

    def get_status(self, eventtime):
        status = super(MmuEncoderMt6826s, self).get_status(eventtime)
        angle_status = self.angle_sensor.get_status(eventtime)
        status['angle_temperature'] = angle_status.get('temperature', None)
        return status


def load_config_prefix(config):
    return MmuEncoderMt6826s(config)
