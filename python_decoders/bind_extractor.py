#!/usr/bin/env python3
"""
Bind Packet Extractor

Extracts hop channels from AFHDS-2A bind mode captures.
This is the key step - you need the hop table to track frequency hopping.

Usage:
    python3 bind_extractor.py <demodulated_bits_file>
    
Example:
    python3 bind_extractor.py ../captures/bind_demod.bin
"""

import sys
import numpy as np
from fec_decoder import FECDecoder
from packet_parser import PacketParser, BindPacket


class BindExtractor:
    """Extract and decode bind packets from demodulated data."""
    
    def __init__(self):
        self.fec = FECDecoder()
        self.parser = PacketParser()
        
        # Known sync patterns
        self.PREAMBLE = bytearray([0xAA, 0xAA, 0xAA, 0xAA])
        self.SYNC_WORD = bytearray([0x54, 0x75, 0xC5, 0x2A])
    
    def load_bits(self, filename):
        """Load demodulated bits from file."""
        try:
            # Bits are typically saved as uint8 (0 or 1)
            bits = np.fromfile(filename, dtype=np.uint8)
            print(f"Loaded {len(bits)} bits from {filename}")
            return bits
        except Exception as e:
            print(f"Error loading file: {e}")
            return None
    
    def find_preamble(self, bits, min_length=16):
        """
        Find preamble pattern (alternating 0101...).
        
        Args:
            bits: numpy array of bits
            min_length: minimum preamble length in bits
            
        Returns:
            list: Indices where preamble starts
        """
        positions = []
        
        # Look for alternating pattern
        for i in range(len(bits) - min_length):
            # Check for 0101... pattern
            is_preamble = True
            for j in range(min_length):
                expected = j % 2
                if bits[i + j] != expected:
                    is_preamble = False
                    break
            
            if is_preamble:
                positions.append(i)
        
        return positions
    
    def extract_packets(self, filename):
        """
        Main extraction function.
        
        Workflow:
        1. Load bits
        2. Apply FEC decoding
        3. Search for bind packet structure
        4. Parse and validate
        """
        
        print("=" * 60)
        print("AFHDS-2A Bind Packet Extractor")
        print("=" * 60)
        print()
        
        # Load bits
        bits = self.load_bits(filename)
        if bits is None:
            return None
        
        print(f"Bit stream length: {len(bits)} bits")
        print()
        
        # Apply FEC decoding
        print("Applying FEC (7,4) decoding...")
        decoded_bytes = self.fec.decode_bytes(bits)
        print(f"Decoded to {len(decoded_bytes)} bytes")
        print(f"First 32 bytes: {decoded_bytes[:32].hex()}")
        print()
        
        # Search for bind packets
        print("Searching for bind packets...")
        
        # Method 1: Search for sync word
        packets = self.parser.find_packets(decoded_bytes, sync_word=self.SYNC_WORD)
        
        if not packets:
            # Method 2: Direct scan
            print("Sync word not found, trying direct scan...")
            packets = self.parser.find_packets(decoded_bytes)
        
        # Filter for bind packets only
        bind_packets = [p for p in packets if isinstance(p, BindPacket)]
        
        print(f"Found {len(bind_packets)} valid bind packet(s)")
        print()
        
        # Display results
        if bind_packets:
            for i, packet in enumerate(bind_packets):
                self.display_bind_packet(packet, i + 1)
        else:
            print("No valid bind packets found!")
            print()
            self.troubleshooting_tips()
        
        return bind_packets
    
    def display_bind_packet(self, packet, number=1):
        """Display bind packet information."""
        
        print(f"{'=' * 60}")
        print(f"Bind Packet #{number}")
        print(f"{'=' * 60}")
        print(f"TX ID: 0x{packet.tx_id:08X}")
        print(f"CRC Valid: {packet.crc_valid}")
        print()
        
        print("Hop Channels:")
        print("-" * 60)
        print(f"{'Ch':<4} {'Hex':<6} {'Decimal':<8} {'Frequency (MHz)':<15}")
        print("-" * 60)
        
        frequencies = packet.get_frequencies()
        for i, (channel, freq) in enumerate(zip(packet.hop_channels, frequencies)):
            print(f"{i:<4} 0x{channel:02X}   {channel:<8} {freq:<15.1f}")
        
        print()
        
        # Save to file
        output_file = f"hop_channels_{packet.tx_id:08X}.txt"
        self.save_hop_channels(packet, output_file)
        print(f"Hop channels saved to: {output_file}")
        print()
    
    def save_hop_channels(self, packet, filename):
        """Save hop channels to file for later use."""
        
        with open(filename, 'w') as f:
            f.write(f"# AFHDS-2A Hop Channels\n")
            f.write(f"# TX ID: 0x{packet.tx_id:08X}\n")
            f.write(f"# Extracted from bind packet\n")
            f.write(f"\n")
            
            frequencies = packet.get_frequencies()
            
            f.write(f"TX_ID=0x{packet.tx_id:08X}\n")
            f.write(f"\n")
            f.write(f"# Channel values (hex)\n")
            f.write("HOP_CHANNELS_HEX=" + ",".join([f"0x{ch:02X}" for ch in packet.hop_channels]) + "\n")
            f.write(f"\n")
            f.write(f"# Channel values (decimal)\n")
            f.write("HOP_CHANNELS_DEC=" + ",".join([str(ch) for ch in packet.hop_channels]) + "\n")
            f.write(f"\n")
            f.write(f"# Frequencies (MHz)\n")
            f.write("FREQUENCIES=" + ",".join([f"{freq:.1f}" for freq in frequencies]) + "\n")
    
    def troubleshooting_tips(self):
        """Print troubleshooting tips if no packets found."""
        
        print("Troubleshooting Tips:")
        print("-" * 60)
        print("1. Verify TX is in bind mode:")
        print("   - Hold bind button while powering on")
        print("   - LED should blink rapidly")
        print()
        print("2. Check demodulation:")
        print("   - Are bits mostly random? → Frequency offset issue")
        print("   - Do you see repeating patterns? → Good sign")
        print()
        print("3. Verify FEC decoding:")
        print("   - Run: python3 fec_decoder.py")
        print("   - All tests should pass")
        print()
        print("4. Check bit alignment:")
        print("   - Bits might be shifted by 1-7 positions")
        print("   - Try rotating the bit stream")
        print()
        print("5. Capture more data:")
        print("   - Bind packets are sent every ~3ms")
        print("   - Capture at least 10 seconds")
        print("-" * 60)


def main():
    """Main entry point."""
    
    if len(sys.argv) < 2:
        print("Usage: python3 bind_extractor.py <demodulated_bits_file>")
        print()
        print("Example:")
        print("  python3 bind_extractor.py ../captures/bind_demod.bin")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    extractor = BindExtractor()
    packets = extractor.extract_packets(filename)
    
    if packets:
        print()
        print("SUCCESS! You now have the hop channels.")
        print("Next step: Use these channels to track frequency hopping")
        print("           in realtime_monitor.py")
    else:
        print()
        print("FAILED! No bind packets found.")
        print("Review troubleshooting tips above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
