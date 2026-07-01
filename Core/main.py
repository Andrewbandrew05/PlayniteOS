import os
import subprocess
import asyncio
import json
import yaml
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import base64

app = FastAPI()

# Load authorized keys from a config file
CONFIG_PATH = "C:\\PlayniteOS\\Core\\config.yaml"

def get_authorized_keys():
    # Instead of just reading a list, we can read an 'authorized_keys' file
    # similar to how Linux SSH does it.
    keys = []
    with open("C:\\PlayniteOS\\Core\\authorized_keys", "r") as f:
        for line in f:
            if line.startswith("ssh-ed25519"):
                # Extract the Base64 part, decode it, and take the last 32 bytes
                parts = line.split()
                raw_bytes = base64.b64decode(parts[1])
                keys.append(raw_bytes[-32:].hex())
    return keys

def verify_signature(public_key_hex: str, signature_hex: str, message: bytes):
    try:
        verify_key = VerifyKey(bytes.fromhex(public_key_hex))
        verify_key.verify(message, bytes.fromhex(signature_hex))
        return True
    except (BadSignatureError, ValueError):
        return False

@app.post("/action/{script_name}")
async def run_action(
    script_name: str, 
    request: Request,
    x_public_key: str = Header(None),
    x_signature: str = Header(None)
):
    # 1. Security Check: Is the key authorized?
    if x_public_key not in get_authorized_keys():
        raise HTTPException(status_code=403, detail="Unauthorized Key")

    # 2. Security Check: Verify the signature of the request body
    body = await request.body()
    if not verify_signature(x_public_key, x_signature, body):
        raise HTTPException(status_code=401, detail="Invalid Signature")

    # 3. Execution: Map script_name to actual .ps1 files (Whitelist only!)
    script_map = {
        "create_standard_user": "C:\\PlayniteOS\\Scripts\\CreateStandardWindowsUser.ps1",
        "create_gamer_user":    "C:\\PlayniteOS\\Scripts\\CreateGamerWindowsUser.ps1",
        "kick_user":            "C:\\PlayniteOS\\Scripts\\KickUser.ps1",
        "unlock_admin":         "C:\\PlayniteOS\\Scripts\\UnlockAdmin.ps1",
        "switch_user":          "C:\\PlayniteOS\\Scripts\\SwitchUser.ps1",
    }

    if script_name not in script_map:
        raise HTTPException(status_code=404, detail="Action not found")

    # 4. Parse params from the already-cached body bytes
    params = json.loads(body)
    args = []
    for key, value in params.items():
        args.extend([f"-{key}", str(value)])

    script_path = script_map[script_name]

    async def generate():
        process = await asyncio.create_subprocess_exec(
            "powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_path, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        async for line in process.stdout:
            yield line.decode("utf-8", errors="replace")
        await process.wait()
        yield f"[done] exit code: {process.returncode}\n"

    return StreamingResponse(generate(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
