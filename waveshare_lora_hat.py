# waveshare_lora_hat.py
"""
Ansteuerung des Waveshare SX1262 868M LoRa HAT auf Basis von sx126x.py
https://www.waveshare.com/wiki/SX1262_868M_LoRa_HAT

- Frequenz: 868 MHz
- GPIO-Pins und UART wie im Waveshare-Datenblatt
- Methoden: init, send, receive, get_settings
"""

import RPi.GPIO as GPIO
import serial
import time
import socket

class WaveshareSX1262LoRaHAT:
    # Standard-Pinbelegung laut Waveshare-Doku
    M0 = 22
    M1 = 27
    AUX = 17
    UART_PORT = '/dev/ttyS0'  # ggf. anpassen
    UART_BAUDRATE = 9600
    FREQ = 868  # Default frequency (MHz)
    GERMANY_FREQ = 869.525  # Example Germany frequency (MHz)
    AIRNAV_FREQ = 960  # Listen-only frequency for Airnavigation (MHz)

    def __init__(self, addr=None, power=22, rssi=False, air_speed=2400, net_id=0, buffer_size=240, crypt=0, freq=None):
        hostname = socket.gethostname()
        # Always use 0x9401 for ZeroLora02 (or fallback to 0x9401)
        custom_addr = 0x9401
        self.addr = addr if addr is not None else custom_addr
        # Frequency logic
        self.freq = freq if freq is not None else self.FREQ
        self.power = power
        self.rssi = rssi
        self.air_speed = air_speed
        self.net_id = net_id
        self.buffer_size = buffer_size
        self.crypt = crypt
        # GPIO Setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.M0, GPIO.OUT)
        GPIO.setup(self.M1, GPIO.OUT)
        GPIO.setup(self.AUX, GPIO.IN)
        GPIO.output(self.M0, GPIO.LOW)
        GPIO.output(self.M1, GPIO.HIGH)
        # UART Setup
        self.ser = serial.Serial(self.UART_PORT, self.UART_BAUDRATE)
        self.ser.flushInput()
        time.sleep(0.1)
        self.set_mode_normal()

    def set_frequency(self, freq_mhz):
        """
        Set the frequency for receiving. Only 868 MHz is allowed for sending.
        960 MHz (AIRNAV_FREQ) ist nur für Empfang (listen only) erlaubt.
        """
        allowed = [self.FREQ, getattr(self, 'GERMANY_FREQ', 869.525), getattr(self, 'AIRNAV_FREQ', 960)]
        if freq_mhz not in allowed:
            raise ValueError(f"Frequency {freq_mhz} MHz not allowed.")
        self.freq = freq_mhz
        if self.freq == self.AIRNAV_FREQ:
            print(f"[LoRa] Frequency set to {self.freq} MHz (listen only, Airnavigation)")
        else:
            print(f"[LoRa] Frequency set to {self.freq} MHz (send only allowed on 868 MHz)")

    def set_mode_normal(self):
        GPIO.output(self.M0, GPIO.LOW)
        GPIO.output(self.M1, GPIO.LOW)
        time.sleep(0.1)

    def set_mode_config(self):
        GPIO.output(self.M0, GPIO.LOW)
        GPIO.output(self.M1, GPIO.HIGH)
        time.sleep(0.1)

    def send(self, data: bytes):
        if self.freq != self.FREQ:
            print(f"[LoRa] SEND BLOCKED: Sending is only allowed on {self.FREQ} MHz, current frequency is {self.freq} MHz.")
            raise RuntimeError(f"Sending is only allowed on {self.FREQ} MHz!")
        self.set_mode_normal()
        self.ser.write(data)
        time.sleep(0.1)

    def receive(self):
        self.set_mode_normal()
        if self.ser.inWaiting() > 0:
            time.sleep(0.5)
            r_buff = self.ser.read(self.ser.inWaiting())
            print("Empfangen: ", r_buff)
            return r_buff
        return None

    def get_settings(self):
        self.set_mode_config()
        self.ser.write(bytes([0xC1, 0x00, 0x09]))
        time.sleep(0.1)
        if self.ser.inWaiting() > 0:
            r_buff = self.ser.read(self.ser.inWaiting())
            print("Modul-Settings:", r_buff)
        self.set_mode_normal()

    def close(self):
        self.ser.close()
        GPIO.cleanup()

# Beispiel für die Nutzung
if __name__ == "__main__":
    lora = WaveshareSX1262LoRaHAT()
    lora.get_settings()
    lora.send(b'Hello LoRa!')
    msg = lora.receive()
    print(msg)
    lora.close()
