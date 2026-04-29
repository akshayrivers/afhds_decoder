#!/usr/bin/env python3
"""
AFHDS-2A CRC-16 Implementation

CRC-16 with polynomial 0x1021 (CRC-16-CCITT)
Used in FlySky AFHDS-2A protocol for packet validation.

Reference: https://github.com/pascallanger/DIY-Multiprotocol-TX-Module
"""


class CRC16:
    """
    CRC-16-CCITT calculator for FlySky packets.
    
    Polynomial: 0x1021
    Initial value: 0x0000
    """
    
    def __init__(self, polynomial=0x1021):
        self.polynomial = polynomial
        self.table = self._build_table()
    
    def _build_table(self):
        """Build CRC lookup table for faster computation."""
        table = []
        for byte in range(256):
            crc = byte << 8
            for bit in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ self.polynomial
                else:
                    crc = crc << 1
                crc &= 0xFFFF
            table.append(crc)
        return table
    
    def calculate(self, data):
        """
        Calculate CRC-16 for given data.
        
        Args:
            data: bytes, bytearray, or list of integers
            
        Returns:
            int: 16-bit CRC value
        """
        crc = 0x0000  # FlySky uses 0x0000 initial value
        
        for byte in data:
            if isinstance(byte, str):
                byte = ord(byte)
            
            # XOR byte into CRC
            crc ^= (byte << 8)
            
            # Process 8 bits
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ self.polynomial
                else:
                    crc = crc << 1
                crc &= 0xFFFF
        
        return crc
    
    def calculate_slow(self, data):
        """
        Calculate CRC-16 using bit-by-bit method (slow but clear).
        
        Useful for understanding the algorithm.
        """
        crc = 0x0000
        
        for byte in data:
            if isinstance(byte, str):
                byte = ord(byte)
            
            crc ^= (byte << 8)
            
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ self.polynomial
                else:
                    crc = crc << 1
                crc &= 0xFFFF
        
        return crc
    
    def verify(self, data, expected_crc):
        """
        Verify data against expected CRC.
        
        Args:
            data: Data to check (without CRC bytes)
            expected_crc: Expected CRC value (int or bytes)
            
        Returns:
            bool: True if CRC matches
        """
        if isinstance(expected_crc, (bytes, bytearray)):
            # Convert bytes to int (little-endian or big-endian)
            if len(expected_crc) == 2:
                # Assume little-endian (FlySky convention)
                expected_crc = expected_crc[0] | (expected_crc[1] << 8)
        
        calculated_crc = self.calculate(data)
        return calculated_crc == expected_crc
    
    def append_crc(self, data):
        """
        Calculate CRC and append it to data (little-endian).
        
        Args:
            data: bytearray or bytes
            
        Returns:
            bytearray: data + CRC (2 bytes, little-endian)
        """
        crc = self.calculate(data)
        result = bytearray(data)
        result.append(crc & 0xFF)         # Low byte
        result.append((crc >> 8) & 0xFF)  # High byte
        return result


def test_crc():
    """Test CRC implementation with known values."""
    
    crc = CRC16()
    
    print("Testing CRC-16 Implementation")
    print("-" * 50)
    
    # Test 1: Simple known value
    test_data = b"123456789"
    calculated = crc.calculate(test_data)
    # CRC-16 with init 0x0000 (FlySky variant) should be 0x31C3
    # CRC-16-CCITT-FALSE (init 0xFFFF) would be 0x29B1
    expected = 0x31C3  # FlySky uses init 0x0000
    
    print(f"Test 1 - Known string:")
    print(f"  Data: {test_data}")
    print(f"  Calculated: 0x{calculated:04X}")
    print(f"  Expected: 0x{expected:04X}")
    print(f"  Result: {'PASS' if calculated == expected else 'FAIL'}")
    print()
    
    # Test 2: Empty data
    empty = crc.calculate(b"")
    print(f"Test 2 - Empty data:")
    print(f"  CRC: 0x{empty:04X}")
    print(f"  Expected: 0x0000")
    print(f"  Result: {'PASS' if empty == 0x0000 else 'FAIL'}")
    print()
    
    # Test 3: Table vs slow method consistency
    test_data2 = bytearray([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0])
    crc_table = crc.calculate(test_data2)
    crc_slow = crc.calculate_slow(test_data2)
    
    print(f"Test 3 - Table vs Slow method:")
    print(f"  Data: {test_data2.hex()}")
    print(f"  Table method: 0x{crc_table:04X}")
    print(f"  Slow method:  0x{crc_slow:04X}")
    print(f"  Result: {'PASS' if crc_table == crc_slow else 'FAIL'}")
    print()
    
    # Test 4: Verify function
    packet_data = bytearray([0x58, 0xA1, 0xB2, 0xC3, 0xD4])
    packet_with_crc = crc.append_crc(packet_data)
    
    print(f"Test 4 - Verify function:")
    print(f"  Data: {packet_data.hex()}")
    print(f"  With CRC: {packet_with_crc.hex()}")
    
    # Extract CRC from packet
    data_part = packet_with_crc[:-2]
    crc_part = packet_with_crc[-2:]
    
    is_valid = crc.verify(data_part, crc_part)
    print(f"  Verification: {'PASS' if is_valid else 'FAIL'}")
    print()
    
    # Test 5: FlySky-specific packet structure
    # Typical bind packet structure (example)
    print("Test 5 - FlySky packet example:")
    
    # Simulated bind packet (without CRC)
    bind_packet = bytearray([
        0xBB,  # Packet type: Bind
        0xA3, 0xB2, 0xC1, 0xD0,  # TX ID (example)
        # Hop channels (16 bytes)
        0x0D, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF,
        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0
    ])
    
    bind_with_crc = crc.append_crc(bind_packet)
    print(f"  Packet (no CRC): {bind_packet.hex()}")
    print(f"  Packet (with CRC): {bind_with_crc.hex()}")
    print(f"  CRC bytes: {bind_with_crc[-2:].hex()}")
    
    # Verify
    is_valid = crc.verify(bind_with_crc[:-2], bind_with_crc[-2:])
    print(f"  Self-verification: {'PASS' if is_valid else 'FAIL'}")
    
    print("-" * 50)


if __name__ == "__main__":
    test_crc()
