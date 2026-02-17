"""
Image Storage and Transmission Manager
Handles local storage, batching, and WiFi transmission to ground station
"""

import os
import json
import logging
import threading
import socket
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import hashlib
import queue

logger = logging.getLogger(__name__)


class TransmissionState(Enum):
    """States for image transmission"""
    PENDING = "pending"           # Waiting to send
    SENDING = "sending"           # Currently uploading
    SENT = "sent"                 # Successfully sent
    FAILED = "failed"             # Send failed
    RETRY = "retry"               # Retrying after failure


@dataclass
class ImageMetadata:
    """Metadata for a captured image"""
    filename: str
    filepath: str
    timestamp: float = field(default_factory=time.time)
    size_bytes: int = 0
    md5_hash: str = ""
    profile: str = "CAPTURING"     # Profile used for capture
    drone_altitude: float = 0.0
    transmission_state: str = TransmissionState.PENDING.value
    transmission_attempts: int = 0
    last_attempt: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Create from dictionary"""
        return cls(**data)


class StorageManager:
    """Manages local storage of captured images"""
    
    def __init__(self, config: Dict):
        """
        Initialize storage manager
        
        Args:
            config: Configuration dictionary with storage settings
        """
        self.config = config
        storage_cfg = config.get("storage", {})
        
        # Directory structure
        self.base_dir = storage_cfg.get("local_path", "mission_data")
        self.images_dir = os.path.join(self.base_dir, "images")
        self.tx_queue_dir = os.path.join(self.base_dir, "tx_queue")
        self.metadata_dir = os.path.join(self.base_dir, "metadata")
        self.sent_dir = os.path.join(self.base_dir, "sent")
        
        # Create directories
        for dir_path in [self.base_dir, self.images_dir, self.tx_queue_dir, 
                         self.metadata_dir, self.sent_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Storage limits
        self.max_storage_mb = storage_cfg.get("max_raw_storage_mb", 1000)
        self.min_storage_warn_mb = storage_cfg.get("min_storage_mb_warn", 200)
        self.min_storage_critical_mb = storage_cfg.get("min_storage_mb_fatal", 50)
        
        # Image metadata tracking
        self.image_metadata: Dict[str, ImageMetadata] = {}
        self._load_metadata_index()
        
        logger.info(f"StorageManager initialized")
        logger.info(f"  Images dir: {self.images_dir}")
        logger.info(f"  TX queue dir: {self.tx_queue_dir}")
        logger.info(f"  Max storage: {self.max_storage_mb}MB")
    
    def save_image(self, image_bytes: bytes, profile: str = "CAPTURING",
                   drone_altitude: float = 0.0) -> Optional[ImageMetadata]:
        """
        Save captured image to disk and track metadata
        
        Args:
            image_bytes: Raw image data
            profile: Capture profile name
            drone_altitude: Drone altitude at time of capture
            
        Returns:
            ImageMetadata object if successful, None otherwise
        """
        try:
            # Check storage space
            available_mb = self._get_available_storage_mb()
            image_size_mb = len(image_bytes) / (1024 * 1024)
            
            if available_mb < self.min_storage_critical_mb:
                logger.error(f"Critical storage: {available_mb:.1f}MB available")
                self._cleanup_old_images()
                return None
            
            if available_mb < self.min_storage_warn_mb:
                logger.warning(f"Low storage: {available_mb:.1f}MB available")
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"img_{timestamp}.jpg"
            filepath = os.path.join(self.images_dir, filename)
            
            # Write image to disk
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            # Calculate metadata
            file_size = os.path.getsize(filepath)
            md5_hash = self._calculate_md5(filepath)
            
            # Create metadata record
            metadata = ImageMetadata(
                filename=filename,
                filepath=filepath,
                size_bytes=file_size,
                md5_hash=md5_hash,
                profile=profile,
                drone_altitude=drone_altitude
            )
            
            # Store metadata
            self.image_metadata[filename] = metadata
            self._save_metadata_index()
            
            logger.debug(f"Image saved: {filename} ({file_size/1024:.1f}KB)")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            return None
    
    def get_pending_images(self, max_count: int = 100) -> List[ImageMetadata]:
        """
        Get list of images pending transmission
        
        Args:
            max_count: Maximum images to return
            
        Returns:
            List of ImageMetadata objects for pending images
        """
        pending = [
            m for m in self.image_metadata.values()
            if m.transmission_state == TransmissionState.PENDING.value
        ]
        return sorted(pending, key=lambda x: x.timestamp)[:max_count]
    
    def mark_transmitted(self, filename: str) -> bool:
        """
        Mark image as successfully transmitted
        
        Args:
            filename: Image filename
            
        Returns:
            True if successful
        """
        try:
            if filename not in self.image_metadata:
                logger.warning(f"Metadata not found: {filename}")
                return False
            
            metadata = self.image_metadata[filename]
            metadata.transmission_state = TransmissionState.SENT.value
            
            # Move to sent folder
            if os.path.exists(metadata.filepath):
                sent_path = os.path.join(self.sent_dir, filename)
                os.rename(metadata.filepath, sent_path)
                metadata.filepath = sent_path
            
            self._save_metadata_index()
            logger.debug(f"Image marked as transmitted: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking transmitted: {e}")
            return False
    
    def mark_transmission_failed(self, filename: str) -> bool:
        """
        Mark image transmission as failed
        
        Args:
            filename: Image filename
            
        Returns:
            True if successful
        """
        try:
            if filename not in self.image_metadata:
                return False
            
            metadata = self.image_metadata[filename]
            metadata.transmission_state = TransmissionState.FAILED.value
            metadata.transmission_attempts += 1
            metadata.last_attempt = time.time()
            
            self._save_metadata_index()
            return True
            
        except Exception as e:
            logger.error(f"Error marking failed: {e}")
            return False
    
    def get_storage_status(self) -> Dict:
        """
        Get current storage status
        
        Returns:
            Dictionary with storage information
        """
        pending = len([m for m in self.image_metadata.values() 
                      if m.transmission_state == TransmissionState.PENDING.value])
        sent = len([m for m in self.image_metadata.values() 
                   if m.transmission_state == TransmissionState.SENT.value])
        failed = len([m for m in self.image_metadata.values() 
                     if m.transmission_state == TransmissionState.FAILED.value])
        
        total_size_mb = sum(m.size_bytes for m in self.image_metadata.values()) / (1024 * 1024)
        available_mb = self._get_available_storage_mb()
        
        return {
            "total_images": len(self.image_metadata),
            "pending": pending,
            "sent": sent,
            "failed": failed,
            "total_size_mb": total_size_mb,
            "available_mb": available_mb,
            "status": self._get_storage_health_status()
        }
    
    def _get_available_storage_mb(self) -> float:
        """Get available storage in MB"""
        try:
            stat = os.statvfs(self.base_dir)
            available_bytes = stat.f_bavail * stat.f_frsize
            return available_bytes / (1024 * 1024)
        except Exception as e:
            logger.error(f"Error getting storage: {e}")
            return 0.0
    
    def _get_storage_health_status(self) -> str:
        """Get health status of storage"""
        available = self._get_available_storage_mb()
        if available < self.min_storage_critical_mb:
            return "CRITICAL"
        elif available < self.min_storage_warn_mb:
            return "WARNING"
        else:
            return "OK"
    
    def _calculate_md5(self, filepath: str) -> str:
        """Calculate MD5 hash of file"""
        try:
            md5 = hashlib.md5()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating MD5: {e}")
            return ""
    
    def _cleanup_old_images(self) -> int:
        """
        Delete oldest images to free up space
        
        Returns:
            Number of images deleted
        """
        try:
            deleted_count = 0
            # Sort by transmission state (sent first), then by age
            images_to_delete = sorted(
                self.image_metadata.values(),
                key=lambda x: (x.transmission_state != TransmissionState.SENT.value, x.timestamp)
            )
            
            available = self._get_available_storage_mb()
            while available < self.min_storage_warn_mb and images_to_delete:
                metadata = images_to_delete.pop(0)
                
                if os.path.exists(metadata.filepath):
                    os.remove(metadata.filepath)
                    del self.image_metadata[metadata.filename]
                    deleted_count += 1
                    available = self._get_available_storage_mb()
            
            if deleted_count > 0:
                self._save_metadata_index()
                logger.info(f"Cleaned up {deleted_count} old images")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up images: {e}")
            return 0
    
    def _save_metadata_index(self):
        """Save metadata index to file"""
        try:
            index_file = os.path.join(self.metadata_dir, "index.json")
            index_data = {
                filename: metadata.to_dict()
                for filename, metadata in self.image_metadata.items()
            }
            
            with open(index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving metadata index: {e}")
    
    def _load_metadata_index(self):
        """Load metadata index from file"""
        try:
            index_file = os.path.join(self.metadata_dir, "index.json")
            
            if os.path.exists(index_file):
                with open(index_file, 'r') as f:
                    index_data = json.load(f)
                
                for filename, data in index_data.items():
                    self.image_metadata[filename] = ImageMetadata.from_dict(data)
                
                logger.info(f"Loaded metadata for {len(self.image_metadata)} images")
                
        except Exception as e:
            logger.error(f"Error loading metadata index: {e}")


class ImageTransmitter:
    """Handles image transmission over WiFi to ground station"""
    
    def __init__(self, config: Dict, storage_manager: StorageManager):
        """
        Initialize image transmitter
        
        Args:
            config: Configuration dictionary
            storage_manager: StorageManager instance
        """
        self.config = config
        self.storage = storage_manager
        
        comm_cfg = config.get("communication", {})
        self.ground_station_ip = comm_cfg.get("ground_station_ip", "0.0.0.0")
        self.ground_station_port = comm_cfg.get("ground_station_port", 9999)
        
        # Batching settings
        batch_cfg = config.get("batching", {})
        self.batch_size = batch_cfg.get("batch_size", 10)
        self.batch_timeout_sec = batch_cfg.get("time_threshold_sec", 30)
        
        # Link quality thresholds for transmission
        link_cfg = comm_cfg.get("link_thresholds", {})
        self.rssi_good = 50                                    # Send at full speed
        self.rssi_degraded = link_cfg.get("rssi_degraded", 70) # Reduce batch size
        self.rssi_critical = link_cfg.get("rssi_critical", 85) # Don't send
        
        # State
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._tx_queue: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        
        # Statistics
        self.images_sent = 0
        self.bytes_sent = 0
        self.send_failures = 0
        
        logger.info(f"ImageTransmitter initialized")
        logger.info(f"  Ground station: {self.ground_station_ip}:{self.ground_station_port}")
        logger.info(f"  Batch size: {self.batch_size}")
    
    def start(self):
        """Start transmission thread"""
        if self.running:
            logger.warning("Transmitter already running")
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._transmission_loop, daemon=True)
        self._thread.start()
        logger.info("Image transmitter started")
    
    def stop(self):
        """Stop transmission thread"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Image transmitter stopped")
    
    def transmit_images(self, rssi: Optional[int] = None) -> Tuple[int, int]:
        """
        Transmit pending images based on link quality
        
        Args:
            rssi: Current RSSI signal strength (lower is better)
                  None = assume good link
                  
        Returns:
            Tuple of (images_sent, bytes_sent)
        """
        if rssi is None:
            rssi = 50  # Assume good link if not provided
        
        # Determine batch size based on link quality
        batch_size = self._calculate_batch_size(rssi)
        
        if batch_size == 0:
            logger.debug(f"Link quality poor (RSSI {rssi}), not transmitting")
            return 0, 0
        
        # Get images to send
        pending = self.storage.get_pending_images(max_count=batch_size)
        
        if not pending:
            return 0, 0
        
        logger.info(f"Transmitting {len(pending)} images (batch size: {batch_size}, RSSI: {rssi})")
        
        sent_count = 0
        bytes_sent = 0
        
        for metadata in pending:
            if self._send_image(metadata):
                self.storage.mark_transmitted(metadata.filename)
                self.images_sent += 1
                bytes_sent += metadata.size_bytes
                sent_count += 1
            else:
                self.storage.mark_transmission_failed(metadata.filename)
                self.send_failures += 1
        
        self.bytes_sent += bytes_sent
        
        logger.info(f"Transmitted {sent_count}/{len(pending)} images ({bytes_sent/(1024):.1f}KB)")
        
        return sent_count, bytes_sent
    
    def _calculate_batch_size(self, rssi: int) -> int:
        """
        Calculate batch size based on link quality
        
        Args:
            rssi: RSSI value (lower is better, higher is stronger)
                  
        Returns:
            Batch size (0 = don't send)
        """
        if rssi < self.rssi_good:
            return self.batch_size  # Full batch
        elif rssi < self.rssi_degraded:
            return max(1, self.batch_size // 2)  # Half batch
        elif rssi < self.rssi_critical:
            return 1  # Single image only
        else:
            return 0  # Don't send
    
    def _send_image(self, metadata: ImageMetadata) -> bool:
        """
        Send a single image to ground station
        
        Args:
            metadata: Image metadata
            
        Returns:
            True if successful
        """
        try:
            if not os.path.exists(metadata.filepath):
                logger.error(f"Image file not found: {metadata.filepath}")
                return False
            
            # Read image data
            with open(metadata.filepath, 'rb') as f:
                image_data = f.read()
            
            # Create transmission packet
            packet = self._create_transmission_packet(metadata, image_data)
            
            # Send to ground station
            success = self._send_packet(packet)
            
            if success:
                logger.debug(f"Image sent: {metadata.filename}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending image: {e}")
            return False
    
    def _create_transmission_packet(self, metadata: ImageMetadata, 
                                    image_data: bytes) -> bytes:
        """
        Create transmission packet with metadata and image
        
        Packet format:
        - Header: "IMG_PKT" (7 bytes)
        - Filename length: uint16 (2 bytes)
        - Filename: variable
        - Metadata JSON length: uint16 (2 bytes)
        - Metadata JSON: variable
        - Image data length: uint32 (4 bytes)
        - Image data: variable
        - MD5 checksum: 32 bytes
        
        Args:
            metadata: Image metadata
            image_data: Raw image data
            
        Returns:
            Complete packet as bytes
        """
        try:
            # Metadata as JSON
            meta_dict = {
                "filename": metadata.filename,
                "timestamp": metadata.timestamp,
                "size_bytes": metadata.size_bytes,
                "profile": metadata.profile,
                "altitude": metadata.drone_altitude
            }
            meta_json = json.dumps(meta_dict).encode('utf-8')
            
            # Build packet
            packet = b"IMG_PKT"  # Header
            packet += len(metadata.filename).to_bytes(2, 'big')
            packet += metadata.filename.encode('utf-8')
            packet += len(meta_json).to_bytes(2, 'big')
            packet += meta_json
            packet += len(image_data).to_bytes(4, 'big')
            packet += image_data
            packet += metadata.md5_hash.encode('utf-8')
            
            return packet
            
        except Exception as e:
            logger.error(f"Error creating packet: {e}")
            return b""
    
    def _send_packet(self, packet: bytes) -> bool:
        """
        Send packet to ground station via UDP/TCP
        
        Args:
            packet: Packet data to send
            
        Returns:
            True if successful
        """
        try:
            if self.config.get("communication", {}).get("protocol") == "tcp":
                return self._send_tcp(packet)
            else:
                return self._send_udp(packet)
                
        except Exception as e:
            logger.error(f"Error sending packet: {e}")
            return False
    
    def _send_udp(self, packet: bytes) -> bool:
        """Send packet via UDP"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            sock.sendto(packet, (self.ground_station_ip, self.ground_station_port))
            sock.close()
            return True
        except Exception as e:
            logger.error(f"UDP send failed: {e}")
            return False
    
    def _send_tcp(self, packet: bytes) -> bool:
        """Send packet via TCP"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.ground_station_ip, self.ground_station_port))
            sock.sendall(packet)
            sock.close()
            return True
        except Exception as e:
            logger.error(f"TCP send failed: {e}")
            return False
    
    def _transmission_loop(self):
        """Background transmission loop"""
        while self.running:
            try:
                # Transmit queued images periodically
                self.transmit_images()
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in transmission loop: {e}")
                time.sleep(1)
    
    def get_transmission_stats(self) -> Dict:
        """
        Get transmission statistics
        
        Returns:
            Dictionary with stats
        """
        return {
            "images_sent": self.images_sent,
            "bytes_sent": self.bytes_sent,
            "send_failures": self.send_failures,
            "pending": len(self.storage.get_pending_images())
        }


class ImageManager:
    """
    High-level manager for image storage and transmission
    Integrates StorageManager and ImageTransmitter
    """
    
    def __init__(self, config: Dict):
        """
        Initialize image manager
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.storage = StorageManager(config)
        self.transmitter = ImageTransmitter(config, self.storage)
        
        logger.info("ImageManager initialized")
    
    def save_captured_image(self, image_bytes: bytes, profile: str = "CAPTURING",
                           altitude: float = 0.0) -> Optional[str]:
        """
        Save captured image
        
        Args:
            image_bytes: Image data
            profile: Capture profile
            altitude: Drone altitude
            
        Returns:
            Image filename if successful, None otherwise
        """
        metadata = self.storage.save_image(image_bytes, profile, altitude)
        if metadata:
            return metadata.filename
        return None
    
    def start_transmission(self):
        """Start automatic image transmission"""
        self.transmitter.start()
    
    def stop_transmission(self):
        """Stop automatic image transmission"""
        self.transmitter.stop()
    
    def transmit_batch(self, link_quality_rssi: Optional[int] = None) -> Dict:
        """
        Transmit batch of images based on link quality
        
        Args:
            link_quality_rssi: Link quality (RSSI value)
            
        Returns:
            Transmission statistics
        """
        sent, bytes_sent = self.transmitter.transmit_images(link_quality_rssi)
        return {
            "images_sent": sent,
            "bytes_sent": bytes_sent,
            "storage": self.storage.get_storage_status(),
            "transmission": self.transmitter.get_transmission_stats()
        }
    
    def get_status(self) -> Dict:
        """
        Get overall system status
        
        Returns:
            Comprehensive status dictionary
        """
        return {
            "storage": self.storage.get_storage_status(),
            "transmission": self.transmitter.get_transmission_stats(),
            "ground_station": {
                "ip": self.transmitter.ground_station_ip,
                "port": self.transmitter.ground_station_port,
                "protocol": self.config.get("communication", {}).get("protocol", "udp")
            }
        }
