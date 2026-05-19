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
        self.rotation_distance = config.getfloat('rotation_distance', 4.0, above=0.)

        # MT6826S uses angle data instead of pulse counting. Set encoder_resolution
        # based on rotation_distance to ensure filament movement is accurately tracked.
        # For a 360° rotation, filament moves by rotation_distance mm.
        # encoder_resolution = distance per degree = rotation_distance / 360
        calculated_resolution = self.rotation_distance / 360.0
        section_name = config.get_name()
        if not config.fileconfig.has_option(section_name, 'encoder_resolution'):
            config.fileconfig.set(section_name, 'encoder_resolution', str(calculated_resolution))

        # MT6826S requires a dummy encoder_pin for base class compatibility
        if not config.fileconfig.has_option(section_name, 'encoder_pin'):
            # Use a placeholder value; actual angle data comes from angle sensor
            config.fileconfig.set(section_name, 'encoder_pin', 'mmu:PA0')

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
    encoder = MmuEncoderMt6826s(config)

    # Compatibility alias: expose MT6826S-backed encoder under the same
    # object namespace used by pulsed encoders.
    alias_name = 'mmu_encoder %s' % encoder.name
    printer = config.get_printer()
    if printer.lookup_object(alias_name, None) is None:
        printer.add_object(alias_name, encoder)

    return encoder
