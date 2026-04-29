#!/usr/bin/env python3
"""
Control Packet Decoder

Decodes AFHDS-2A control packets to extract stick positions and switch states.

Usage:
    python3 control_decoder.py <demodulated_data_file>
"""

import sys
import numpy as np
from fec_decoder import FECDecoder
from packet_parser import PacketParser, ControlPacket


class ControlDecoder:
    """Decode control packets from demodulated data."""
    
    def __init__(self):
        self.fec = FECDecoder()
        self.parser = PacketParser()
    
    def load_data(self, filename):
        """Load demodulated data from file."""
        try:
            data = np.fromfile(filename, dtype=np.uint8)
            print(f"Loaded {len(data)} bytes from {filename}")
            return data
        except Exception as e:
            print(f"Error loading file: {e}")
            return None
    
    def decode_stream(self, filename):
        """
        Decode control packets from a data stream.
        
        Args:
            filename: Path to demodulated data file
            
        Returns:
            list: List of ControlPacket objects
        """
        
        print("=" * 60)
        print("AFHDS-2A Control Packet Decoder")
        print("=" * 60)
        print()
        
        # Load data
        bits = self.load_data(filename)
        if bits is None:
            return []
        
        # Apply FEC if needed (check if already decoded)
        if len(bits) > 100 and np.all((bits == 0) | (bits == 1)):
            print("Data appears to be raw bits, applying FEC...")
            decoded_bytes = self.fec.decode_bytes(bits)
        else:
            print("Data appears to be already decoded")
            decoded_bytes = bits
        
        print(f"Processing {len(decoded_bytes)} bytes")
        print()
        
        # Find control packets
        print("Searching for control packets...")
        packets = self.parser.find_packets(decoded_bytes)
        
        control_packets = [p for p in packets if isinstance(p, ControlPacket)]
        
        print(f"Found {len(control_packets)} valid control packet(s)")
        print()
        
        # Display packets
        for i, packet in enumerate(control_packets):
            self.display_control_packet(packet, i + 1)
        
        return control_packets
    
    def display_control_packet(self, packet, number=1):
        """Display control packet information in readable format."""
        
        print(f"{'=' * 60}")
        print(f"Control Packet #{number}")
        print(f"{'=' * 60}")
        print(f"TX ID: 0x{packet.tx_id:08X}")
        print(f"CRC Valid: {packet.crc_valid}")
        print()
        
        # Stick positions (first 4 channels)
        sticks = packet.get_stick_positions()
        print("Stick Positions:")
        print("-" * 60)
        
        for name, value in sticks.items():
            if value is not None:
                percent = packet.get_channel_percent(list(sticks.keys()).index(name))
                bar = self._make_bar(value, 1000, 2000)
                print(f"{name.capitalize():<10}: {value:4d} μs  [{bar}] {percent:+6.1f}%")
        
        print()
        
        # All channels
        print("All Channels:")
        print("-" * 60)
        print(f"{'Ch':<4} {'Value (μs)':<12} {'Percent':<10} {'Bar':<20}")
        print("-" * 60)
        
        for i, value in enumerate(packet.channels):
            percent = packet.get_channel_percent(i)
            bar = self._make_bar(value, 1000, 2000)
            print(f"{i:<4} {value:<12} {percent:+6.1f}%    [{bar}]")
        
        print()
    
    def _make_bar(self, value, min_val, max_val, width=15):
        """Create a visual bar for channel value."""
        
        # Normalize to 0-1
        normalized = (value - min_val) / (max_val - min_val)
        normalized = max(0, min(1, normalized))  # Clamp
        
        # Create bar
        filled = int(normalized * width)
        bar = '=' * filled + '-' * (width - filled)
        
        # Add center marker
        center = width // 2
        if filled == center:
            bar = bar[:center] + '|' + bar[center+1:]
        elif filled > center:
            bar = bar[:center] + '|' + bar[center+1:]
        else:
            bar = bar[:filled] + '-' * (center - filled) + '|' + '-' * (width - center - 1)
        
        return bar
    
    def analyze_packets(self, packets):
        """Analyze packet statistics."""
        
        if not packets:
            return
        
        print("=" * 60)
        print("Packet Statistics")
        print("=" * 60)
        print(f"Total packets: {len(packets)}")
        print(f"Valid CRC: {sum(1 for p in packets if p.crc_valid)}")
        print(f"Invalid CRC: {sum(1 for p in packets if not p.crc_valid)}")
        print()
        
        # TX IDs
        tx_ids = set(p.tx_id for p in packets)
        print(f"Unique TX IDs: {len(tx_ids)}")
        for tx_id in tx_ids:
            count = sum(1 for p in packets if p.tx_id == tx_id)
            print(f"  0x{tx_id:08X}: {count} packets")
        print()
        
        # Channel ranges
        if packets and packets[0].channels:
            print("Channel Value Ranges:")
            print("-" * 60)
            
            num_channels = len(packets[0].channels)
            for ch in range(num_channels):
                values = [p.channels[ch] for p in packets if len(p.channels) > ch]
                if values:
                    min_val = min(values)
                    max_val = max(values)
                    avg_val = sum(values) / len(values)
                    print(f"Ch {ch:<2}: min={min_val:4d}  max={max_val:4d}  avg={avg_val:6.1f}")
        
        print()


def main():
    """Main entry point."""
    
    if len(sys.argv) < 2:
        print("Usage: python3 control_decoder.py <demodulated_data_file>")
        print()
        print("Example:")
        print("  python3 control_decoder.py ../captures/control_demod.bin")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    decoder = ControlDecoder()
    packets = decoder.decode_stream(filename)
    
    if packets:
        decoder.analyze_packets(packets)
        print("SUCCESS! Control packets decoded.")
    else:
        print("No control packets found.")
        print()
        print("Troubleshooting:")
        print("  1. Verify TX is transmitting (not in bind mode)")
        print("  2. Check demodulation quality")
        print("  3. Verify FEC decoding is working")
        sys.exit(1)


if __name__ == "__main__":
    main()
