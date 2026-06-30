import os
import requests
import json
from nacl.signing import SigningKey
from cryptography.hazmat.primitives import serialization

# --- CONFIGURATION ---
TARGET_IP = "192.168.10.52"  # Replace with your Windows machine IP
TARGET_PORT = "8080"

def get_signing_key_from_ssh():
    # Automatically expands '~' to '/home/username'
    key_path = os.path.expanduser("~/.ssh/snowpiercerPlayniteOS")
    
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Could not find SSH key at {key_path}")

    with open(key_path, "rb") as key_file:
        # Load the OpenSSH formatted private key
        # If your key has a passphrase, replace None with b"your_passphrase"
        private_key = serialization.load_ssh_private_key(
            key_file.read(),
            password=None 
        )
    
    # Extract the raw 32-byte seed required by PyNaCl
    raw_seed = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    return SigningKey(raw_seed)

def send_action(action_name, params):
    try:
        signing_key = get_signing_key_from_ssh()
        public_key_hex = signing_key.verify_key.encode().hex()

        url = f"http://{TARGET_IP}:{TARGET_PORT}/action/{action_name}"
        
        body_json = json.dumps(params)
        body_bytes = body_json.encode('utf-8')

        # Sign the body
        signature = signing_key.sign(body_bytes).signature.hex()

        headers = {
            "X-Public-Key": public_key_hex,
            "X-Signature": signature,
            "Content-Type": "application/json"
        }

        response = requests.post(url, data=body_bytes, headers=headers)
        print(f"--- Action: {action_name} ---")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

    except Exception as e:
        print(f"Error: {e}")

# --- TEST ---
send_action("create_user", {"UserName": "Imtired", "Password": "urmom"})
