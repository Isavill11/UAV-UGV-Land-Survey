#!/usr/bin/env python3
"""
Ground Station Image Receiver
Receives transmitted images from UAV via UDP/TCP
Verifies MD5 checksums and saves to organized directory structure
"""

import socket
import json
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime
from threading import Thread, Lock
import struct

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImageReceiver:
    """Receive and store images transmitted from UAV"""
    
    def __init__(self, listen_ip: str = "0.0.0.0", listen_port: int = 9999, 
                 save_dir: str = "./received_images", protocol: str = "udp"):
        """
        Initialize receiver
        
        Args:
            listen_ip: IP to listen on (0.0.0.0 for all interfaces)
            listen_port: Port to listen on
            save_dir: Directory to save received images
            protocol: "udp" or "tcp"
        """
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.save_dir = Path(save_dir)
        self.protocol = protocol.lower()
        self.running = False
        self.socket = None
        self.lock = Lock()
        
        # Statistics
        self.images_received = 0
        self.images_verified = 0
        self.images_failed = 0
        self.bytes_received = 0
        
        # Create save directories
        self.save_dir.mkdir(parents=True, exist_ok=True)
        (self.save_dir / "verified").mkdir(exist_ok=True)
        (self.save_dir / "unverified").mkdir(exist_ok=True)
        (self.save_dir / "failed").mkdir(exist_ok=True)
        (self.save_dir / "metadata").mkdir(exist_ok=True)
        
        logger.info(f"Image receiver initialized: {protocol.upper()} on {listen_ip}:{listen_port}")
        logger.info(f"Save directory: {self.save_dir}")
    
    def start(self):
        """Start listening for images"""
        if self.protocol == "udp":
            self._start_udp()
        elif self.protocol == "tcp":
            self._start_tcp()
        else:
            logger.error(f"Unknown protocol: {self.protocol}")
    
    def _start_udp(self):
        """Start UDP receiver"""
        logger.info("Starting UDP receiver...")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.listen_ip, self.listen_port))
        
        self.running = True
        logger.info(f"UDP listening on {self.listen_ip}:{self.listen_port}")
        
        try:
            while self.running:
                try:
                    data, addr = self.socket.recvfrom(65536)  # 64KB UDP max
                    logger.debug(f"Received {len(data)} bytes from {addr}")
                    
                    # Process in background thread
                    Thread(target=self._process_packet, args=(data, addr), daemon=True).start()
                
                except Exception as e:
                    logger.error(f"UDP receive error: {e}")
        
        finally:
            self.socket.close()
    
    def _start_tcp(self):
        """Start TCP receiver"""
        logger.info("Starting TCP receiver...")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.listen_ip, self.listen_port))
        self.socket.listen(5)
        
        self.running = True
        logger.info(f"TCP listening on {self.listen_ip}:{self.listen_port}")
        
        try:
            while self.running:
                try:
                    client_socket, addr = self.socket.accept()
                    logger.info(f"TCP connection from {addr}")
                    
                    # Receive full packet from client
                    Thread(target=self._receive_tcp_packet, args=(client_socket, addr), daemon=True).start()
                
                except Exception as e:
                    logger.error(f"TCP accept error: {e}")
        
        finally:
            self.socket.close()
    
    def _receive_tcp_packet(self, client_socket, addr):
        """Receive complete packet over TCP"""
        try:
            data = b""
            while True:
                chunk = client_socket.recv(8192)
                if not chunk:
                    break
                data += chunk
            
            if data:
                logger.debug(f"Received {len(data)} bytes via TCP from {addr}")
                self._process_packet(data, addr)
        
        except Exception as e:
            logger.error(f"TCP receive error: {e}")
        
        finally:
            client_socket.close()
    
    def _process_packet(self, data: bytes, source: tuple):
        """
        Process received image packet
        
        Packet format:
        Header (7B) | Filename Len (2B) | Filename (var) | Meta Len (2B) | 
        Metadata JSON (var) | Image Len (4B) | Image Data (var) | MD5 Hash (32B)
        """
        try:
            if len(data) < 45:  # Minimum: 7 header + 2 fname_len + 2 meta_len + 4 img_len + 32 md5
                logger.error(f"Packet too short: {len(data)} bytes")
                with self.lock:
                    self.images_failed += 1
                return
            
            offset = 0
            
            # Parse header
            header = data[offset:offset+7].decode('ascii', errors='ignore')
            offset += 7
            
            if header != "IMG_PKT":
                logger.error(f"Invalid packet header: {header}")
                with self.lock:
                    self.images_failed += 1
                return
            
            # Parse filename length and filename
            fname_len = struct.unpack('>H', data[offset:offset+2])[0]
            offset += 2
            
            if offset + fname_len > len(data):
                logger.error("Filename extends beyond packet")
                with self.lock:
                    self.images_failed += 1
                return
            
            filename = data[offset:offset+fname_len].decode('utf-8')
            offset += fname_len
            
            # Parse metadata length and metadata
            meta_len = struct.unpack('>H', data[offset:offset+2])[0]
            offset += 2
            
            if offset + meta_len > len(data):
                logger.error("Metadata extends beyond packet")
                with self.lock:
                    self.images_failed += 1
                return
            
            metadata_json = data[offset:offset+meta_len].decode('utf-8')
            try:
                metadata = json.loads(metadata_json)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid metadata JSON: {e}")
                metadata = {}
            
            offset += meta_len
            
            # Parse image length and image data
            img_len = struct.unpack('>I', data[offset:offset+4])[0]
            offset += 4
            
            if offset + img_len > len(data) - 32:  # -32 for MD5 hash
                logger.error(f"Image data extends beyond packet: {img_len} vs {len(data) - offset - 32}")
                with self.lock:
                    self.images_failed += 1
                return
            
            image_data = data[offset:offset+img_len]
            offset += img_len
            
            # Parse MD5 hash
            received_md5 = data[offset:offset+32].decode('ascii')
            
            # Verify MD5
            calculated_md5 = hashlib.md5(image_data).hexdigest()
            md5_valid = (received_md5 == calculated_md5)
            
            if not md5_valid:
                logger.warning(f"MD5 mismatch for {filename}: "
                              f"expected {received_md5}, got {calculated_md5}")
            
            # Save image and metadata
            self._save_image(filename, image_data, metadata, md5_valid)
            
            with self.lock:
                self.images_received += 1
                self.bytes_received += img_len
                if md5_valid:
                    self.images_verified += 1
                else:
                    logger.warning(f"Image saved but MD5 verification failed: {filename}")
            
            logger.info(f"✓ Received: {filename} ({len(image_data)} bytes) from {source[0]}:{source[1]}")
        
        except Exception as e:
            logger.error(f"Error processing packet: {e}", exc_info=True)
            with self.lock:
                self.images_failed += 1
    
    def _save_image(self, filename: str, image_data: bytes, metadata: dict, md5_valid: bool):
        """Save image and metadata to organized directory"""
        try:
            # Choose directory based on MD5 validity
            subdir = "verified" if md5_valid else "unverified"
            image_path = self.save_dir / subdir / filename
            
            # Create subdirectories by date if metadata available
            if "timestamp" in metadata:
                try:
                    dt = datetime.fromisoformat(metadata["timestamp"])
                    date_dir = self.save_dir / subdir / dt.strftime("%Y-%m-%d")
                    date_dir.mkdir(parents=True, exist_ok=True)
                    image_path = date_dir / filename
                except Exception:
                    pass  # Fall back to base directory
            
            # Ensure directory exists
            image_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save image
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            logger.debug(f"Saved image: {image_path}")
            
            # Save metadata as separate JSON file
            if metadata:
                metadata_path = self.save_dir / "metadata" / f"{filename}.json"
                metadata_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2, default=str)
                
                logger.debug(f"Saved metadata: {metadata_path}")
        
        except Exception as e:
            logger.error(f"Error saving image: {e}")
    
    def stop(self):
        """Stop receiver"""
        logger.info("Stopping receiver...")
        self.running = False
        if self.socket:
            self.socket.close()
        
        logger.info("="*60)
        logger.info("Receiver Statistics:")
        logger.info(f"  Images received: {self.images_received}")
        logger.info(f"  Images verified (MD5 OK): {self.images_verified}")
        logger.info(f"  Images failed: {self.images_failed}")
        logger.info(f"  Total bytes received: {self.bytes_received / 1024 / 1024:.2f} MB")
        logger.info("="*60)
    
    def get_stats(self):
        """Get receiver statistics"""
        with self.lock:
            return {
                "images_received": self.images_received,
                "images_verified": self.images_verified,
                "images_failed": self.images_failed,
                "bytes_received": self.bytes_received,
            }


def main():
    """Entry point for ground station receiver"""
    parser = argparse.ArgumentParser(
        description="Ground station receiver for UAV transmitted images"
    )
    parser.add_argument("--ip", default="0.0.0.0", 
                       help="Listen IP address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9999,
                       help="Listen port (default: 9999)")
    parser.add_argument("--protocol", choices=["udp", "tcp"], default="udp",
                       help="Protocol (default: udp)")
    parser.add_argument("--save-dir", default="./received_images",
                       help="Directory to save images (default: ./received_images)")
    
    args = parser.parse_args()
    
    receiver = ImageReceiver(
        listen_ip=args.ip,
        listen_port=args.port,
        save_dir=args.save_dir,
        protocol=args.protocol
    )
    
    try:
        receiver.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        receiver.stop()


if __name__ == "__main__":
    main()
