# Troubleshooting Guide

Common problems and solutions for AFHDS-2A decoding.

---

## Installation Issues

### "hackrf_info shows nothing"

**Symptoms:** `hackrf_info` returns no output or error

**Solutions:**

1. Check USB connection:
   ```bash
   lsusb | grep HackRF
   # Should show: "Great Scott Gadgets HackRF One"
   ```

2. Fix permissions:
   ```bash
   sudo usermod -a -G plugdev $USER
   # Log out and back in
   ```

3. Reinstall udev rules:
   ```bash
   sudo apt install --reinstall hackrf
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

4. Try different USB port (prefer USB 2.0, not 3.0)

5. Power issue - some HackRFs need external power:
   ```bash
   # Check if it's detected at all
   lsusb -v | grep -i hackrf
   ```

---

### "ModuleNotFoundError: No module named 'osmosdr'"

**Symptoms:** Python can't import GNU Radio modules

**Solutions:**

1. Check GNU Radio installation:
   ```bash
   gnuradio-config-info --version
   python3 -c "from gnuradio import gr; print(gr.version())"
   ```

2. Install gr-osmosdr:
   ```bash
   sudo apt install gr-osmosdr
   ```

3. Check Python path:
   ```bash
   python3 -c "import sys; print('\n'.join(sys.path))"
   # Should include GNU Radio paths
   ```

4. Try with python3 explicitly:
   ```bash
   python3 script.py  # Not just: python script.py
   ```

---

## Signal Acquisition Issues

### "No signal visible in waterfall"

**Symptoms:** Waterfall shows only noise, no frequency hops

**Solutions:**

1. **Increase gain:**
   Edit `01_spectrum_observer.py`:
   ```python
   self.rf_gain = 40  # Was 32
   self.if_gain = 30  # Was 24
   ```

2. **Check TX is transmitting:**
   - Power LED on?
   - Not in bind mode?
   - Battery charged?

3. **Try different antenna:**
   - Use 2.4 GHz antenna (not the tiny one)
   - Point antenna at TX
   - Remove obstacles

4. **Move closer:**
   - Start with HackRF 0.5-1m from TX
   - Too close can also cause issues (saturation)

5. **Check frequency:**
   ```python
   # Try different center freq
   self.center_freq = 2.420e9  # or 2.450e9, 2.460e9
   ```

6. **Verify with known signal:**
   ```bash
   # Try capturing WiFi (should show signals)
   self.center_freq = 2.437e9  # WiFi channel 6
   ```

---

### "Signal visible but no clear bursts"

**Symptoms:** Waterfall shows activity but not distinct hops

**Solutions:**

1. **Reduce gain** (might be saturated):
   ```python
   self.rf_gain = 24
   self.if_gain = 16
   ```

2. **Adjust FFT size:**
   ```python
   # Larger = more frequency resolution
   self.qtgui_waterfall = qtgui.waterfall_sink_c(
       4096,  # Was 2048
   ```

3. **Check update rate:**
   ```python
   self.qtgui_waterfall.set_update_time(0.01)  # Faster updates
   ```

---

## Bind Mode Issues

### "TX won't enter bind mode"

**Symptoms:** LED doesn't blink rapidly

**Solutions:**

1. **Correct procedure:**
   - Power OFF TX completely
   - Press AND HOLD bind button
   - Power ON TX (while still holding)
   - Wait 2 seconds
   - Release bind button
   - LED should blink rapidly

2. **Check TX model:**
   - Some TXs: different button
   - FS-i6: Bind button on back
   - FS-i6S: Bind switch on side
   - FS-i6X: Menu-based bind

3. **Receiver might be needed:**
   - Some TXs require RX to be nearby
   - Try with receiver powered on

4. **Reset TX:**
   - Full factory reset
   - Try bind procedure again

---

### "Bind capture file is too small"

**Symptoms:** `bind_capture.iq` is < 50 MB

**Solutions:**

1. **Capture wasn't long enough:**
   Edit `02_bind_capture.py`:
   ```python
   duration = 30  # Was 10 seconds
   ```

2. **HackRF disconnected during capture:**
   - Check USB connection
   - Check `dmesg | tail` for errors

3. **Disk full:**
   ```bash
   df -h
   # Need at least 200 MB free
   ```

---

## Demodulation Issues

### "Demodulated bits look random"

**Symptoms:** `bind_demod.bin` has no patterns

**Check:**
```bash
xxd bind_demod.bin | head -50
# Should see some repeating patterns
# If all random: demod failed
```

**Solutions:**

1. **Frequency offset too large:**
   Edit `03_gfsk_demodulator.py`:
   ```python
   # Try different offset values
   self.freq_xlating_fir = filter.freq_xlating_fir_filter_ccc(
       self.decimation,
       filter.firdes.low_pass(1, self.samp_rate, self.channel_bw, 50e3),
       50e3,  # Try: 0, 50e3, -50e3, 100e3, -100e3
       self.samp_rate
   )
   ```

2. **Wrong sample rate:**
   - Verify capture was at 20 MS/s
   - Check `bind_capture.iq` file size:
     - 10 sec @ 20 MS/s = ~160 MB
     - If different size, sample rate was wrong

3. **Clock recovery issues:**
   ```python
   # Adjust samples per symbol
   self.sps = 0.5  # Try 0.4, 0.5, 0.6
   ```

4. **Try manual demod:**
   ```bash
   # Use GNU Radio Companion GUI
   gnuradio-companion
   # Build flowgraph visually
   # Add QT GUI sinks to debug each stage
   ```

---

### "Demod output is all zeros or all ones"

**Symptoms:** Binary slicer stuck

**Solutions:**

1. **Gain too high/low before slicer:**
   ```python
   # Adjust quadrature demod gain
   self.quadrature_demod = analog.quadrature_demod_cf(
       0.5  # Try different values: 0.3, 0.5, 1.0, 2.0
   )
   ```

2. **DC offset:**
   Add DC blocker before slicer:
   ```python
   self.dc_blocker = filter.dc_blocker_ff(32, True)
   # Insert in chain before binary_slicer
   ```

---

## Packet Extraction Issues

### "No bind packets found"

**Most common problem!**

**Diagnostic steps:**

1. **Check file size:**
   ```bash
   ls -lh captures/bind_demod.bin
   # Should be > 1 MB
   ```

2. **Look for patterns manually:**
   ```bash
   xxd captures/bind_demod.bin | grep "aa aa aa"
   # Preamble should appear
   ```

3. **Check FEC decoder:**
   ```bash
   cd python_decoders
   python3 fec_decoder.py
   # All tests should PASS
   ```

4. **Try without FEC first:**
   Edit `bind_extractor.py`:
   ```python
   # Comment out FEC line temporarily
   # decoded_bytes = self.fec.decode_bytes(bits)
   decoded_bytes = bits  # Try raw bits
   ```

5. **Bit alignment issue:**
   - Bits might be shifted by 1-7 positions
   - Try rotating:
   ```python
   # In bind_extractor.py, after loading bits:
   bits = np.roll(bits, 1)  # Try 1,2,3,4,5,6,7
   ```

6. **Check for sync word:**
   ```python
   # Search for known patterns
   import numpy as np
   bits = np.fromfile('bind_demod.bin', dtype=np.uint8)
   
   # Look for preamble (01010101 pattern)
   for i in range(len(bits)-32):
       if all(bits[i+j] == j%2 for j in range(32)):
           print(f"Preamble at bit {i}")
   ```

---

### "CRC never passes"

**Symptoms:** Packets found but `crc_valid=False`

**Solutions:**

1. **Byte alignment wrong:**
   ```python
   # FEC might be producing wrong byte boundaries
   # Check nibble ordering in FEC decoder
   ```

2. **Endianness issue:**
   - CRC bytes might be swapped
   - Check packet_parser.py CRC verification

3. **Wrong CRC polynomial:**
   Verify in `crc.py`:
   ```python
   polynomial = 0x1021  # Should be this for CCITT
   ```

4. **Data corruption:**
   - Weak signal during capture
   - Re-capture with higher gain

---

## HackRF Hardware Issues

### "USB timeouts or disconnects"

**Symptoms:** HackRF stops mid-capture

**Solutions:**

1. **Use USB 2.0 port:**
   ```bash
   lsusb -t
   # Look for USB 2.0 hub, not 3.0
   ```

2. **Reduce sample rate:**
   ```python
   self.samp_rate = 10e6  # Instead of 20e6
   # Adjust other parameters accordingly
   ```

3. **Power issue:**
   - Use powered USB hub
   - Some HackRFs need external 5V

4. **Firmware update:**
   ```bash
   hackrf_spiflash -w hackrf_one_usb.bin
   # Get firmware from GitHub
   ```

---

### "Gain settings don't work"

**Symptoms:** Changing gain has no effect

**Solutions:**

1. **Check valid range:**
   ```python
   # LNA: 0-40 dB (8 dB steps)
   # VGA: 0-62 dB (2 dB steps)
   ```

2. **Set explicitly:**
   ```python
   self.osmosdr_source.set_gain_mode(False, 0)  # Manual gain
   self.osmosdr_source.set_gain(32, 0)
   ```

3. **Try different gain APIs:**
   ```python
   # Some versions use different names
   self.osmosdr_source.set_gain('LNA', 32, 0)
   self.osmosdr_source.set_gain('VGA', 24, 0)
   ```

---

## Python Decoder Issues

### "Import errors in python_decoders"

**Symptoms:** Can't import FECDecoder, etc.

**Solutions:**

1. **Run from correct directory:**
   ```bash
   cd python_decoders
   python3 bind_extractor.py ../captures/bind_demod.bin
   ```

2. **Add to Python path:**
   ```bash
   export PYTHONPATH="${PYTHONPATH}:/path/to/afhds2a_decoder"
   ```

3. **Use relative imports:**
   - Already set up in scripts
   - Should work from project root

---

### "FEC decoder gives wrong output"

**Symptoms:** Decoded bytes don't make sense

**Solutions:**

1. **Verify FEC table:**
   ```bash
   python3 fec_decoder.py
   # Check all tests pass
   ```

2. **Check bit order:**
   - LSB first vs MSB first
   - Might need to reverse bits

3. **Compare with reference:**
   - Use captures from DIY-Multiprotocol project
   - Compare output

---

## Performance Issues

### "Demodulation is very slow"

**Solutions:**

1. **Reduce file size for testing:**
   ```bash
   # Use first 10 seconds only
   head -c 160000000 bind_capture.iq > test.iq
   ```

2. **Use fast PC:**
   - Demod is CPU intensive
   - Multi-core helps

3. **Profile bottleneck:**
   ```bash
   python3 -m cProfile 03_gfsk_demodulator.py
   ```

---

## Getting More Help

### Before asking for help, provide:

1. **System info:**
   ```bash
   uname -a
   hackrf_info
   gnuradio-config-info --version
   python3 --version
   ```

2. **File sizes:**
   ```bash
   ls -lh captures/
   ```

3. **Error messages:**
   ```bash
   # Copy full error text
   ```

4. **What you tried:**
   - List troubleshooting steps attempted

### Where to ask:

- **GitHub Issues:** Best for code bugs
- **r/GNURadio:** Best for flowgraph help
- **r/RTLSDR:** Best for hardware issues
- **Discord/IRC:** Best for real-time help

---

## Debug Mode

Enable verbose output:

```python
# Add to any script
import logging
logging.basicConfig(level=logging.DEBUG)
```

```bash
# Run with debug
python3 -u script.py 2>&1 | tee debug.log
```

---

## Common Error Messages

### "RuntimeError: std::exception"
- Usually: GNU Radio block connection error
- Check flowgraph connections
- Verify block parameters

### "OverflowError"
- HackRF can't keep up
- Reduce sample rate or add throttle

### "Fatal Python error: deallocating None"
- GNU Radio version mismatch
- Reinstall GNU Radio

### "Segmentation fault"
- Corrupted installation
- Reinstall gr-osmosdr

---

## Last Resort

If nothing works:

1. **Start over with clean install:**
   ```bash
   sudo apt purge gnuradio hackrf
   sudo apt autoremove
   sudo apt install gnuradio hackrf gr-osmosdr
   ```

2. **Try on different PC**
   - VM might have USB issues
   - Try native Linux install

3. **Test with RTL-SDR instead**
   - Cheaper, easier for testing
   - Same protocol

4. **Use Logic Analyzer**
   - If you have FlySky module
   - Capture SPI between MCU and RF chip
   - Easier to decode

Remember: Most problems are gain/frequency offset! Start there.
