#!/usr/bin/env python3
"""
Real-Time Control Monitor (ADVANCED)

Monitors FlySky control data in real-time by tracking frequency hops.

Prerequisites:
- Hop channels extracted from bind packet
- HackRF One connected

Usage:
    python3 realtime_monitor.py hop_channels_XXXXXXXX.txt

Note: This is advanced - HackRF retune latency means 60-80% packet capture.
"""

import sys
import os
import time
import threading
import queue
from gnuradio import gr, blocks, filter, analog, digital
import osmosdr
import numpy as np

# Import local decoders
try:
    from fec_decoder import FECDecoder
    from packet_parser import PacketParser, ControlPacket
except ImportError:
    print("Error: Run from python_decoders/ directory")
    sys.exit(1)


class HopTracker(gr.top_block):
    """Real-time frequency hopping tracker."""
    
    def __init__(self, hop_channels, output_queue):
        gr.top_block.__init__(self, "AFHDS-2A Hop Tracker")
        
        self.hop_channels = hop_channels
        self.output_queue = output_queue
        self.current_hop = 0
        
        # RF parameters
        self.samp_rate = 20e6
        self.symbol_rate = 1e6
        self.decimation = 40
        self.sps = (self.samp_rate / self.decimation) / self.symbol_rate
        
        # Build initial flowgraph
        self.build_flowgraph()
        
        # Start hop timer
        self.hop_timer = None
        self.hop_interval = 0.00385  # 3.85 ms
    
    def build_flowgraph(self):
        """Build GNU Radio flowgraph."""
        
        # HackRF Source
        self.osmosdr_source = osmosdr.source(args="numchan=1 hackrf=0")
        self.osmosdr_source.set_sample_rate(self.samp_rate)
        self.osmosdr_source.set_center_freq(self.get_current_freq(), 0)
        self.osmosdr_source.set_freq_corr(0, 0)
        self.osmosdr_source.set_gain(40, 0)
        self.osmosdr_source.set_if_gain(30, 0)
        
        # Demodulation chain (same as offline)
        self.freq_xlating_fir = filter.freq_xlating_fir_filter_ccc(
            self.decimation,
            filter.firdes.low_pass(1, self.samp_rate, 250e3, 50e3),
            0,
            self.samp_rate
        )
        
        self.quadrature_demod = analog.quadrature_demod_cf(
            (self.samp_rate / self.decimation) / (2 * 3.14159 * 250e3)
        )
        
        self.low_pass_filter = filter.fir_filter_fff(
            1,
            filter.firdes.low_pass(1, self.samp_rate / self.decimation, 500e3, 100e3)
        )
        
        self.clock_recovery = digital.clock_recovery_mm_ff(
            self.sps,
            0.25 * 0.25,
            0.5,
            0.05,
            0.005
        )
        
        self.binary_slicer = digital.binary_slicer_fb()
        
        # Vector sink to collect bits
        self.vector_sink = blocks.vector_sink_b()
        
        # Connect blocks
        self.connect((self.osmosdr_source, 0), (self.freq_xlating_fir, 0))
        self.connect((self.freq_xlating_fir, 0), (self.quadrature_demod, 0))
        self.connect((self.quadrature_demod, 0), (self.low_pass_filter, 0))
        self.connect((self.low_pass_filter, 0), (self.clock_recovery, 0))
        self.connect((self.clock_recovery, 0), (self.binary_slicer, 0))
        self.connect((self.binary_slicer, 0), (self.vector_sink, 0))
    
    def get_current_freq(self):
        """Get current hop frequency."""
        channel = self.hop_channels[self.current_hop]
        return 2400e6 + (channel * 0.5e6)
    
    def next_hop(self):
        """Move to next hop channel."""
        self.current_hop = (self.current_hop + 1) % len(self.hop_channels)
        
        # Retune HackRF
        freq = self.get_current_freq()
        self.osmosdr_source.set_center_freq(freq, 0)
        
        # Collect bits from vector sink
        bits = self.vector_sink.data()
        if len(bits) > 100:  # Enough for a packet
            self.output_queue.put(np.array(bits, dtype=np.uint8))
        
        # Clear vector sink
        self.vector_sink.reset()
    
    def start_hopping(self):
        """Start hop timer."""
        self.hop_timer = threading.Timer(self.hop_interval, self.hop_callback)
        self.hop_timer.daemon = True
        self.hop_timer.start()
    
    def hop_callback(self):
        """Timer callback to hop."""
        self.next_hop()
        self.start_hopping()  # Schedule next hop
    
    def stop_hopping(self):
        """Stop hop timer."""
        if self.hop_timer:
            self.hop_timer.cancel()


class ControlMonitor:
    """Monitor and decode control packets."""
    
    def __init__(self, hop_channels):
        self.hop_channels = hop_channels
        self.fec = FECDecoder()
        self.parser = PacketParser()
        
        self.packet_count = 0
        self.valid_count = 0
        self.last_packet = None
    
    def process_bits(self, bits):
        """Process received bits."""
        
        # Apply FEC decoding
        decoded = self.fec.decode_bytes(bits)
        
        if len(decoded) < 35:  # Not enough for control packet
            return
        
        # Try to parse packet
        packet = self.parser.parse(decoded)
        
        if packet and isinstance(packet, ControlPacket):
            self.packet_count += 1
            
            if packet.verify_crc():
                self.valid_count += 1
                self.last_packet = packet
                self.display_packet(packet)
    
    def display_packet(self, packet):
        """Display control packet data."""
        
        # Clear screen (optional)
        # print("\033[2J\033[H")
        
        print(f"\r[{self.valid_count}/{self.packet_count}] ", end='')
        
        # Display stick positions
        sticks = packet.get_stick_positions()
        
        for name, value in sticks.items():
            if value:
                bar = self.make_bar(value, 1000, 2000, width=10)
                print(f"{name[:3].upper()}:{value:4d}[{bar}] ", end='')
        
        sys.stdout.flush()
    
    def make_bar(self, value, min_val, max_val, width=10):
        """Create ASCII bar."""
        normalized = (value - min_val) / (max_val - min_val)
        normalized = max(0, min(1, normalized))
        filled = int(normalized * width)
        return '=' * filled + '-' * (width - filled)
    
    def print_stats(self):
        """Print statistics."""
        if self.packet_count > 0:
            rate = (self.valid_count / self.packet_count) * 100
            print(f"\n\nStatistics:")
            print(f"  Total packets: {self.packet_count}")
            print(f"  Valid packets: {self.valid_count}")
            print(f"  Success rate: {rate:.1f}%")


def load_hop_channels(filename):
    """Load hop channels from file."""
    
    hop_channels = []
    
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Parse HOP_CHANNELS_HEX line
                if line.startswith('HOP_CHANNELS_HEX='):
                    hex_str = line.split('=')[1]
                    channels_hex = hex_str.split(',')
                    
                    for ch_hex in channels_hex:
                        ch_hex = ch_hex.strip()
                        if ch_hex.startswith('0x'):
                            hop_channels.append(int(ch_hex, 16))
                    
                    break
        
        if not hop_channels:
            print("Error: No hop channels found in file")
            return None
        
        if len(hop_channels) != 16:
            print(f"Warning: Expected 16 channels, got {len(hop_channels)}")
        
        return hop_channels
    
    except Exception as e:
        print(f"Error loading hop channels: {e}")
        return None


def main():
    """Main entry point."""
    
    print("=" * 60)
    print("AFHDS-2A Real-Time Control Monitor (ADVANCED)")
    print("=" * 60)
    print()
    
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python3 realtime_monitor.py <hop_channels_file>")
        print()
        print("Example:")
        print("  python3 realtime_monitor.py hop_channels_A3B2C1D0.txt")
        print()
        print("Note: You must extract hop channels first with bind_extractor.py")
        sys.exit(1)
    
    hop_file = sys.argv[1]
    
    # Check file exists
    if not os.path.exists(hop_file):
        print(f"Error: File not found: {hop_file}")
        sys.exit(1)
    
    # Load hop channels
    print(f"Loading hop channels from: {hop_file}")
    hop_channels = load_hop_channels(hop_file)
    
    if not hop_channels:
        sys.exit(1)
    
    print(f"Loaded {len(hop_channels)} hop channels")
    print(f"Frequencies: {[2400 + ch*0.5 for ch in hop_channels[:4]]}... MHz")
    print()
    
    print("WARNING: Real-time hop tracking is DIFFICULT with HackRF!")
    print("  - Retune latency: ~1-2 ms")
    print("  - Hop interval: 3.85 ms")
    print("  - Expected success: 60-80% of packets")
    print()
    print("This is a DEMONSTRATION of the concept.")
    print("For production use, consider hardware with faster retune.")
    print()
    
    input("Press Enter to start monitoring...")
    print()
    
    print("Monitoring control data...")
    print("(Press Ctrl+C to stop)")
    print()
    
    # Create queue for data passing
    data_queue = queue.Queue()
    
    # Create monitor
    monitor = ControlMonitor(hop_channels)
    
    # Create and start flowgraph
    tracker = HopTracker(hop_channels, data_queue)
    
    try:
        tracker.start()
        tracker.start_hopping()
        
        # Main loop
        while True:
            try:
                # Get bits from queue (with timeout)
                bits = data_queue.get(timeout=0.1)
                monitor.process_bits(bits)
            except queue.Empty:
                continue
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
        tracker.stop_hopping()
        tracker.stop()
        tracker.wait()
        
        monitor.print_stats()
        
        print("\nDone!")
    
    except Exception as e:
        print(f"\nError: {e}")
        tracker.stop_hopping()
        tracker.stop()
        tracker.wait()
        sys.exit(1)


if __name__ == '__main__':
    main()
