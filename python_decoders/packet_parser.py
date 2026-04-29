#!/usr/bin/env python3
"""
AFHDS-2A Packet Parser

Parses different packet types in FlySky AFHDS-2A protocol:
- Bind packets (0xBB)
- Control packets (0x58)
- Telemetry packets (various)

Reference: https://github.com/pascallanger/DIY-Multiprotocol-TX-Module
"""

import struct
from .crc import CRC16


class PacketType:
    """Known AFHDS-2A packet types."""
    BIND = 0xBB
    CONTROL = 0x58
    TELEMETRY_AA55 = 0xAA  # Telemetry variant 1
    TELEMETRY_AA56 = 0x56  # Telemetry variant 2
    

class AFHDSPacket:
    """Base class for all AFHDS-2A packets."""
    
    def __init__(self, raw_data):
        self.raw_data = bytearray(raw_data)
        self.packet_type = None
        self.tx_id = None
        self.crc = None
        self.crc_valid = False
        
        if len(raw_data) > 0:
            self.packet_type = raw_data[0]
    
    def verify_crc(self):
        """Verify packet CRC."""
        if len(self.raw_data) < 3:
            return False
        
        crc_calc = CRC16()
        data_part = self.raw_data[:-2]
        crc_bytes = self.raw_data[-2:]
        
        self.crc_valid = crc_calc.verify(data_part, crc_bytes)
        self.crc = crc_bytes[0] | (crc_bytes[1] << 8)
        
        return self.crc_valid
    
    def __repr__(self):
        return f"<AFHDSPacket type=0x{self.packet_type:02X} len={len(self.raw_data)} crc_ok={self.crc_valid}>"


class BindPacket(AFHDSPacket):
    """
    Bind packet structure.
    
    Format:
        Byte 0: 0xBB (packet type)
        Bytes 1-4: TX ID (4 bytes, little-endian)
        Bytes 5-20: Hop channels (16 bytes)
        Bytes 21-22: CRC-16
    
    Total: 23 bytes
    """
    
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.hop_channels = []
        self.parse()
    
    def parse(self):
        """Parse bind packet fields."""
        if len(self.raw_data) < 23:
            return False
        
        # TX ID (bytes 1-4)
        self.tx_id = struct.unpack('<I', self.raw_data[1:5])[0]
        
        # Hop channels (bytes 5-20)
        self.hop_channels = list(self.raw_data[5:21])
        
        # Verify CRC
        self.verify_crc()
        
        return True
    
    def get_frequencies(self):
        """
        Convert hop channels to actual frequencies.
        
        Returns:
            list: Frequencies in MHz
        """
        frequencies = []
        for channel in self.hop_channels:
            # Formula: 2400 MHz + (channel × 0.5 MHz)
            freq_mhz = 2400.0 + (channel * 0.5)
            frequencies.append(freq_mhz)
        return frequencies
    
    def __repr__(self):
        return (f"<BindPacket tx_id=0x{self.tx_id:08X} "
                f"channels={len(self.hop_channels)} crc_ok={self.crc_valid}>")


class ControlPacket(AFHDSPacket):
    """
    Control packet structure.
    
    Format:
        Byte 0: 0x58 (packet type)
        Bytes 1-4: TX ID (4 bytes, little-endian)
        Bytes 5-32: Channel data (14 channels × 2 bytes each, little-endian)
        Bytes 33-34: CRC-16
    
    Total: 35 bytes
    
    Channel values:
        - Range: 1000-2000 microseconds
        - Center: 1500 microseconds
        - Format: uint16, little-endian
    """
    
    CHANNEL_COUNT = 14
    
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.channels = []
        self.parse()
    
    def parse(self):
        """Parse control packet fields."""
        if len(self.raw_data) < 35:
            return False
        
        # TX ID (bytes 1-4)
        self.tx_id = struct.unpack('<I', self.raw_data[1:5])[0]
        
        # Channel data (bytes 5-32)
        self.channels = []
        for i in range(self.CHANNEL_COUNT):
            offset = 5 + (i * 2)
            # Little-endian uint16
            channel_value = struct.unpack('<H', self.raw_data[offset:offset+2])[0]
            self.channels.append(channel_value)
        
        # Verify CRC
        self.verify_crc()
        
        return True
    
    def get_channel_percent(self, channel_index):
        """
        Get channel value as percentage (-100% to +100%).
        
        Args:
            channel_index: 0-13
            
        Returns:
            float: Percentage (-100.0 to +100.0)
        """
        if channel_index >= len(self.channels):
            return None
        
        value = self.channels[channel_index]
        # Center at 1500, range ±500
        percent = ((value - 1500) / 500.0) * 100.0
        return percent
    
    def get_stick_positions(self):
        """
        Get standard stick positions.
        
        Returns:
            dict: {'aileron', 'elevator', 'throttle', 'rudder'}
        """
        return {
            'aileron': self.channels[0] if len(self.channels) > 0 else None,
            'elevator': self.channels[1] if len(self.channels) > 1 else None,
            'throttle': self.channels[2] if len(self.channels) > 2 else None,
            'rudder': self.channels[3] if len(self.channels) > 3 else None,
        }
    
    def __repr__(self):
        return (f"<ControlPacket tx_id=0x{self.tx_id:08X} "
                f"channels={len(self.channels)} crc_ok={self.crc_valid}>")


class PacketParser:
    """Main packet parser - detects and parses packet types."""
    
    def __init__(self):
        self.crc = CRC16()
    
    def parse(self, raw_data):
        """
        Parse raw packet data and return appropriate packet object.
        
        Args:
            raw_data: bytes or bytearray
            
        Returns:
            AFHDSPacket subclass or None
        """
        if len(raw_data) < 3:
            return None
        
        packet_type = raw_data[0]
        
        # Determine packet type and parse accordingly
        if packet_type == PacketType.BIND:
            return BindPacket(raw_data)
        
        elif packet_type == PacketType.CONTROL:
            return ControlPacket(raw_data)
        
        else:
            # Unknown packet type, return generic
            return AFHDSPacket(raw_data)
    
    def find_packets(self, bit_stream, sync_word=None):
        """
        Find packets in a decoded bit stream.
        
        Args:
            bit_stream: bytearray of decoded data
            sync_word: Optional sync word to search for (e.g., b'\\x54\\x75\\xc5\\x2a')
            
        Returns:
            list: List of packet objects
        """
        packets = []
        
        # If sync word provided, search for it
        if sync_word:
            # Search for sync word occurrences
            for i in range(len(bit_stream) - len(sync_word)):
                if bit_stream[i:i+len(sync_word)] == sync_word:
                    # Found sync word, try to parse packet after it
                    packet_start = i + len(sync_word)
                    
                    # Try different packet lengths
                    for length in [23, 35, 40]:  # Common packet sizes
                        if packet_start + length <= len(bit_stream):
                            candidate = bit_stream[packet_start:packet_start+length]
                            packet = self.parse(candidate)
                            
                            if packet and packet.verify_crc():
                                packets.append(packet)
                                break
        else:
            # Scan for packet type bytes
            i = 0
            while i < len(bit_stream) - 3:
                packet_type = bit_stream[i]
                
                # Try to parse based on type
                if packet_type == PacketType.BIND and i + 23 <= len(bit_stream):
                    packet = BindPacket(bit_stream[i:i+23])
                    if packet.verify_crc():
                        packets.append(packet)
                        i += 23
                        continue
                
                elif packet_type == PacketType.CONTROL and i + 35 <= len(bit_stream):
                    packet = ControlPacket(bit_stream[i:i+35])
                    if packet.verify_crc():
                        packets.append(packet)
                        i += 35
                        continue
                
                i += 1
        
        return packets


def test_packet_parser():
    """Test packet parser with sample data."""
    
    print("Testing Packet Parser")
    print("-" * 50)
    
    parser = PacketParser()
    crc = CRC16()
    
    # Test 1: Bind packet
    print("Test 1 - Bind Packet:")
    
    bind_data = bytearray([
        0xBB,  # Type
        0xA3, 0xB2, 0xC1, 0xD0,  # TX ID
        # 16 hop channels
        0x0D, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF,
        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
    ])
    bind_data = crc.append_crc(bind_data)
    
    bind_packet = parser.parse(bind_data)
    print(f"  Packet: {bind_packet}")
    print(f"  TX ID: 0x{bind_packet.tx_id:08X}")
    print(f"  Hop Channels: {[f'0x{ch:02X}' for ch in bind_packet.hop_channels[:4]]}...")
    print(f"  Frequencies: {bind_packet.get_frequencies()[:4]}... MHz")
    print(f"  CRC Valid: {bind_packet.crc_valid}")
    print()
    
    # Test 2: Control packet
    print("Test 2 - Control Packet:")
    
    control_data = bytearray([
        0x58,  # Type
        0xA3, 0xB2, 0xC1, 0xD0,  # TX ID
    ])
    
    # Add 14 channel values (center = 1500)
    for i in range(14):
        value = 1500 + (i * 10)  # Slight variation
        control_data.extend(struct.pack('<H', value))
    
    control_data = crc.append_crc(control_data)
    
    control_packet = parser.parse(control_data)
    print(f"  Packet: {control_packet}")
    print(f"  TX ID: 0x{control_packet.tx_id:08X}")
    print(f"  Channels: {control_packet.channels[:4]}...")
    print(f"  Stick positions: {control_packet.get_stick_positions()}")
    print(f"  CRC Valid: {control_packet.crc_valid}")
    print()
    
    # Test 3: Invalid CRC
    print("Test 3 - Invalid CRC:")
    bad_data = bytearray(bind_data)
    bad_data[-1] ^= 0xFF  # Corrupt CRC
    
    bad_packet = parser.parse(bad_data)
    print(f"  Packet: {bad_packet}")
    print(f"  CRC Valid: {bad_packet.crc_valid}")
    
    print("-" * 50)


if __name__ == "__main__":
    test_packet_parser()
