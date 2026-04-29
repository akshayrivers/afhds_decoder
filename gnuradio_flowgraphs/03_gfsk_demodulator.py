#!/usr/bin/env python3
"""
Phase 3: GFSK Demodulator

Demodulates captured IQ data to bits.
This processes the bind_capture.iq file from Phase 2.

Usage:
    python3 03_gfsk_demodulator.py [input_file] [output_file]
    
Example:
    python3 03_gfsk_demodulator.py ../captures/bind_capture.iq ../captures/bind_demod.bin

Output:
    - Demodulated bits saved as binary file
    - Ready for bind_extractor.py
"""

from gnuradio import gr, blocks, filter, analog, digital
import osmosdr
import sys
import os


class GFSKDemodulator(gr.top_block):
    """GFSK demodulator for AFHDS-2A."""
    
    def __init__(self, input_file, output_file):
        gr.top_block.__init__(self, "AFHDS-2A GFSK Demodulator")
        
        ##################################################
        # Variables
        ##################################################
        self.samp_rate = 20e6  # Input sample rate
        self.symbol_rate = 1e6  # 1 Mbps
        self.decimation = 40  # Reduce to 500 kS/s
        self.channel_bw = 250e3  # 250 kHz channel bandwidth
        
        # Calculate samples per symbol after decimation
        self.sps = (self.samp_rate / self.decimation) / self.symbol_rate
        
        ##################################################
        # Blocks
        ##################################################
        
        # File Source (IQ from Phase 2)
        self.blocks_file_source = blocks.file_source(
            gr.sizeof_gr_complex,
            input_file,
            False  # Don't repeat
        )
        
        # Frequency Xlating FIR Filter
        # Decimates and allows frequency offset correction
        self.freq_xlating_fir = filter.freq_xlating_fir_filter_ccc(
            self.decimation,
            filter.firdes.low_pass(1, self.samp_rate, self.channel_bw, 50e3),
            0,  # Frequency offset (adjust if needed)
            self.samp_rate
        )
        
        # Quadrature Demod (FM demodulation for GFSK)
        # Gain adjusted for GFSK deviation
        self.quadrature_demod = analog.quadrature_demod_cf(
            (self.samp_rate / self.decimation) / (2 * 3.14159 * 250e3)
        )
        
        # Low Pass Filter (clean up demod output)
        self.low_pass_filter = filter.fir_filter_fff(
            1,
            filter.firdes.low_pass(1, self.samp_rate / self.decimation, 500e3, 100e3)
        )
        
        # Clock Recovery (Mueller & Müller)
        # Synchronize to symbol timing
        self.clock_recovery = digital.clock_recovery_mm_ff(
            self.sps,  # Omega (samples per symbol)
            0.25 * 0.25,  # Gain omega
            0.5,  # Mu
            0.05,  # Gain mu
            0.005  # Omega relative limit
        )
        
        # Binary Slicer (convert to 0s and 1s)
        self.binary_slicer = digital.binary_slicer_fb()
        
        # Char to Float (for visualization if needed)
        self.char_to_float = blocks.char_to_float(1, 1)
        
        # File Sink (output bits)
        self.blocks_file_sink = blocks.file_sink(
            gr.sizeof_char,
            output_file,
            False
        )
        self.blocks_file_sink.set_unbuffered(False)
        
        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_file_source, 0), (self.freq_xlating_fir, 0))
        self.connect((self.freq_xlating_fir, 0), (self.quadrature_demod, 0))
        self.connect((self.quadrature_demod, 0), (self.low_pass_filter, 0))
        self.connect((self.low_pass_filter, 0), (self.clock_recovery, 0))
        self.connect((self.clock_recovery, 0), (self.binary_slicer, 0))
        self.connect((self.binary_slicer, 0), (self.blocks_file_sink, 0))


def main():
    """Main entry point."""
    
    print("=" * 60)
    print("Phase 3: GFSK Demodulator")
    print("=" * 60)
    print()
    
    # Parse arguments
    if len(sys.argv) >= 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    else:
        input_file = "../captures/bind_capture.iq"
        output_file = "../captures/bind_demod.bin"
    
    # Check input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        print()
        print("Usage:")
        print("  python3 03_gfsk_demodulator.py [input_file] [output_file]")
        print()
        print("Example:")
        print("  python3 03_gfsk_demodulator.py ../captures/bind_capture.iq ../captures/bind_demod.bin")
        sys.exit(1)
    
    # Get file size
    file_size_mb = os.path.getsize(input_file) / 1024 / 1024
    
    print("Demodulation Settings:")
    print(f"  Input: {input_file}")
    print(f"  Output: {output_file}")
    print(f"  Input size: {file_size_mb:.1f} MB")
    print(f"  Symbol rate: 1 Mbps")
    print(f"  Decimation: 40x (20 MS/s → 500 kS/s)")
    print()
    
    print("Processing...")
    print("(This may take 10-30 seconds)")
    print()
    
    # Create and run flowgraph
    tb = GFSKDemodulator(input_file, output_file)
    
    try:
        tb.start()
        tb.wait()
        
        # Check output
        if os.path.exists(output_file):
            output_size = os.path.getsize(output_file)
            print()
            print("=" * 60)
            print("SUCCESS!")
            print("=" * 60)
            print(f"Demodulated bits saved to: {output_file}")
            print(f"Output size: {output_size} bytes ({output_size} bits)")
            print()
            print("Next step:")
            print("  Extract bind packet with:")
            print(f"  python3 ../python_decoders/bind_extractor.py {output_file}")
            print()
        else:
            print("Error: Output file was not created!")
            sys.exit(1)
    
    except Exception as e:
        print(f"Error during demodulation: {e}")
        tb.stop()
        tb.wait()
        sys.exit(1)


if __name__ == '__main__':
    main()
