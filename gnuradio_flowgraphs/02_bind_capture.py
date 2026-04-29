#!/usr/bin/env python3
"""
Phase 2: Bind Mode Capture

Captures IQ data from FlySky TX in bind mode.
Bind mode uses fixed frequencies, making it easier to capture.

Usage:
    1. Put TX in bind mode (hold bind button, power on)
    2. Run: python3 02_bind_capture.py
    3. Wait for 10 seconds
    4. Output: ../captures/bind_capture.iq

Bind frequencies:
    - 2.406 GHz (channel 0x0D)
    - 2.470 GHz (channel 0x8C)
"""

import osmosdr
from gnuradio import gr, blocks
import time
import sys


class BindCapture(gr.top_block):
    """Capture bind mode IQ data."""
    
    def __init__(self, output_file, duration=10, bind_freq=2.406e9):
        gr.top_block.__init__(self, "AFHDS-2A Bind Capture")
        
        ##################################################
        # Variables
        ##################################################
        self.samp_rate = 20e6  # 20 MS/s
        self.center_freq = bind_freq
        self.rf_gain = 40  # Higher gain for bind mode
        self.if_gain = 30
        self.duration = duration
        
        ##################################################
        # Blocks
        ##################################################
        
        # HackRF Source
        self.osmosdr_source = osmosdr.source(args="numchan=1 hackrf=0")
        self.osmosdr_source.set_sample_rate(self.samp_rate)
        self.osmosdr_source.set_center_freq(self.center_freq, 0)
        self.osmosdr_source.set_freq_corr(0, 0)
        self.osmosdr_source.set_gain(self.rf_gain, 0)
        self.osmosdr_source.set_if_gain(self.if_gain, 0)
        self.osmosdr_source.set_bb_gain(0, 0)
        self.osmosdr_source.set_antenna('', 0)
        self.osmosdr_source.set_bandwidth(0, 0)
        
        # Head block to limit capture duration
        num_samples = int(self.samp_rate * self.duration)
        self.blocks_head = blocks.head(gr.sizeof_gr_complex, num_samples)
        
        # File Sink
        self.blocks_file_sink = blocks.file_sink(
            gr.sizeof_gr_complex,
            output_file,
            False  # Don't append
        )
        self.blocks_file_sink.set_unbuffered(False)
        
        ##################################################
        # Connections
        ##################################################
        self.connect((self.osmosdr_source, 0), (self.blocks_head, 0))
        self.connect((self.blocks_head, 0), (self.blocks_file_sink, 0))


def main():
    """Main entry point."""
    
    print("=" * 60)
    print("Phase 2: Bind Mode Capture")
    print("=" * 60)
    print()
    print("BEFORE RUNNING:")
    print("  1. Put FlySky TX in BIND MODE")
    print("     - Hold bind button")
    print("     - Power on TX")
    print("     - LED should blink rapidly")
    print("  2. TX should be within 1-2 meters of HackRF")
    print()
    
    # Get user confirmation
    response = input("Is TX in bind mode? (y/n): ")
    if response.lower() != 'y':
        print("Put TX in bind mode first, then run again.")
        sys.exit(0)
    
    # Select bind frequency
    print()
    print("Bind frequencies:")
    print("  1. 2.406 GHz (channel 0x0D) - DEFAULT")
    print("  2. 2.470 GHz (channel 0x8C)")
    
    freq_choice = input("Select frequency (1 or 2, default=1): ").strip()
    
    if freq_choice == '2':
        bind_freq = 2.470e9
        freq_name = "2.470 GHz"
    else:
        bind_freq = 2.406e9
        freq_name = "2.406 GHz"
    
    # Set output file
    output_file = "../captures/bind_capture.iq"
    duration = 10  # seconds
    
    print()
    print("Capture Settings:")
    print(f"  Frequency: {freq_name}")
    print(f"  Sample Rate: 20 MS/s")
    print(f"  Duration: {duration} seconds")
    print(f"  Output: {output_file}")
    print()
    print(f"File size will be ~{int(20e6 * 8 * duration / 1024 / 1024)} MB")
    print()
    
    input("Press Enter to start capture...")
    
    print()
    print("Starting capture...")
    
    # Create and run flowgraph
    tb = BindCapture(output_file, duration, bind_freq)
    
    try:
        tb.start()
        
        # Show progress
        for i in range(duration):
            print(f"  Capturing... {i+1}/{duration} seconds", end='\r')
            time.sleep(1)
        
        print()
        print("Waiting for flowgraph to finish...")
        tb.wait()
        
        print()
        print("=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"Bind mode IQ data saved to: {output_file}")
        print()
        print("Next step:")
        print("  Run Phase 3 to demodulate this capture:")
        print("  python3 03_gfsk_demodulator.py")
        print()
        
    except KeyboardInterrupt:
        print()
        print("Capture interrupted!")
        tb.stop()
        tb.wait()
    
    except Exception as e:
        print(f"Error: {e}")
        tb.stop()
        tb.wait()
        sys.exit(1)


if __name__ == '__main__':
    main()
