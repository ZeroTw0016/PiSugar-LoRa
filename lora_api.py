from flask import Blueprint, jsonify, request
from waveshare_lora_hat import WaveshareSX1262LoRaHAT
import threading
import json
import os

lora_hat = WaveshareSX1262LoRaHAT()
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
    lora_hat.send(msg.encode('utf-8'))
    timestamp = datetime.datetime.now().isoformat(timespec='seconds')
    messages.append({'type': 'sent', 'msg': msg, 'timestamp': timestamp})
    if len(messages) > MAX_LORA_MSGS:
        messages[:] = messages[-MAX_LORA_MSGS:]
    save_lora_messages(messages)
    return jsonify({'status': 'sent'})

@lora_api.route('/api/lora/receive', methods=['GET'])
def lora_receive():
    import datetime
    r = lora_hat.receive()
    if r:
        msg = r.decode('utf-8', errors='replace')
        timestamp = datetime.datetime.now().isoformat(timespec='seconds')
        print(f"[LoRa] Empfangen (API): {msg}")
        messages.append({'type': 'recv', 'msg': msg, 'timestamp': timestamp})
        if len(messages) > MAX_LORA_MSGS:
            messages[:] = messages[-MAX_LORA_MSGS:]
        save_lora_messages(messages)
        return jsonify({'msg': msg, 'timestamp': timestamp})
    return jsonify({'msg': None, 'timestamp': None})

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
            # Only allow switching to 868 or Germany frequency for receive
            allowed = [lora_hat.FREQ, getattr(lora_hat, 'GERMANY_FREQ', 869.525)]
            if freq in allowed:
                lora_hat.set_frequency(freq)
                return jsonify({'frequency': lora_hat.freq, 'status': 'ok'})
            else:
                return jsonify({'error': 'Frequency not allowed'}), 400
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
    while True:
        r = lora_hat.receive()
        if r:
            msg = r.decode('utf-8', errors='replace')
            timestamp = datetime.datetime.now().isoformat(timespec='seconds')
            print(f"[LoRa] Empfangen (Background): {msg}")
            messages.append({'type': 'recv', 'msg': msg, 'timestamp': timestamp})
            if len(messages) > MAX_LORA_MSGS:
                messages[:] = messages[-MAX_LORA_MSGS:]
            save_lora_messages(messages)
            # Automatisches Reply auf Testnachrichten mit Prefix
            if msg.startswith(PREFIX) and str(lora_hat.addr) not in msg:
                # Antworte mit gleichem Inhalt zurück
                print(f"[LoRa] Reply to test: {msg}")
                lora_hat.send(msg.encode('utf-8'))
        import time
        time.sleep(1)

# Start background thread for receiving
threading.Thread(target=lora_receive_background, daemon=True).start()
