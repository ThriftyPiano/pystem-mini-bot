# Minimal ES8311 audio codec driver for microphone capture over I2S.
#
# The codec runs as I2S slave and derives its internal MCLK from the BCLK
# (SCLK) line, so the ESP32 only needs to drive BCLK/WS — no MCLK pin
# required. Configured for 16 kHz / 16-bit mono ADC capture.

from machine import I2C
import time

_ADDR = 0x18

# Register map (subset)
_REG00_RESET = 0x00
_REG01_CLK = 0x01
_REG02_CLK = 0x02
_REG03_CLK = 0x03
_REG04_CLK = 0x04
_REG05_CLK = 0x05
_REG06_CLK = 0x06
_REG07_CLK = 0x07
_REG08_CLK = 0x08
_REG09_SDPIN = 0x09
_REG0A_SDPOUT = 0x0A
_REG0B_SYSTEM = 0x0B
_REG0C_SYSTEM = 0x0C
_REG0D_SYSTEM = 0x0D
_REG0E_SYSTEM = 0x0E
_REG10_SYSTEM = 0x10
_REG11_SYSTEM = 0x11
_REG12_SYSTEM = 0x12
_REG13_SYSTEM = 0x13
_REG14_SYSTEM = 0x14
_REG15_ADC = 0x15
_REG16_ADC = 0x16
_REG17_ADC = 0x17
_REG1B_ADC = 0x1B
_REG1C_ADC = 0x1C
_REG31_DAC = 0x31
_REG32_DAC = 0x32
_REG37_DAC = 0x37
_REG44_GPIO = 0x44
_REG45_GP = 0x45


class ES8311:
    def __init__(self, i2c: I2C, addr: int = _ADDR):
        self.i2c = i2c
        self.addr = addr

    def _w(self, reg, val):
        self.i2c.writeto_mem(self.addr, reg, bytes([val & 0xFF]))

    def _r(self, reg):
        return self.i2c.readfrom_mem(self.addr, reg, 1)[0]

    def init_mic(self, mic_gain=4):
        """Configure the codec for 16 kHz / 16-bit mono microphone capture.

        mic_gain: analog mic gain step, 0..7 (0 dB .. 42 dB in 6 dB steps).
        """
        w = self._w
        # Improve I2C noise immunity; first write may be ignored after
        # power-up, so it is issued twice.
        w(_REG44_GPIO, 0x08)
        w(_REG44_GPIO, 0x08)

        # Power-up / clock defaults
        w(_REG01_CLK, 0x30)
        w(_REG02_CLK, 0x00)
        w(_REG03_CLK, 0x10)
        w(_REG16_ADC, 0x24)
        w(_REG04_CLK, 0x10)
        w(_REG05_CLK, 0x00)
        w(_REG0B_SYSTEM, 0x00)
        w(_REG0C_SYSTEM, 0x00)
        w(_REG10_SYSTEM, 0x1F)
        w(_REG11_SYSTEM, 0x7F)
        w(_REG00_RESET, 0x80)  # power on, slave mode
        time.sleep_ms(2)

        # Enable all internal clocks, then select BCLK pin as MCLK source
        w(_REG01_CLK, 0x3F | 0x80)

        # Clock dividers for 16 kHz from BCLK = 512 kHz (16-bit stereo frame):
        # internal MCLK = BCLK * 8 = 256 * Fs
        w(_REG02_CLK, (3 << 3))  # pre_div=1, pre_mult=x8
        w(_REG05_CLK, 0x00)      # adc_div=1, dac_div=1
        w(_REG03_CLK, 0x10)      # single speed, ADC OSR 0x10
        w(_REG04_CLK, 0x20)      # DAC OSR 0x20
        w(_REG07_CLK, self._r(_REG07_CLK) & 0xC0)  # LRCK divider high
        w(_REG08_CLK, 0xFF)      # LRCK divider low (0x0100 - 1)
        w(_REG06_CLK, (self._r(_REG06_CLK) & 0xE0) | 0x03)  # BCLK div 4

        # Serial port: I2S standard format, 16-bit
        w(_REG09_SDPIN, (self._r(_REG09_SDPIN) & 0xFC & ~0x1C) | 0x0C)
        w(_REG0A_SDPOUT, (self._r(_REG0A_SDPOUT) & 0xFC & ~0x1C) | 0x0C)

        w(_REG13_SYSTEM, 0x10)
        w(_REG1B_ADC, 0x0A)
        w(_REG1C_ADC, 0x6A)

        # Start ADC path (keep DAC serial input muted)
        w(_REG09_SDPIN, self._r(_REG09_SDPIN) | 0x40)
        w(_REG0A_SDPOUT, self._r(_REG0A_SDPOUT) & ~0x40)
        w(_REG17_ADC, 0xBF)      # ADC digital volume 0 dB
        w(_REG0E_SYSTEM, 0x02)   # power up analog input
        w(_REG12_SYSTEM, 0x00)
        w(_REG14_SYSTEM, 0x1A)   # analog mic, PGA on
        w(_REG0D_SYSTEM, 0x01)   # power up
        w(_REG15_ADC, 0x40)      # ADC soft ramp
        w(_REG37_DAC, 0x08)
        w(_REG45_GP, 0x00)
        w(_REG44_GPIO, 0x58)     # ADC data to both slots

        self.set_mic_gain(mic_gain)

    def enable_dac(self, volume=0xBF):
        """Additionally enable the DAC path for speaker playback.

        Call after init_mic(). Playback uses a machine.I2S TX instance on
        the same BCLK/WS pins with sd on the codec's DIN pin. On the
        StickS3 the AW8737 amplifier must also be enabled via the M5PM1
        power chip (m5pm1.M5PM1.speaker_enable).
        """
        w = self._w
        w(_REG09_SDPIN, self._r(_REG09_SDPIN) & ~0x40)  # unmute DAC serial in
        w(_REG12_SYSTEM, 0x00)   # power up DAC
        w(_REG37_DAC, 0x08)
        self.set_dac_volume(volume)

    def set_mic_gain(self, gain):
        self._w(_REG16_ADC, 0x20 | (gain & 0x07))

    def set_adc_volume(self, vol=0xBF):
        # 0x00 = -95.5 dB, 0xBF = 0 dB, 0xFF = +32 dB (0.5 dB steps)
        self._w(_REG17_ADC, vol & 0xFF)

    def set_dac_volume(self, vol=0xBF):
        # 0x00 = -95.5 dB, 0xBF = 0 dB, 0xFF = +32 dB (0.5 dB steps)
        self._w(_REG32_DAC, vol & 0xFF)
