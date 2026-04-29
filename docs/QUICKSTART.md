# AFHDS-2A Decoder - Quick Start Guide

Get from zero to decoding in 30 minutes.

## Prerequisites Check

```bash
# Test HackRF
hackrf_info

# Test GNU Radio
python3 -c "import gnuradio; print('OK')"

# Test Python packages
python3 -c "import numpy, scipy; print('OK')"
```

If any fail, run `./setup.sh` first.

## 30-Minute Workflow

### Minute 0-5: See the Signal

```bash
cd gnuradio_flowgraphs
python3 01_spectrum_observer.py
```

**What to do:**
1. Power on FlySky TX (normal mode, not bind)
2. Look at waterfall display
3. You should see vertical lines hopping around

**Success criteria:** You see bursts every ~4ms jumping frequency

---

### Minute 5-10: Capture Bind Mode

```bash
python3 02_bind_capture.py
```

**What to do:**
1. Power OFF your TX
2. Hold bind button
3. Power ON TX (while holding bind)
4. LED should blink rapidly
5. Run the script and follow prompts
6. Select default frequency (option 1)
7. Wait 10 seconds

**Success criteria:** File created: `../captures/bind_capture.iq` (~160 MB)

---

### Minute 10-15: Demodulate

```bash
python3 03_gfsk_demodulator.py
```

**What to do:**
1. Just run it (uses default files)
2. Wait ~30 seconds

**Success criteria:** File created: `../captures/bind_demod.bin`

---

### Minute 15-20: Extract Hop Channels

```bash
cd ../python_decoders
python3 bind_extractor.py ../captures/bind_demod.bin
```

**What to do:**
1. Run the script
2. Read the output

**Success criteria:** You see 16 hop channels with frequencies

**Example output:**
```
Bind Packet #1
TX ID: 0xA3B2C1D0
Hop Channels:
Ch   Hex    Decimal  Frequency (MHz)
0    0x0D   13       2406.5
1    0x23   35       2417.5
...
```

---

### Minute 20-30: Verify Results

```bash
# Test FEC decoder
python3 fec_decoder.py

# Test CRC
python3 crc.py

# Test packet parser
python3 packet_parser.py
```

**Success criteria:** All tests pass

---

## If Something Goes Wrong

### "No signal in waterfall"
- Increase gain in `01_spectrum_observer.py`:
  - Change `rf_gain = 40`
  - Change `if_gain = 30`
- Move HackRF closer to TX
- Check TX battery

### "No bind packets found"
**Most common issue!**

1. Verify bind mode:
   ```
   - LED should blink RAPIDLY (not slowly)
   - Try holding bind button longer
   - Some TXs need different bind procedure
   ```

2. Try other bind frequency:
   ```bash
   python3 02_bind_capture.py
   # Select option 2 (2.470 GHz)
   ```

3. Check demod quality:
   ```bash
   # Look at first 100 bytes
   xxd ../captures/bind_demod.bin | head -20
   
   # Should see patterns, not all zeros or random
   ```

### "Tests fail"

```bash
# Reinstall dependencies
pip3 install --user --upgrade numpy scipy

# Rerun setup
cd ..
./setup.sh
```

---

## After Success

You now have the hop channels! This is the critical breakthrough.

**Next steps:**

1. **Decode control data** (Week 4):
   - Capture normal TX operation
   - Track frequency hops using extracted channels
   - Decode stick positions

2. **Real-time monitoring**:
   - Use `realtime_monitor.py` (coming in Phase 4)
   - See live stick positions

---

## File Locations Reference

```
afhds2a_decoder/
├── captures/
│   ├── bind_capture.iq          ← Phase 2 output
│   └── bind_demod.bin           ← Phase 3 output
│
├── hop_channels_XXXXXXXX.txt    ← Your extracted channels!
│
└── gnuradio_flowgraphs/
    ├── 01_spectrum_observer.py  ← Start here
    ├── 02_bind_capture.py       ← Then this
    └── 03_gfsk_demodulator.py   ← Then this
```

---

## Expected Timeline

| Task | Time | Cumulative |
|------|------|------------|
| See signal | 5 min | 5 min |
| Capture bind | 5 min | 10 min |
| Demodulate | 5 min | 15 min |
| Extract channels | 5 min | 20 min |
| Verify | 10 min | 30 min |

**Total: 30 minutes** (if everything works first try)

**Realistic with debugging: 2-3 hours**

---

## What You've Achieved

After completing this:

✅ You understand RF capture with HackRF  
✅ You can see AFHDS-2A hopping pattern  
✅ You captured bind mode successfully  
✅ You demodulated GFSK to bits  
✅ You decoded FEC and extracted packets  
✅ **You have the hop channel sequence!**

This is 70% of the work. The remaining 30% is tracking hops in real-time.

---

## Help Resources

**Immediate help:**
- `docs/TROUBLESHOOTING.md`
- Read error messages carefully
- Check file sizes (capture should be ~160 MB)

**Community:**
- r/GNURadio
- r/RTLSDR
- GitHub discussions

**Next phase:**
- `docs/PHASE_4_GUIDE.md` (coming soon)
