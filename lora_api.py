from flask import Blueprint, jsonify, request
from waveshare_lora_hat import WaveshareSX1262LoRaHAT
import threading
import json
import os
# --- TTS Integration für LoRa ---


# Frequenz persistent speichern
LORA_FREQ_FILE = 'lora_freq.json'
def load_lora_frequency():
    if os.path.exists(LORA_FREQ_FILE):
        try:
            with open(LORA_FREQ_FILE, 'r') as f:
                return float(json.load(f))
        except Exception:
            return None
    return None
def save_lora_frequency(freq):
    try:
        with open(LORA_FREQ_FILE, 'w') as f:
            json.dump(freq, f)
    except Exception:
        pass

saved_freq = load_lora_frequency()
lora_hat = WaveshareSX1262LoRaHAT(freq=saved_freq if saved_freq else None)
lora_api = Blueprint('lora_api', __name__)

# Shared message buffer
LORA_MSG_FILE = 'lora_messages.json'
MAX_LORA_MSGS = 20
def load_lora_messages():
    if os.path.exists(LORA_MSG_FILE):
        try:
            with open(LORA_MSG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []
def save_lora_messages(msgs):
    try:
        with open(LORA_MSG_FILE, 'w') as f:
            json.dump(msgs[-MAX_LORA_MSGS:], f, separators=(',', ':'))
    except Exception:
        pass
messages = load_lora_messages()

@lora_api.route('/api/lora/send', methods=['POST'])
def lora_send():
    from flask import request
    data = request.get_json(force=True)
    msg = data.get('msg', '')
    import datetime
    msg_bytes = msg.encode('utf-8')[:240]  # Ensure max 240 bytes
    print(f"[LoRa] Sende Nachricht: {msg}")
    lora_hat.send(msg_bytes)
    timestamp = datetime.datetime.now().isoformat(timespec='seconds')
    messages.append({'type': 'sent', 'msg': msg, 'timestamp': timestamp})
    print(f"[LoRa] Nachricht gespeichert: {msg}")
    if len(messages) > MAX_LORA_MSGS:
        messages[:] = messages[-MAX_LORA_MSGS:]
    save_lora_messages(messages)
    return jsonify({'status': 'sent'})

@lora_api.route('/api/lora/receive', methods=['GET'])
def lora_receive():
    import datetime
    r = lora_hat.receive()
    if r:
        msg_bytes = r[:240]  # Only process up to 240 bytes
        try:
            msg = msg_bytes.decode('utf-8')
        except UnicodeDecodeError:
            msg = None
        timestamp = datetime.datetime.now().isoformat(timespec='seconds')
        print(f"[LoRa] Empfangen (API): {msg if msg is not None else msg_bytes}")
        messages.append({'type': 'recv', 'msg': msg if msg is not None else str(msg_bytes), 'timestamp': timestamp})
        print(f"[LoRa] Empfang gespeichert: {msg if msg is not None else msg_bytes}")
        if len(messages) > MAX_LORA_MSGS:
            messages[:] = messages[-MAX_LORA_MSGS:]
        save_lora_messages(messages)
        return jsonify({'msg': msg if msg is not None else None, 'raw': list(msg_bytes), 'timestamp': timestamp})
    print("[LoRa] Kein Empfang (API)")
    return jsonify({'msg': None, 'raw': None, 'timestamp': None})

@lora_api.route('/api/lora/messages', methods=['GET'])
def lora_messages():
    return jsonify(messages)

@lora_api.route('/api/lora/address', methods=['GET'])
def lora_address():
    return jsonify({'address': lora_hat.addr})

@lora_api.route('/api/lora/frequency', methods=['GET', 'POST'])
def lora_frequency():
    if hasattr(lora_hat, 'freq'):
        if request.method == 'GET':
            return jsonify({'frequency': lora_hat.freq})
        elif request.method == 'POST':
            data = request.get_json(force=True)
            freq = float(data.get('frequency', lora_hat.FREQ))
            # Only allow 868 MHz
            if freq == lora_hat.FREQ:
                lora_hat.set_frequency(freq)
                save_lora_frequency(lora_hat.freq)
                confirmed_freq = lora_hat.freq
                return jsonify({'frequency': confirmed_freq, 'status': 'ok'})
            else:
                return jsonify({'error': 'Frequency not allowed. Only 868 MHz is supported.'}), 400
    return jsonify({'error': 'Not supported'}), 400

@lora_api.route('/api/lora/test', methods=['POST'])
def lora_test():
    # Test: Sende eine Testnachricht mit Prefix und prüfe Empfang
    import datetime
    PREFIX = "LORATEST_"
    test_msg = f"{PREFIX}{lora_hat.addr}_{datetime.datetime.now().strftime('%H%M%S')}"
    lora_hat.send(test_msg.encode('utf-8'))
    # Warte kurz und versuche zu empfangen
    import time
    time.sleep(1)
    received = lora_hat.receive()
    if received and test_msg in received.decode('utf-8', errors='replace'):
        result = 'OK'
    else:
        result = 'FAILED'
    return jsonify({'test_sent': test_msg, 'result': result, 'received': received.decode('utf-8', errors='replace') if received else None})

def lora_receive_background():
    import datetime
    PREFIX = "LORATEST_"
    print("[LoRa] Starte Hintergrund-Empfangsthread")
    while True:
        r = lora_hat.receive()
        if r:
            msg = r.decode('utf-8', errors='replace')
            timestamp = datetime.datetime.now().isoformat(timespec='seconds')
            print(f"[LoRa] Empfangen (Background): {msg}")
            messages.append({'type': 'recv', 'msg': msg, 'timestamp': timestamp})
            print(f"[LoRa] Empfang gespeichert (Background): {msg}")
            if len(messages) > MAX_LORA_MSGS:
                messages[:] = messages[-MAX_LORA_MSGS:]
            save_lora_messages(messages)
            if msg.startswith(PREFIX) and str(lora_hat.addr) not in msg:
                # Antworte mit gleichem Inhalt zurück
                print(f"[LoRa] Reply to test: {msg}")
                lora_hat.send(msg.encode('utf-8'))
        import time
        time.sleep(1)

# Start background thread for receiving
threading.Thread(target=lora_receive_background, daemon=True).start()
