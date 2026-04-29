# AFHDS-2A Decoder Project

Complete working implementation to decode FlySky AFHDS-2A protocol using HackRF One.

## Project Structure

```
afhds2a_decoder/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── setup.sh                          # Automated setup script
│
├── gnuradio_flowgraphs/              # GNU Radio .grc files
│   ├── 01_spectrum_observer.grc      # Phase 1: See the signal
│   ├── 02_bind_capture.grc           # Phase 2: Capture bind mode
│   ├── 03_gfsk_demodulator.grc       # Phase 3: Demodulate to bits
│   └── 04_realtime_decoder.grc       # Phase 4: Real-time tracking
│
├── python_decoders/                  # Python decoding scripts
│   ├── __init__.py
│   ├── fec_decoder.py                # FEC (7,4) implementation
│   ├── crc.py                        # CRC-16 calculator
│   ├── packet_parser.py              # Packet structure parser
│   ├── bind_extractor.py             # Extract hop channels from bind
│   ├── control_decoder.py            # Decode control packets
│   ├── hop_tracker.py                # Frequency hopping tracker
│   └── realtime_monitor.py           # Live data display
│
├── captures/                         # Store IQ captures here
│   └── .gitkeep
│
├── tests/                            # Test files and samples
│   ├── test_fec.py
│   ├── test_crc.py
│   └── sample_packets.bin
│
└── docs/
    ├── QUICKSTART.md                 # Quick start guide
    ├── PHASE_1_GUIDE.md              # Detailed phase guides
    ├── PHASE_2_GUIDE.md
    ├── PHASE_3_GUIDE.md
    └── TROUBLESHOOTING.md
```

## Quick Setup (Ubuntu/Debian)

```bash
# 1. Clone or extract this project
cd afhds2a_decoder

# 2. Run setup script (installs everything)
chmod +x setup.sh
./setup.sh

# 3. Test HackRF connection
hackrf_info

# 4. Start with Phase 1
gnuradio-companion gnuradio_flowgraphs/01_spectrum_observer.grc
```

## Manual Setup

If automated setup fails:

```bash
# Install system dependencies
sudo apt update
sudo apt install -y \
    gnuradio \
    gr-osmosdr \
    hackrf \
    python3-pip \
    python3-numpy \
    python3-scipy \
    python3-matplotlib

# Install Python packages
pip3 install -r requirements.txt

# Test installation
python3 -c "import gnuradio; print('GNU Radio OK')"
hackrf_info
```

## Usage Workflow

### Phase 1: Spectrum Observation (Day 1)
```bash
# Open spectrum observer
gnuradio-companion gnuradio_flowgraphs/01_spectrum_observer.grc

# Power on FlySky TX, observe frequency hops
# Expected: Bursts every ~3.85ms jumping around 2.4 GHz
```

### Phase 2: Bind Mode Capture (Day 2-3)
```bash
# Put TX in bind mode (hold bind button while powering on)
gnuradio-companion gnuradio_flowgraphs/02_bind_capture.grc

# Capture 10 seconds to: captures/bind_capture.iq
```

### Phase 3: Demodulation (Day 4-7)
```bash
# Demodulate captured IQ to bits
gnuradio-companion gnuradio_flowgraphs/03_gfsk_demodulator.grc

# Extract bind packet and hop channels
python3 python_decoders/bind_extractor.py captures/bind_demod.bin
```

### Phase 4: Real-time Decoding (Day 8+)
```bash
# Real-time control data decoding
python3 python_decoders/realtime_monitor.py
```

## Expected Output Examples

### After Phase 2 (Bind Capture):
```
Bind packet captured successfully!
TX ID: 0xA3B2C1D0
Hop Channels (16):
  Ch 0: 0x0D → 2406.5 MHz
  Ch 1: 0x23 → 2417.5 MHz
  Ch 2: 0x45 → 2434.5 MHz
  ...
```

### After Phase 4 (Control Decode):
```
=== FlySky Control Data ===
Aileron:  1523 μs (center: 1500)
Elevator: 1498 μs
Throttle: 1000 μs (min)
Rudder:   1501 μs
SwA:      1000 μs
SwB:      1500 μs
...
Packet rate: 76% (245/321 packets)
```

## Hardware Setup

### HackRF One Configuration
- Antenna: 2.4 GHz (included antenna works)
- USB: Use USB 2.0 port (USB 3.0 can cause noise)
- Position: Within 1-2 meters of FlySky TX initially

### FlySky Transmitter
- Any AFHDS-2A compatible TX:
  - FlySky FS-i6
  - FlySky FS-i6S
  - FlySky FS-i6X
- Bind mode: Hold bind button during power-on

## Troubleshooting

### "hackrf_info shows nothing"
```bash
# Check USB connection
lsusb | grep HackRF

# Fix permissions
sudo usermod -a -G plugdev $USER
# Log out and back in

# Reinstall udev rules
sudo apt install --reinstall hackrf
```

### "GNU Radio flowgraph won't run"
```bash
# Check Python path
python3 -c "import osmosdr; print('osmosdr OK')"

# Rebuild GNU Radio blocks
gnuradio-config-info --version
```

### "No signal visible in waterfall"
- Increase gain (LNA: 40, VGA: 30)
- Verify TX is powered on
- Check frequency: 2.442 GHz for normal mode, 2.406 GHz for bind
- Try different antenna position

## Project Goals by Week

**Week 1:** Capture bind mode IQ successfully  
**Week 2:** Demodulate to bits, see patterns  
**Week 3:** Decode bind packet, extract hop table  
**Week 4:** Real-time control data decoding

## Key Files Reference

| Task | File to Use |
|------|-------------|
| See signal first time | `01_spectrum_observer.grc` |
| Capture bind mode | `02_bind_capture.grc` |
| Test FEC decoder | `tests/test_fec.py` |
| Extract hop channels | `bind_extractor.py` |
| Monitor live data | `realtime_monitor.py` |

## Support & Resources

- **Issues?** Check `docs/TROUBLESHOOTING.md`
- **Phase guides:** See `docs/PHASE_*_GUIDE.md`
- **Protocol reference:** https://github.com/pascallanger/DIY-Multiprotocol-TX-Module
- **Timing reference:** https://fareham.org/rw3-afhds2a.shtml

## License

MIT License - Free to use, modify, distribute

## Contributing

Found a bug? Improved the decoder? Submit issues/PRs!

---

**Next Step:** Run `./setup.sh` and open `01_spectrum_observer.grc`
