#!/usr/bin/env python3
"""
Phase 1: Spectrum Observer

Simple spectrum analyzer to see FlySky frequency hopping.
Run this first to verify you can see the signal.

Usage:
    python3 01_spectrum_observer.py
    
Then:
    1. Power on FlySky TX
    2. Look for vertical lines in waterfall
    3. Lines should appear every ~3.85ms and hop frequency
"""

from gnuradio import gr, blocks
from gnuradio import qtgui
from gnuradio import fft
import osmosdr
import sys
from PyQt5 import Qt
import signal


class SpectrumObserver(gr.top_block, Qt.QWidget):
    """Spectrum analyzer for AFHDS-2A signals."""
    
    def __init__(self):
        gr.top_block.__init__(self, "AFHDS-2A Spectrum Observer")
        Qt.QWidget.__init__(self)
        
        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 20e6  # 20 MS/s (HackRF max)
        self.center_freq = center_freq = 2.442e9  # 2.442 GHz (center of band)
        self.rf_gain = rf_gain = 32  # LNA gain
        self.if_gain = if_gain = 24  # VGA gain
        
        ##################################################
        # Blocks
        ##################################################
        
        # HackRF Source
        self.osmosdr_source = osmosdr.source(
            args="numchan=1 hackrf=0"
        )
        self.osmosdr_source.set_sample_rate(samp_rate)
        self.osmosdr_source.set_center_freq(center_freq, 0)
        self.osmosdr_source.set_freq_corr(0, 0)
        self.osmosdr_source.set_gain(rf_gain, 0)  # LNA
        self.osmosdr_source.set_if_gain(if_gain, 0)  # VGA
        self.osmosdr_source.set_bb_gain(0, 0)
        self.osmosdr_source.set_antenna('', 0)
        self.osmosdr_source.set_bandwidth(0, 0)
        
        # QT GUI Frequency Sink
        self.qtgui_freq_sink = qtgui.freq_sink_c(
            2048,  # FFT size
            self.get_window(),  # Window function
            center_freq,
            samp_rate,
            "FlySky AFHDS-2A Spectrum",
            1
        )
        self.qtgui_freq_sink.set_update_time(0.05)
        self.qtgui_freq_sink.set_y_axis(-100, 10)
        
        # QT GUI Waterfall Sink
        self.qtgui_waterfall = qtgui.waterfall_sink_c(
            2048,  # FFT size
            self.get_window(),  # Window function
            center_freq,
            samp_rate,
            "FlySky AFHDS-2A Waterfall",
            1
        )
        self.qtgui_waterfall.set_update_time(0.05)
        
        ##################################################
        # Connections
        ##################################################
        self.connect((self.osmosdr_source, 0), (self.qtgui_freq_sink, 0))
        self.connect((self.osmosdr_source, 0), (self.qtgui_waterfall, 0))
        
        ##################################################
        # Setup GUI
        ##################################################
        self.setup_gui()
    
    def get_window(self):
        """Get FFT window function (compatible with GR 3.10)."""
        try:
            # GNU Radio 3.10+ uses fft.window
            return fft.window.WIN_HAMMING
        except AttributeError:
            # Older versions
            try:
                return fft.window.hamming(2048)
            except:
                # Fallback to list (should work everywhere)
                import math
                N = 2048
                return [0.54 - 0.46 * math.cos(2 * math.pi * n / N) for n in range(N)]
    
    def setup_gui(self):
        """Setup Qt GUI layout."""
        self.setWindowTitle("AFHDS-2A Spectrum Observer")
        self.setMinimumSize(800, 600)
        
        layout = Qt.QVBoxLayout()
        
        # Add frequency sink widget
        freq_widget = self.qtgui_freq_sink.qwidget()
        layout.addWidget(freq_widget)
        
        # Add waterfall widget
        waterfall_widget = self.qtgui_waterfall.qwidget()
        layout.addWidget(waterfall_widget)
        
        # Add instructions
        instructions = Qt.QLabel(
            "INSTRUCTIONS:\n"
            "1. Power on FlySky TX (normal mode, not bind)\n"
            "2. Look for bursts in waterfall - they should:\n"
            "   - Appear every ~3.85 ms\n"
            "   - Jump around (frequency hopping)\n"
            "   - Be ~500 kHz wide\n"
            "3. If you see hopping bursts, move to Phase 2!"
        )
        instructions.setStyleSheet("background-color: #ffffcc; padding: 10px;")
        layout.addWidget(instructions)
        
        self.setLayout(layout)
    
    def closeEvent(self, event):
        """Handle window close."""
        self.stop()
        self.wait()
        event.accept()


def main():
    """Main entry point."""
    
    print("=" * 60)
    print("Phase 1: Spectrum Observer")
    print("=" * 60)
    print()
    print("This will show the FlySky signal spectrum.")
    print("You should see frequency hopping bursts.")
    print()
    print("HackRF Settings:")
    print("  Center Frequency: 2.442 GHz")
    print("  Sample Rate: 20 MS/s")
    print("  LNA Gain: 32 dB")
    print("  VGA Gain: 24 dB")
    print()
    print("Close window or press Ctrl+C to exit.")
    print("=" * 60)
    print()
    
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    # Create Qt application
    qapp = Qt.QApplication(sys.argv)
    
    # Create and run flowgraph
    tb = SpectrumObserver()
    tb.start()
    tb.show()
    
    # Run Qt event loop
    sys.exit(qapp.exec_())


if __name__ == '__main__':
    main()
