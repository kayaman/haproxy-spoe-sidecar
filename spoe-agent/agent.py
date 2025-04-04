import socket
import struct
import json
import time
import requests
from threading import Thread
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('spoe-agent')

# Configuration
DOWNSTREAM_URL = os.getenv('DOWNSTREAM_URL', 'http://http-event-processor:8080/http-events')
BUFFER_SIZE = int(os.getenv('BUFFER_SIZE', '16384'))
LISTEN_ADDR = os.getenv('LISTEN_ADDR', '0.0.0.0')
LISTEN_PORT = int(os.getenv('LISTEN_PORT', '9000'))

# Message type constants
SPOP_HELLO = 1
SPOP_DISC = 2
SPOP_NOTIFY = 3
SPOP_ACK = 4

# Frame types
SPOA_FRAME_T_HELLO = 1
SPOA_FRAME_T_NOTIFY = 2
SPOA_FRAME_T_ACK = 3
SPOA_FRAME_T_DISCONNECT = 4

# Data types
SPOE_DATA_T_NULL = 0
SPOE_DATA_T_BOOL = 1
SPOE_DATA_T_INT32 = 2
SPOE_DATA_T_UINT32 = 3
SPOE_DATA_T_INT64 = 4
SPOE_DATA_T_UINT64 = 5
SPOE_DATA_T_IPV4 = 6
SPOE_DATA_T_IPV6 = 7
SPOE_DATA_T_STR = 8
SPOE_DATA_T_BIN = 9

def decode_frame_header(data):
    if len(data) < 4:
        return None, None, None, 0
    
    frame_id = struct.unpack('!I', data[0:4])[0]
    frame_type = (frame_id & 0xF0000000) >> 28
    stream_id = (frame_id & 0x0FFFFFFF)
    frame_len = struct.unpack('!I', data[4:8])[0]
    
    return frame_type, stream_id, data[8:8+frame_len], 8+frame_len

def encode_frame(frame_type, stream_id, data):
    frame_id = (frame_type << 28) | (stream_id & 0x0FFFFFFF)
    frame_len = len(data)
    
    frame = struct.pack('!II', frame_id, frame_len) + data
    return frame

def decode_kv(data, offset):
    name_len = struct.unpack('!I', data[offset:offset+4])[0]
    offset += 4
    name = data[offset:offset+name_len].decode('utf-8')
    offset += name_len
    
    data_type = data[offset]
    offset += 1
    
    value = None
    if data_type == SPOE_DATA_T_NULL:
        value = None
    elif data_type == SPOE_DATA_T_BOOL:
        value = bool(data[offset])
        offset += 1
    elif data_type == SPOE_DATA_T_INT32:
        value = struct.unpack('!i', data[offset:offset+4])[0]
        offset += 4
    elif data_type == SPOE_DATA_T_UINT32:
        value = struct.unpack('!I', data[offset:offset+4])[0]
        offset += 4
    elif data_type == SPOE_DATA_T_STR:
        value_len = struct.unpack('!I', data[offset:offset+4])[0]
        offset += 4
        value = data[offset:offset+value_len].decode('utf-8')
        offset += value_len
    elif data_type == SPOE_DATA_T_BIN:
        value_len = struct.unpack('!I', data[offset:offset+4])[0]
        offset += 4
        value = data[offset:offset+value_len]
        offset += value_len
    
    return name, value, offset

def handle_hello(data):
    response = bytearray()
    
    # Add "version" parameter
    response.extend(struct.pack('!I', 7))  # Length of "version"
    response.extend(b'version')
    response.append(SPOE_DATA_T_STR)
    response.extend(struct.pack('!I', 4))  # Length of "2.0"
    response.extend(b'2.0')
    
    # Add "max-frame-size" parameter
    response.extend(struct.pack('!I', 13))  # Length of "max-frame-size"
    response.extend(b'max-frame-size')
    response.append(SPOE_DATA_T_UINT32)
    response.extend(struct.pack('!I', BUFFER_SIZE))
    
    # Add "capabilities" parameter
    response.extend(struct.pack('!I', 12))  # Length of "capabilities"
    response.extend(b'capabilities')
    response.append(SPOE_DATA_T_STR)
    response.extend(struct.pack('!I', 7))  # Length of "pipelining"
    response.extend(b'pipelining')
    
    return response

def handle_notify(data):
    response = bytearray()
    offset = 0
    
    # Extract message name length and name
    msg_len = struct.unpack('!I', data[offset:offset+4])[0]
    offset += 4
    msg_name = data[offset:offset+msg_len].decode('utf-8')
    offset += msg_len
    
    # Number of arguments
    nb_args = struct.unpack('!H', data[offset:offset+2])[0]
    offset += 2
    
    # Process arguments
    args = {}
    for _ in range(nb_args):
        name, value, offset = decode_kv(data, offset)
        args[name] = value
    
    # Determine if this is a request or response message
    event_type = "request" if "method" in args else "response"
    
    # Prepare data for downstream processing
    event_data = {
        "type": event_type,
        "timestamp": time.time(),
        "data": args
    }
    
    # Send to downstream processing in a non-blocking way
    Thread(target=send_to_downstream, args=(event_data,)).start()
    
    # Return an empty ACK
    return response

def send_to_downstream(data):
    try:
        requests.post(
            DOWNSTREAM_URL,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        logger.info(f"Sent {data['type']} event to downstream processor")
    except Exception as e:
        logger.error(f"Failed to send to downstream: {e}")

def handle_client(client_socket, address):
    logger.info(f"New connection from {address}")
    
    try:
        data = client_socket.recv(BUFFER_SIZE)
        while data:
            frame_type, stream_id, frame_data, consumed = decode_frame_header(data)
            
            if frame_type is None:
                # Incomplete frame, read more data
                more_data = client_socket.recv(BUFFER_SIZE)
                if not more_data:
                    break
                data += more_data
                continue
            
            response_data = bytearray()
            
            if frame_type == SPOA_FRAME_T_HELLO:
                response_data = handle_hello(frame_data)
            elif frame_type == SPOA_FRAME_T_NOTIFY:
                response_data = handle_notify(frame_data)
            elif frame_type == SPOA_FRAME_T_DISCONNECT:
                break
            
            # Send response frame
            response_frame = encode_frame(SPOA_FRAME_T_ACK, stream_id, response_data)
            client_socket.sendall(response_frame)
            
            # Remove processed data
            data = data[consumed:]
            
            # If no more data, read more
            if not data:
                data = client_socket.recv(BUFFER_SIZE)
    
    except Exception as e:
        logger.error(f"Error handling client: {e}")
    finally:
        client_socket.close()
        logger.info(f"Connection from {address} closed")

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((LISTEN_ADDR, LISTEN_PORT))
        server_socket.listen(10)
        logger.info(f"SPOE agent listening on {LISTEN_ADDR}:{LISTEN_PORT}")
        
        while True:
            client_socket, address = server_socket.accept()
            Thread(target=handle_client, args=(client_socket, address)).start()
    
    except KeyboardInterrupt:
        logger.info("Server shutting down")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()