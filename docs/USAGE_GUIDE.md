# Complete Usage Guide - AFHDS-2A Decoder

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [Phase 1: See the Signal](#phase-1-see-the-signal)
3. [Phase 2: Capture Bind Mode](#phase-2-capture-bind-mode)
4. [Phase 3: Demodulate](#phase-3-demodulate)
5. [Phase 4: Extract Hop Channels](#phase-4-extract-hop-channels)
6. [Understanding the Output](#understanding-the-output)
7. [Next Steps](#next-steps)

---

## Initial Setup

### 1. Run Setup Script

```bash
cd afhds2a_decoder
./setup.sh
```

**What it does:**
- Installs GNU Radio and HackRF tools
- Sets up USB permissions
- Installs Python dependencies
- Creates directory structure

**After setup:** Log out and back in (for USB permissions)

### 2. Test Your System

```bash
python3 test_system.py
```

**Expected output:**
```
✓ PASS: NumPy installed
✓ PASS: GNU Radio 3.x
✓ PASS: HackRF detected (Serial: ...)
✓ PASS: FEC decoder works
✓ PASS: CRC calculator works
...
All tests passed!
```

**If tests fail:** See `docs/TROUBLESHOOTING.md`

### 3. Connect HackRF

```bash
# Verify connection
hackrf_info

# Expected output:
# Serial number: 0x000000...
# Board ID Number: 2 (HackRF One)
# Firmware Version: ...
```

---

## Phase 1: See the Signal

**Goal:** Visually confirm FlySky TX is transmitting

### Steps

```bash
cd gnuradio_flowgraphs
python3 01_spectrum_observer.py
```

### What You'll See

![Spectrum Waterfall]

**Two windows will open:**

1. **Frequency Plot** (top)
   - Shows power vs frequency
   - Should see spikes jumping around

2. **Waterfall** (bottom)
   - Time on vertical axis
   - Frequency on horizontal axis
   - Look for vertical white/yellow lines

### What to Look For

✓ **Success indicators:**
- Vertical lines appearing every ~3-4 milliseconds
- Lines jumping to different frequencies (hopping!)
- Lines are ~500 kHz wide
- Pattern repeats continuously

✗ **Problem indicators:**
- Only noise, no clear signals
- Lines don't hop (stay at one frequency)
- Signal too weak (barely visible)

### Adjustments

If signal is too weak, edit `01_spectrum_observer.py`:

```python
self.rf_gain = 40  # Increase from 32
self.if_gain = 30  # Increase from 24
```

If signal is too strong (saturated):

```python
self.rf_gain = 24  # Decrease
self.if_gain = 16  # Decrease
```

### Moving On

✓ When you can clearly see hopping bursts, proceed to Phase 2

---

## Phase 2: Capture Bind Mode

**Goal:** Record IQ data from bind mode to extract hop table

### Why Bind Mode?

- Uses only 2 fixed frequencies (no hopping)
- Broadcasts the hop table in clear
- Much easier to decode than normal mode

### Steps

#### 1. Put TX in Bind Mode

**FS-i6 / FS-i6S:**
1. Power OFF transmitter
2. Press and HOLD the bind button (on back/side)
3. While holding, power ON transmitter
4. Wait 2 seconds
5. Release bind button
6. **LED should blink RAPIDLY**

**FS-i6X:**
1. Power ON
2. Menu → System → RX Setup → Bind
3. LED should blink rapidly

**Verify:** LED is blinking fast (2-3 times per second)

#### 2. Run Capture

```bash
python3 02_bind_capture.py
```

**Follow prompts:**
```
Is TX in bind mode? (y/n): y
Select frequency (1 or 2, default=1): 1    [Press Enter]
Press Enter to start capture...            [Press Enter]
```

**During capture:**
- Keep TX in bind mode
- Keep HackRF within 1-2 meters
- Wait for 10 seconds
- Don't move antenna

#### 3. Verify Capture

```bash
ls -lh ../captures/bind_capture.iq

# Expected: ~160 MB
# If much smaller: something went wrong
```

### Troubleshooting

**"LED not blinking rapidly"**
- Try different bind procedure (see TX manual)
- Some TXs need receiver nearby
- Factory reset TX and try again

**"Capture file too small"**
- TX wasn't in bind mode
- HackRF disconnected during capture
- Try longer capture (edit script: `duration = 30`)

**"No such file or directory"**
- Run from `gnuradio_flowgraphs/` directory
- Check that `captures/` directory exists

---

## Phase 3: Demodulate

**Goal:** Convert IQ samples to digital bits

### Steps

```bash
python3 03_gfsk_demodulator.py
```

**What it does:**
1. Loads `bind_capture.iq`
2. Applies GFSK demodulation
3. Recovers symbol timing
4. Outputs bits to `bind_demod.bin`

**Expected output:**
```
Demodulation Settings:
  Input: ../captures/bind_capture.iq
  Output: ../captures/bind_demod.bin
  Input size: 160.0 MB
  Symbol rate: 1 Mbps
  
Processing...
(This may take 10-30 seconds)

SUCCESS!
Demodulated bits saved to: ../captures/bind_demod.bin
Output size: 1234567 bytes
```

### Verify Output

```bash
# Look at first few bytes
xxd ../captures/bind_demod.bin | head -20

# Should see patterns, NOT all zeros or all ones
# Look for repeating sequences
```

**Good examples:**
```
00000000: 0101 0101 0101 5475 c52a bb...   # Preamble visible
00000000: aaaa aaaa 5475 c52a bb...        # After FEC
```

**Bad examples:**
```
00000000: 0000 0000 0000 0000 0000...   # All zeros = bad
00000000: ffff ffff ffff ffff ffff...   # All ones = bad
00000000: 7fa3 2e91 84bc 3d77 49ab...   # Completely random = bad
```

### Troubleshooting

If output looks wrong, try adjusting frequency offset:

Edit `03_gfsk_demodulator.py`:

```python
self.freq_xlating_fir = filter.freq_xlating_fir_filter_ccc(
    self.decimation,
    filter.firdes.low_pass(1, self.samp_rate, self.channel_bw, 50e3),
    50000,  # Try: 0, ±50k, ±100k, ±150k
    self.samp_rate
)
```

---

## Phase 4: Extract Hop Channels

**Goal:** Decode bind packet and extract the 16 hop frequencies

### Steps

```bash
cd ../python_decoders
python3 bind_extractor.py ../captures/bind_demod.bin
```

### Expected Output

```
============================================================
AFHDS-2A Bind Packet Extractor
============================================================

Loaded 1234567 bits from ../captures/bind_demod.bin
Bit stream length: 1234567 bits

Applying FEC (7,4) decoding...
Decoded to 701752 bytes
First 32 bytes: aaaaaaaa5475c52abb...

Searching for bind packets...
Found 1 valid bind packet(s)

============================================================
Bind Packet #1
============================================================
TX ID: 0xA3B2C1D0
CRC Valid: True

Hop Channels:
------------------------------------------------------------
Ch   Hex    Decimal  Frequency (MHz)
------------------------------------------------------------
0    0x0D   13       2406.5         
1    0x23   35       2417.5         
2    0x45   69       2434.5         
3    0x67   103      2451.5         
4    0x89   137      2468.5         
5    0xAB   171      2485.5         
6    0xCD   205      2502.5         
7    0xEF   239      2519.5         
8    0x12   18       2409.0         
9    0x34   52       2426.0         
10   0x56   86       2443.0         
11   0x78   120      2460.0         
12   0x9A   154      2477.0         
13   0xBC   188      2494.0         
14   0xDE   222      2511.0         
15   0xF0   240      2520.0         

Hop channels saved to: hop_channels_A3B2C1D0.txt
```

### Success!

✓ You now have:
- TX ID (unique identifier)
- 16 hop channels
- Exact frequencies for each hop

This is saved in `hop_channels_XXXXXXXX.txt` for later use.

### What If It Fails?

**"No bind packets found"**

Most common issue! Try these in order:

1. **Check demod output quality:**
   ```bash
   xxd ../captures/bind_demod.bin | head -50
   # Should see patterns, not random noise
   ```

2. **Run decoder tests:**
   ```bash
   python3 fec_decoder.py    # Should show PASS
   python3 crc.py            # Should show PASS
   ```

3. **Try bit rotation:**
   Bits might be shifted. Edit `bind_extractor.py`:
   ```python
   # After loading bits, add:
   import numpy as np
   bits = np.roll(bits, 1)  # Try 1,2,3,4,5,6,7
   ```

4. **Increase capture duration:**
   Edit `02_bind_capture.py`:
   ```python
   duration = 30  # Instead of 10
   ```
   Then re-capture from Phase 2.

5. **Try other bind frequency:**
   When running `02_bind_capture.py`, select option 2 (2.470 GHz)

6. **Check TX is actually in bind mode:**
   - LED must blink rapidly
   - Not just slow blink
   - Try different bind procedure

---

## Understanding the Output

### TX ID
```
TX ID: 0xA3B2C1D0
```
- Unique identifier for this transmitter
- Used to pair with receiver
- Prevents crosstalk between multiple TXs

### Hop Channels
```
Ch   Hex    Decimal  Frequency (MHz)
0    0x0D   13       2406.5
```

- **Ch:** Channel index (0-15)
- **Hex:** Channel number in hexadecimal
- **Decimal:** Channel number in decimal
- **Frequency:** Actual RF frequency

**Formula:** `Frequency = 2400 + (channel × 0.5) MHz`

### Hop Pattern

TX cycles through all 16 channels in order:
1. Transmit on channel 0 for ~3.85 ms
2. Jump to channel 1, transmit for ~3.85 ms
3. Jump to channel 2, ...
4. After channel 15, back to channel 0
5. Repeat forever

This is why you saw hopping in the waterfall (Phase 1).

---

## Next Steps

### What You've Accomplished

✓ Successfully captured bind mode  
✓ Demodulated GFSK signal  
✓ Decoded FEC (7,4)  
✓ Extracted hop table  
✓ **You can now track the frequency hopping!**

### Immediate Next Steps

1. **Test with control data:**
   ```bash
   # Capture normal TX operation (not bind mode)
   # Use hop channels to track packets
   # Decode stick positions
   ```

2. **Real-time monitoring:**
   - Track hops in real-time
   - Decode control packets live
   - Display stick positions

3. **Data analysis:**
   - Plot stick movements
   - Analyze signal quality
   - Measure packet loss

### Advanced Topics

- **Telemetry decoding:** Receive data from RX back to TX
- **Packet injection:** Transmit control data (be careful!)
- **Multi-TX support:** Track multiple transmitters
- **Signal analysis:** Measure RSSI, SNR, bit errors

---

## File Reference

### Input Files (you create these)

```
captures/bind_capture.iq        # Raw IQ from HackRF (Phase 2)
captures/bind_demod.bin         # Demodulated bits (Phase 3)
```

### Output Files (scripts create these)

```
hop_channels_XXXXXXXX.txt       # Extracted hop table (Phase 4)
```

### Scripts You Run

```
gnuradio_flowgraphs/
├── 01_spectrum_observer.py     # Phase 1
├── 02_bind_capture.py          # Phase 2
└── 03_gfsk_demodulator.py      # Phase 3

python_decoders/
└── bind_extractor.py           # Phase 4
```

---

## Tips for Success

1. **Start simple:** Follow phases in order
2. **Verify each step:** Don't skip verification
3. **Keep TX close:** 0.5-1m distance initially
4. **Use fresh batteries:** Weak TX signal causes problems
5. **Bind mode is key:** Make sure LED blinks fast
6. **Be patient:** Debugging is normal
7. **Take notes:** Record what works for your setup

---

## Common Gotchas

❌ **Not putting TX in bind mode properly**
→ LED must blink rapidly (2-3/sec)

❌ **HackRF too far from TX**
→ Start within 1 meter

❌ **Not logging out/in after setup**
→ USB permissions require logout

❌ **Using USB 3.0 port**
→ Prefer USB 2.0 to avoid noise

❌ **Expecting 100% success rate**
→ 60-80% packet capture is good!

❌ **Skipping verification steps**
→ Always check file sizes, run tests

---

## Getting Help

**Before asking:**
1. Run `test_system.py` and share results
2. Check `docs/TROUBLESHOOTING.md`
3. Verify file sizes are correct
4. Include actual error messages

**Where to ask:**
- GitHub Issues (code problems)
- r/GNURadio (flowgraph help)
- r/RTLSDR (hardware issues)

**What to provide:**
- Operating system version
- GNU Radio version
- HackRF serial number
- File sizes from `captures/`
- Complete error output
- What you've tried

---

## Success Metrics

After completing all phases:

- [ ] Can see hopping in waterfall (Phase 1)
- [ ] Captured ~160 MB bind file (Phase 2)
- [ ] Demod file has patterns (Phase 3)
- [ ] Extracted 16 hop channels (Phase 4)
- [ ] CRC validation passes
- [ ] All tests in `test_system.py` pass

**If all checked:** You've successfully decoded AFHDS-2A! 🎉

---

**Ready to start?** → Run `./setup.sh`
