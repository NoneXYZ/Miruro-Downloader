import base64
import json
import zlib
import gzip

def encode_payload(payload_dict: dict) -> str:
    json_str = json.dumps(payload_dict)
    return base64.urlsafe_b64encode(json_str.encode('utf-8')).decode('utf-8').rstrip('=')

def decode_payload(raw_payload: str) -> dict:
    padding_needed = len(raw_payload) % 4
    if padding_needed:
        raw_payload += "=" * (4 - padding_needed)
        
    decoded_bytes = base64.urlsafe_b64decode(raw_payload)
    return json.loads(decoded_bytes.decode('utf-8'))

def decode_response(raw_response: str, hex_key: str) -> dict:
    try:
        padding_needed = len(raw_response) % 4
        if padding_needed:
            raw_response += "=" * (4 - padding_needed)
            
        raw_bytes = bytearray(base64.urlsafe_b64decode(raw_response))
        
        if raw_bytes[0] == 31 and raw_bytes[1] == 139:
            decrypted_bytes = raw_bytes
        else:
            key_bytes = bytes.fromhex(hex_key)
            decrypted_bytes = bytearray(len(raw_bytes))
            
            for i in range(len(raw_bytes)):
                decrypted_bytes[i] = raw_bytes[i] ^ key_bytes[i % len(key_bytes)]
                
        if decrypted_bytes[0] == 31 and decrypted_bytes[1] == 139:
            decompressed = gzip.decompress(decrypted_bytes)
        else:
            decompressed = zlib.decompress(decrypted_bytes)
            
        decoded_string = decompressed.decode('utf-8')
        
        try:
            return {"type": "json", "data": json.loads(decoded_string)}
        except json.JSONDecodeError:
            return {"type": "txt", "data": decoded_string}
            
    except Exception as e:
        return {"type": "error", "data": str(e)}
