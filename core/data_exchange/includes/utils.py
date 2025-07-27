import base64
from io import BytesIO


def encode_output_buffer(buffer: BytesIO) -> str:
    """Encodes buffer values to Base64 string"""
    return base64.b64encode(buffer.getvalue()).decode()


def decode_output_result(base64_string: str) -> bytes:
    """Decodes Base64 string to bytes"""
    base64_bytes = base64_string.encode("ascii")
    return base64.b64decode(base64_bytes)
