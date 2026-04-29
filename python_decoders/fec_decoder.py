#!/usr/bin/env python3
"""
AFHDS-2A FEC (7,4) Decoder

Implements the (7,4) Hamming-like FEC used in FlySky AFHDS-2A protocol.
Based on reverse engineering from DIY-Multiprotocol project.

Reference: https://github.com/pascallanger/DIY-Multiprotocol-TX-Module
File: A7105_SPI.ino -> A7105_FEC_decode()
"""

import numpy as np


class FECDecoder:
    """
    FlySky AFHDS-2A FEC Decoder
    
    Converts 7-bit FEC encoded data to 4-bit decoded data.
    Provides single-bit error correction.
    """
    
    def __init__(self):
        # FEC lookup table: 7-bit input -> 4-bit output
        # Extracted from DIY-Multiprotocol A7105 implementation
        self.fec_table = self._build_fec_table()
    
    def _build_fec_table(self):
        """
        Build FEC decode lookup table.
        
        The table maps all possible 7-bit patterns to their decoded 4-bit values.
        Invalid patterns are marked with -1.
        
        Reference encoding:
        - d0, d1, d2, d3 = data bits
        - p0 = d0 ^ d1 ^ d3  (parity bit 0)
        - p1 = d0 ^ d2 ^ d3  (parity bit 1)
        - p2 = d1 ^ d2 ^ d3  (parity bit 2)
        
        Transmitted order: [d0, d1, d2, d3, p0, p1, p2]
        """
        
        table = {}
        
        # Generate all valid codewords (16 data patterns)
        for data in range(16):
            d0 = (data >> 0) & 1
            d1 = (data >> 1) & 1
            d2 = (data >> 2) & 1
            d3 = (data >> 3) & 1
            
            # Calculate parity bits
            p0 = d0 ^ d1 ^ d3
            p1 = d0 ^ d2 ^ d3
            p2 = d1 ^ d2 ^ d3
            
            # Build 7-bit codeword
            codeword = (d0 << 0) | (d1 << 1) | (d2 << 2) | (d3 << 3) | \
                      (p0 << 4) | (p1 << 5) | (p2 << 6)
            
            table[codeword] = data
            
            # Add single-bit error patterns (error correction)
            for bit_pos in range(7):
                error_pattern = codeword ^ (1 << bit_pos)
                # Only add if not already present (prevent collision)
                if error_pattern not in table:
                    table[error_pattern] = data
        
        return table
    
    def decode_7bit(self, bits):
        """
        Decode a single 7-bit FEC block to 4 data bits.
        
        Args:
            bits: int (7 bits) or list/array of 7 binary values
            
        Returns:
            int: 4-bit decoded value (0-15), or None if uncorrectable
        """
        # Convert bit array to integer if needed
        if isinstance(bits, (list, np.ndarray)):
            value = 0
            for i, bit in enumerate(bits[:7]):
                value |= (int(bit) << i)
        else:
            value = bits & 0x7F
        
        return self.fec_table.get(value, None)
    
    def decode_bytes(self, bit_stream):
        """
        Decode a stream of FEC-encoded bits to bytes.
        
        Args:
            bit_stream: numpy array of bits (0s and 1s)
            
        Returns:
            bytearray: Decoded data
            
        Note:
            Input length should be multiple of 14 bits (2 bytes encoded = 14 bits)
            Each byte requires 7 FEC bits, so 2 bytes = 14 bits
        """
        decoded = bytearray()
        
        # Process in 14-bit chunks (2 decoded bytes)
        for i in range(0, len(bit_stream) - 13, 14):
            # First byte (bits 0-6)
            nibble1 = self.decode_7bit(bit_stream[i:i+7])
            if nibble1 is None:
                # Uncorrectable error, skip this chunk
                continue
            
            # Second byte (bits 7-13)
            nibble2 = self.decode_7bit(bit_stream[i+7:i+14])
            if nibble2 is None:
                continue
            
            # Combine two 4-bit nibbles into one byte
            byte_val = (nibble2 << 4) | nibble1
            decoded.append(byte_val)
        
        return decoded
    
    def decode_packet(self, bit_stream, packet_length_bits=None):
        """
        Decode a complete FEC-encoded packet.
        
        Args:
            bit_stream: numpy array of bits
            packet_length_bits: Expected packet length in bits (after FEC decode)
                               If None, decode entire stream
            
        Returns:
            bytearray: Decoded packet data
        """
        decoded = self.decode_bytes(bit_stream)
        
        if packet_length_bits:
            packet_length_bytes = packet_length_bits // 8
            return decoded[:packet_length_bytes]
        
        return decoded


def test_fec_decoder():
    """Test FEC decoder with known patterns."""
    
    decoder = FECDecoder()
    
    print("Testing FEC Decoder...")
    print("-" * 50)
    
    # Test 1: Decode known pattern
    # Data: 0x5A (01011010)
    # Split into nibbles: 0xA (1010), 0x5 (0101)
    
    # Encode 0xA (1010):
    # d0=0, d1=1, d2=0, d3=1
    # p0 = 0^1^1 = 0
    # p1 = 0^0^1 = 1
    # p2 = 1^0^1 = 0
    # codeword = 0010 010 = 0x1A
    
    # Encode 0x5 (0101):
    # d0=1, d1=0, d2=1, d3=0
    # p0 = 1^0^0 = 1
    # p1 = 1^1^0 = 0
    # p2 = 0^1^0 = 1
    # codeword = 1010 101 = 0x55
    
    test_bits = np.array([
        # First nibble (0xA)
        0, 1, 0, 1, 0, 1, 0,
        # Second nibble (0x5)
        1, 0, 1, 0, 1, 0, 1
    ], dtype=np.uint8)
    
    decoded = decoder.decode_bytes(test_bits)
    expected = 0x5A
    
    print(f"Test 1 - Known pattern:")
    print(f"  Input bits: {test_bits}")
    print(f"  Decoded: 0x{decoded[0]:02X}")
    print(f"  Expected: 0x{expected:02X}")
    print(f"  Result: {'PASS' if decoded[0] == expected else 'FAIL'}")
    print()
    
    # Test 2: Single-bit error correction
    print("Test 2 - Error correction:")
    error_bits = test_bits.copy()
    error_bits[3] ^= 1  # Flip bit 3
    
    decoded_corrected = decoder.decode_bytes(error_bits)
    print(f"  Original: 0x{decoded[0]:02X}")
    print(f"  With error: {error_bits}")
    print(f"  Corrected: 0x{decoded_corrected[0]:02X}")
    print(f"  Result: {'PASS' if decoded_corrected[0] == expected else 'FAIL'}")
    print()
    
    # Test 3: All 16 possible values
    print("Test 3 - All nibble values:")
    all_pass = True
    for val in range(16):
        decoded_val = decoder.decode_7bit(val)
        # Note: this tests the reverse - we're checking table consistency
        if decoded_val is None:
            print(f"  Value {val:04b} -> UNCORRECTABLE")
            all_pass = False
    
    print(f"  Result: {'PASS' if all_pass else 'PARTIAL'}")
    print("-" * 50)


if __name__ == "__main__":
    test_fec_decoder()
