import base64, sys

def write_b64(dest, b64_str):
    data = base64.b64decode(b64_str)
    with open(dest, 'wb') as f:
        f.write(data)
    print(f'Wrote {len(data)} bytes to {dest}')

def append_b64(dest, b64_str):
    data = base64.b64decode(b64_str)
    with open(dest, 'ab') as f:
        f.write(data)
    print(f'Appended {len(data)} bytes to {dest}')
