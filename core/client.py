from curl_cffi import requests  
from core.codec import encode_payload, decode_response
from core.config import MIRURO_PIPE_URL, DEFAULT_HEADERS, _VAULT_BYTES

def fetch_miruro_pipe(path, method, payload: dict) -> dict:
    full_payload = {
        "path": path, 
        "method": method, 
        "query": payload
    }
    
    try:
        encoded_string = encode_payload(full_payload)
        
        response = requests.get(
            f"{MIRURO_PIPE_URL}?e={encoded_string}", 
            headers=DEFAULT_HEADERS,
            impersonate="chrome110",
            timeout=60
        )
        response.raise_for_status()
        
        raw_text = response.text.strip()
        clean_json = decode_response(raw_text, _VAULT_BYTES[14:].hex())
        return clean_json
            
    except Exception as e:
        print(f"Pipe request failed: {str(e)}")
        return {"error": f"Pipe request failed: {str(e)}"}
