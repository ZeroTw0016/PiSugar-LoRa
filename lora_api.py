from flask import Blueprint, jsonify
from waveshare_lora_hat import WaveshareSX1262LoRaHAT
import threading

lora_hat = WaveshareSX1262LoRaHAT()
lora_api = Blueprint('lora_api', __name__)

# Shared message buffer
messages = []

@lora_api.route('/api/lora/send', methods=['POST'])
def lora_send():
    from flask import request
    data = request.get_json(force=True)
    msg = data.get('msg', '')
    lora_hat.send(msg.encode('utf-8'))
    messages.append({'type': 'sent', 'msg': msg})
    return jsonify({'status': 'sent'})

@lora_api.route('/api/lora/receive', methods=['GET'])
def lora_receive():
    r = lora_hat.receive()
    if r:
        msg = r.decode('utf-8', errors='replace')
        print(f"[LoRa] Empfangen (API): {msg}")
        messages.append({'type': 'recv', 'msg': msg})
        return jsonify({'msg': msg})
    return jsonify({'msg': None})

@lora_api.route('/api/lora/messages', methods=['GET'])
def lora_messages():
    return jsonify(messages)

def lora_receive_background():
    while True:
        r = lora_hat.receive()
        if r:
            msg = r.decode('utf-8', errors='replace')
            print(f"[LoRa] Empfangen (Background): {msg}")
            messages.append({'type': 'recv', 'msg': msg})
        import time
        time.sleep(1)

# Start background thread for receiving
threading.Thread(target=lora_receive_background, daemon=True).start()
