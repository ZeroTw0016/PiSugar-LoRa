from flask import Flask, jsonify, request, abort, render_template
from battery_store import store
from lora_api import lora_api
import smbus2
import time
# --- Bluetooth API ---
from bluetooth_utils import scan_bluetooth_devices, pair_bluetooth_device, list_paired_devices
from bluetooth_state import selected_bt_output

# PiSugar 3 Standard I2C-Adresse
PISUGAR_I2C_ADDR = 0x57
I2C_BUS = 1

app = Flask(__name__)
app.register_blueprint(lora_api)

def get_bus():
    return smbus2.SMBus(I2C_BUS)

def read_register(addr, reg):
    with get_bus() as bus:
        return bus.read_byte_data(addr, reg)

def write_register(addr, reg, value):
    with get_bus() as bus:
        bus.write_byte_data(addr, reg, value)

def is_write_protection_on():
    val = read_register(PISUGAR_I2C_ADDR, 0x0B)
    return val != 1

def set_write_protection(enabled: bool):
    if enabled:
        write_register(PISUGAR_I2C_ADDR, 0x0B, 0xFF)
    else:
        write_register(PISUGAR_I2C_ADDR, 0x0B, 0x29)
    time.sleep(0.05)

def get_status():
    reg2 = read_register(PISUGAR_I2C_ADDR, 0x02)
    reg3 = read_register(PISUGAR_I2C_ADDR, 0x03)
    reg4 = read_register(PISUGAR_I2C_ADDR, 0x04)
    reg6 = read_register(PISUGAR_I2C_ADDR, 0x06)
    reg7 = read_register(PISUGAR_I2C_ADDR, 0x07)
    reg9 = read_register(PISUGAR_I2C_ADDR, 0x09)
    reg20 = read_register(PISUGAR_I2C_ADDR, 0x20)
    reg22 = read_register(PISUGAR_I2C_ADDR, 0x22)
    reg23 = read_register(PISUGAR_I2C_ADDR, 0x23)
    reg2a = read_register(PISUGAR_I2C_ADDR, 0x2A)
    reg40 = read_register(PISUGAR_I2C_ADDR, 0x40)
    reg44 = [read_register(PISUGAR_I2C_ADDR, r) for r in range(0x44, 0x48)]
    reg50 = read_register(PISUGAR_I2C_ADDR, 0x50)
    rege0 = read_register(PISUGAR_I2C_ADDR, 0xE0)
    return {
        'external_power': bool((reg2 >> 7) & 1),
        'charging_switch': bool((reg2 >> 6) & 1),
        'output_switch': bool((reg2 >> 2) & 1),
        'output_switch_delay': bool((reg2 >> 5) & 1),
        'output_switch_delay_time': reg9,
        'auto_resume_boot': bool((reg2 >> 4) & 1),
        'anti_mistouch': bool((reg2 >> 3) & 1),
        'button_pressed': bool(reg2 & 1),
        'auto_hibernate': bool((reg3 >> 6) & 1),
        'soft_shutdown': bool((reg3 >> 4) & 1),
        'soft_shutdown_state': bool((reg3 >> 3) & 1),
        'chip_temp_c': reg4 - 40,
        'watchdog_enabled': bool((reg6 >> 7) & 1),
        'watchdog_reset': bool((reg6 >> 5) & 1),
        'watchdog_interval': reg7,
        'boot_watchdog_enabled': bool((reg6 >> 4) & 1),
        'boot_watchdog_reset': bool((reg6 >> 3) & 1),
        'boot_watchdog_restart_limit': read_register(PISUGAR_I2C_ADDR, 0x0A),
        'charging_protection': bool((reg20 >> 7) & 1),
        'scl_awake': bool((reg20 >> 3) & 1),
        'battery_voltage_mv': ((reg22 << 8) | reg23),
        'battery_percent': reg2a,
        'timing_boot_enabled': bool((reg40 >> 7) & 1),
        'timing_boot_data': reg44,
        'custom_i2c_addr': reg50,
        'led_control': rege0 & 0x0F,
        'write_protection': is_write_protection_on(),
        'selected_bt_output': selected_bt_output
    }


# Status-Endpunkt
@app.route('/api/status', methods=['GET'])
def api_status():
    try:
        status = get_status()
        # Battery history speichern
        from time import time as _now
        store.add_battery(status['battery_percent'], int(_now()*1000))
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# API für Batterie-Historie
@app.route('/api/battery_history', methods=['GET'])
def api_battery_history():
    return jsonify(store.get_battery_history())

# API für Shutdown-Historie
@app.route('/api/shutdown_history', methods=['GET'])
def api_shutdown_history():
    return jsonify(store.get_shutdowns())

# Write-Protection-Endpunkt
@app.route('/api/write_protection', methods=['GET', 'POST'])
def api_write_protection():
    if request.method == 'GET':
        return jsonify({'write_protection': is_write_protection_on()})
    if request.method == 'POST':
        data = request.get_json(force=True)
        enabled = bool(data.get('enabled', True))
        # Nur das Aktivieren blockieren, wenn bereits aktiv
        if enabled and is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        set_write_protection(enabled)
        return jsonify({'write_protection': is_write_protection_on()})

# Beispiel für Output-Switch (Register 0x02, Bit 2)
# Beispiel für Output-Switch (Register 0x02, Bit 2)

# --- Output Switch ---
@app.route('/api/output_switch', methods=['GET', 'POST'])
def api_output_switch():
    if request.method == 'GET':
        reg2 = read_register(PISUGAR_I2C_ADDR, 0x02)
        return jsonify({'output_switch': bool((reg2 >> 2) & 1)})
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        on = bool(data.get('on', True))
        reg2 = read_register(PISUGAR_I2C_ADDR, 0x02)
        if on:
            reg2 |= (1 << 2)
        else:
            reg2 &= ~(1 << 2)
        write_register(PISUGAR_I2C_ADDR, 0x02, reg2)
        return jsonify({'output_switch': bool((reg2 >> 2) & 1)})

# --- Charging Switch ---
@app.route('/api/charging_switch', methods=['GET', 'POST'])
def api_charging_switch():
    if request.method == 'GET':
        reg2 = read_register(PISUGAR_I2C_ADDR, 0x02)
        return jsonify({'charging_switch': bool((reg2 >> 6) & 1)})
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        on = bool(data.get('on', True))
        reg2 = read_register(PISUGAR_I2C_ADDR, 0x02)
        if on:
            reg2 |= (1 << 6)
        else:
            reg2 &= ~(1 << 6)
        write_register(PISUGAR_I2C_ADDR, 0x02, reg2)
        return jsonify({'charging_switch': bool((reg2 >> 6) & 1)})

# --- Output Switch Delay ---
@app.route('/api/output_switch_delay', methods=['POST'])
def api_output_switch_delay():
    if is_write_protection_on():
        abort(403, description='Write protection is enabled. Changes are not allowed.')
    data = request.get_json(force=True)
    delay = int(data.get('delay', 0))
    write_register(PISUGAR_I2C_ADDR, 0x09, delay)
    reg2 = read_register(PISUGAR_I2C_ADDR, 0x02)
    reg2 &= ~(1 << 5)
    write_register(PISUGAR_I2C_ADDR, 0x02, reg2)
    return jsonify({'output_switch_delay_time': delay})

# --- Auto Resume Boot ---
@app.route('/api/auto_resume_boot', methods=['GET', 'POST'])
def api_auto_resume_boot():
    if request.method == 'GET':
        reg2 = read_register(PISUGAR_I2C_ADDR, 0x02)
        return jsonify({'auto_resume_boot': bool((reg2 >> 4) & 1)})
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        on = bool(data.get('on', True))
        reg2 = read_register(PISUGAR_I2C_ADDR, 0x02)
        if on:
            reg2 |= (1 << 4)
        else:
            reg2 &= ~(1 << 4)
        write_register(PISUGAR_I2C_ADDR, 0x02, reg2)
        return jsonify({'auto_resume_boot': bool((reg2 >> 4) & 1)})

# --- Anti-Mistouch ---
@app.route('/api/anti_mistouch', methods=['GET', 'POST'])
def api_anti_mistouch():
    if request.method == 'GET':
        reg2 = read_register(PISUGAR_I2C_ADDR, 0x02)
        return jsonify({'anti_mistouch': bool((reg2 >> 3) & 1)})
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        on = bool(data.get('on', True))
        reg2 = read_register(PISUGAR_I2C_ADDR, 0x02)
        if on:
            reg2 |= (1 << 3)
        else:
            reg2 &= ~(1 << 3)
        write_register(PISUGAR_I2C_ADDR, 0x02, reg2)
        return jsonify({'anti_mistouch': bool((reg2 >> 3) & 1)})

# --- Auto Hibernate ---
@app.route('/api/auto_hibernate', methods=['GET', 'POST'])
def api_auto_hibernate():
    if request.method == 'GET':
        reg3 = read_register(PISUGAR_I2C_ADDR, 0x03)
        return jsonify({'auto_hibernate': bool((reg3 >> 6) & 1)})
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        on = bool(data.get('on', True))
        reg3 = read_register(PISUGAR_I2C_ADDR, 0x03)
        if on:
            reg3 |= (1 << 6)
        else:
            reg3 &= ~(1 << 6)
        write_register(PISUGAR_I2C_ADDR, 0x03, reg3)
        return jsonify({'auto_hibernate': bool((reg3 >> 6) & 1)})

# --- Soft Shutdown ---
@app.route('/api/soft_shutdown', methods=['GET', 'POST'])
def api_soft_shutdown():
    if request.method == 'GET':
        reg3 = read_register(PISUGAR_I2C_ADDR, 0x03)
        return jsonify({'soft_shutdown': bool((reg3 >> 4) & 1)})
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        on = bool(data.get('on', True))
        reg3 = read_register(PISUGAR_I2C_ADDR, 0x03)
        if on:
            reg3 |= (1 << 4)
        else:
            reg3 &= ~(1 << 4)
        write_register(PISUGAR_I2C_ADDR, 0x03, reg3)
        return jsonify({'soft_shutdown': bool((reg3 >> 4) & 1)})

# --- Watchdog ---
@app.route('/api/watchdog', methods=['GET', 'POST'])
def api_watchdog():
    if request.method == 'GET':
        reg6 = read_register(PISUGAR_I2C_ADDR, 0x06)
        reg7 = read_register(PISUGAR_I2C_ADDR, 0x07)
        return jsonify({
            'watchdog_enabled': bool((reg6 >> 7) & 1),
            'watchdog_reset': bool((reg6 >> 5) & 1),
            'watchdog_interval': reg7
        })
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        reg6 = read_register(PISUGAR_I2C_ADDR, 0x06)
        if 'enabled' in data:
            if data['enabled']:
                reg6 |= (1 << 7)
            else:
                reg6 &= ~(1 << 7)
        if 'reset' in data and data['reset']:
            reg6 |= (1 << 5)
        write_register(PISUGAR_I2C_ADDR, 0x06, reg6)
        if 'interval' in data:
            write_register(PISUGAR_I2C_ADDR, 0x07, int(data['interval']))
        return jsonify({'success': True})

# --- Boot Watchdog ---
@app.route('/api/boot_watchdog', methods=['GET', 'POST'])
def api_boot_watchdog():
    if request.method == 'GET':
        reg6 = read_register(PISUGAR_I2C_ADDR, 0x06)
        return jsonify({
            'boot_watchdog_enabled': bool((reg6 >> 4) & 1),
            'boot_watchdog_reset': bool((reg6 >> 3) & 1),
            'boot_watchdog_restart_limit': read_register(PISUGAR_I2C_ADDR, 0x0A)
        })
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        reg6 = read_register(PISUGAR_I2C_ADDR, 0x06)
        if 'enabled' in data:
            if data['enabled']:
                reg6 |= (1 << 4)
            else:
                reg6 &= ~(1 << 4)
        if 'reset' in data and data['reset']:
            reg6 |= (1 << 3)
        write_register(PISUGAR_I2C_ADDR, 0x06, reg6)
        if 'restart_limit' in data:
            write_register(PISUGAR_I2C_ADDR, 0x0A, int(data['restart_limit']))
        return jsonify({'success': True})

# --- Charging Protection ---
@app.route('/api/charging_protection', methods=['GET', 'POST'])
def api_charging_protection():
    if request.method == 'GET':
        reg20 = read_register(PISUGAR_I2C_ADDR, 0x20)
        return jsonify({'charging_protection': bool((reg20 >> 7) & 1)})
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        on = bool(data.get('on', True))
        reg20 = read_register(PISUGAR_I2C_ADDR, 0x20)
        if on:
            reg20 |= (1 << 7)
        else:
            reg20 &= ~(1 << 7)
        write_register(PISUGAR_I2C_ADDR, 0x20, reg20)
        return jsonify({'charging_protection': bool((reg20 >> 7) & 1)})

# --- SCL Awake ---
@app.route('/api/scl_awake', methods=['GET', 'POST'])
def api_scl_awake():
    if request.method == 'GET':
        reg20 = read_register(PISUGAR_I2C_ADDR, 0x20)
        return jsonify({'scl_awake': bool((reg20 >> 3) & 1)})
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        on = bool(data.get('on', True))
        reg20 = read_register(PISUGAR_I2C_ADDR, 0x20)
        if on:
            reg20 |= (1 << 3)
        else:
            reg20 &= ~(1 << 3)
        write_register(PISUGAR_I2C_ADDR, 0x20, reg20)
        return jsonify({'scl_awake': bool((reg20 >> 3) & 1)})

# --- Timing Boot ---
@app.route('/api/timing_boot', methods=['GET', 'POST'])
def api_timing_boot():
    if request.method == 'GET':
        reg40 = read_register(PISUGAR_I2C_ADDR, 0x40)
        reg44 = [read_register(PISUGAR_I2C_ADDR, r) for r in range(0x44, 0x48)]
        return jsonify({'timing_boot_enabled': bool((reg40 >> 7) & 1), 'timing_boot_data': reg44})
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        reg40 = read_register(PISUGAR_I2C_ADDR, 0x40)
        if 'enabled' in data:
            if data['enabled']:
                reg40 |= (1 << 7)
            else:
                reg40 &= ~(1 << 7)
            write_register(PISUGAR_I2C_ADDR, 0x40, reg40)
        if 'data' in data and isinstance(data['data'], list) and len(data['data']) == 4:
            for i, v in enumerate(data['data']):
                write_register(PISUGAR_I2C_ADDR, 0x44 + i, int(v))
        return jsonify({'success': True})

# --- Custom I2C Address ---
@app.route('/api/custom_i2c_addr', methods=['GET', 'POST'])
def api_custom_i2c_addr():
    if request.method == 'GET':
        reg50 = read_register(PISUGAR_I2C_ADDR, 0x50)
        return jsonify({'custom_i2c_addr': reg50})
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        addr = int(data.get('addr', 0x57))
        write_register(PISUGAR_I2C_ADDR, 0x50, addr)
        return jsonify({'custom_i2c_addr': addr})

# --- LED Control ---
@app.route('/api/led_control', methods=['GET', 'POST'])
def api_led_control():
    if request.method == 'GET':
        rege0 = read_register(PISUGAR_I2C_ADDR, 0xE0)
        return jsonify({'led_control': rege0 & 0x0F})
    if request.method == 'POST':
        if is_write_protection_on():
            abort(403, description='Write protection is enabled. Changes are not allowed.')
        data = request.get_json(force=True)
        value = int(data.get('value', 0)) & 0x0F
        rege0 = read_register(PISUGAR_I2C_ADDR, 0xE0)
        rege0 = (rege0 & 0xF0) | value
        write_register(PISUGAR_I2C_ADDR, 0xE0, rege0)
        return jsonify({'led_control': value})

# Bluetooth: Gekoppelte Geräte auflisten
@app.route('/api/bluetooth/paired', methods=['GET'])
def api_bluetooth_paired():
    try:
        devices = list_paired_devices()
        return jsonify({'devices': devices})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Bluetooth: Gerät koppeln
@app.route('/api/bluetooth/pair', methods=['POST'])
def api_bluetooth_pair():
    data = request.get_json(force=True)
    address = data.get('address')
    if not address:
        return jsonify({'error': 'No address provided'}), 400
    success = pair_bluetooth_device(address)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Pairing failed'}), 500

# Bluetooth: Gerät trennen
@app.route('/api/bluetooth/disconnect', methods=['POST'])
def api_bluetooth_disconnect():
    import subprocess
    data = request.get_json(force=True)
    address = data.get('address')
    if not address:
        return jsonify({'error': 'No address provided'}), 400
    try:
        subprocess.check_call(['bluetoothctl', 'disconnect', address], timeout=10)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/bluetooth/scan', methods=['POST'])
def api_bluetooth_scan():
    data = request.get_json(force=True)
    scan_on = data.get('scan_on', True)
    try:
        devices = scan_bluetooth_devices(scan_on=scan_on)
        return jsonify({'devices': devices, 'scanning': scan_on})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Bluetooth: Audio-Ausgabe-Gerät setzen
@app.route('/api/bluetooth/output', methods=['POST'])
def api_bluetooth_output():
    data = request.get_json(force=True)
    address = data.get('address')
    if not address:
        return jsonify({'success': False, 'error': 'No address provided'}), 400
    from bluetooth_state import selected_bt_output
    selected_bt_output['address'] = address
    return jsonify({'success': True})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    import threading
    import logging
    def battery_background_task():
        while True:
            try:
                status = get_status()
                from time import time as _now
                store.add_battery(status['battery_percent'], int(_now()*1000))
            except Exception as e:
                logging.warning(f"Battery background task error: {e}")
            time.sleep(60)  # alle 60 Sekunden

    threading.Thread(target=battery_background_task, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
