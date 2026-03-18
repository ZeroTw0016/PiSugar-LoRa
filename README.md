## Editierbare PiSugar-Parameter
Die folgenden PiSugar-Batterie-Parameter können über die Weboberfläche oder API geändert werden, **sofern die Write Protection deaktiviert ist**:

- Timing Boot
- Auto Resume Boot
- Soft Shutdown
- Watchdog (enabled, reset, interval)
- Boot Watchdog
- Charging Protection
- Auto Hibernate
- Anti Mistouch

Alle anderen Einstellungen sind schreibgeschützt, solange Write Protection aktiv ist.
# PiSugar-LoRa Webserver & LoRa HAT

## Features
- Weboberfläche für PiSugar-Batterie-Status und LoRa-Kommunikation
- Live-Anzeige und Senden/Empfangen von LoRa-Nachrichten
- Waveshare SX1262 868M LoRa HAT Unterstützung
- Responsives UI (auch für Handy)

## Installation
1. Abhängigkeiten installieren:
   ```
   pip install -r requirements.txt
   ```
2. (Optional) I2C aktivieren und Benutzer zur Gruppe `i2c` hinzufügen:
   ```
   sudo raspi-config # Interfacing Options → I2C aktivieren
   sudo usermod -aG i2c $USER
   ```
3. (Optional) Serielle Schnittstelle aktivieren:
   ```
   sudo raspi-config # Interfacing Options → Serial Port
   ```

## Starten
```bash
python3 pisugar_server.py
```

Weboberfläche erreichbar unter:  
http://<raspberry-pi-ip>:5000

## Autostart als Service (systemd)
1. Erstelle die Datei `/etc/systemd/system/pisugar-lora.service` mit folgendem Inhalt:
   ```ini
   [Unit]
   Description=PiSugar LoRa Webserver
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/PiSugar-LoRa
   ExecStart=/usr/bin/python3 /home/pi/PiSugar-LoRa/pisugar_server.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   Passe ggf. User, WorkingDirectory und ExecStart an deinen Pfad/Nutzer an!

2. Service aktivieren und starten:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable pisugar-lora
   sudo systemctl start pisugar-lora
   sudo systemctl status pisugar-lora
   ```

## Hinweise
- Die LoRa-Parameter (Frequenz, air_speed, etc.) können im Code angepasst werden.
- Für pyserial muss das falsche Paket `serial` deinstalliert sein!
- Die Weboberfläche zeigt Batterie-Status im Banner und LoRa-Nachrichten im Hauptbereich.


