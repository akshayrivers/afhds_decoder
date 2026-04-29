#!/usr/bin/env python3
"""
System Test Script

Tests all components of the AFHDS-2A decoder project.
Run this after setup to verify everything works.

Usage:
    python3 test_system.py
"""

import sys
import os
import subprocess

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text):
    """Print section header."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


def test_pass(text):
    """Print pass message."""
    print(f"{GREEN}✓ PASS:{RESET} {text}")


def test_fail(text):
    """Print fail message."""
    print(f"{RED}✗ FAIL:{RESET} {text}")


def test_warn(text):
    """Print warning message."""
    print(f"{YELLOW}⚠ WARN:{RESET} {text}")


def test_info(text):
    """Print info message."""
    print(f"  {text}")


def run_command(cmd, check=False):
    """Run command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        if check and result.returncode != 0:
            return None
        return result.stdout.strip()
    except Exception as e:
        return None


def test_python_imports():
    """Test Python package imports."""
    print_header("Testing Python Imports")
    
    all_pass = True
    
    # Test standard packages
    packages = [
        ('numpy', 'NumPy'),
        ('scipy', 'SciPy'),
    ]
    
    for module, name in packages:
        try:
            __import__(module)
            test_pass(f"{name} installed")
        except ImportError:
            test_fail(f"{name} not found")
            test_info(f"Install with: pip3 install {module}")
            all_pass = False
    
    # Test GNU Radio
    try:
        import gnuradio
        from gnuradio import gr
        version = gr.version()
        test_pass(f"GNU Radio {version}")
    except ImportError as e:
        test_fail("GNU Radio not found")
        test_info("Install with: sudo apt install gnuradio")
        all_pass = False
    
    # Test gr-osmosdr
    try:
        import osmosdr
        test_pass("gr-osmosdr installed")
    except ImportError:
        test_fail("gr-osmosdr not found")
        test_info("Install with: sudo apt install gr-osmosdr")
        all_pass = False
    
    return all_pass


def test_hackrf():
    """Test HackRF One connection."""
    print_header("Testing HackRF One")
    
    # Check if hackrf_info exists
    result = run_command("which hackrf_info")
    if not result:
        test_fail("hackrf_info not found")
        test_info("Install with: sudo apt install hackrf")
        return False
    
    test_pass("HackRF tools installed")
    
    # Check if HackRF is connected
    result = run_command("hackrf_info 2>/dev/null")
    if not result or "No HackRF" in result:
        test_warn("HackRF not connected or not detected")
        test_info("1. Check USB connection")
        test_info("2. Run: sudo usermod -a -G plugdev $USER")
        test_info("3. Log out and back in")
        return False
    
    # Parse HackRF info
    lines = result.split('\n')
    for line in lines:
        if 'Serial number' in line:
            serial = line.split(':')[-1].strip()
            test_pass(f"HackRF detected (Serial: {serial})")
            break
    
    if 'Firmware' in result:
        test_pass("Firmware loaded")
    
    return True


def test_project_structure():
    """Test project directory structure."""
    print_header("Testing Project Structure")
    
    all_pass = True
    
    required_dirs = [
        'python_decoders',
        'gnuradio_flowgraphs',
        'captures',
        'docs'
    ]
    
    for dir_name in required_dirs:
        if os.path.isdir(dir_name):
            test_pass(f"Directory: {dir_name}/")
        else:
            test_fail(f"Missing directory: {dir_name}/")
            all_pass = False
    
    required_files = [
        'README.md',
        'setup.sh',
        'requirements.txt',
        'python_decoders/__init__.py',
        'python_decoders/fec_decoder.py',
        'python_decoders/crc.py',
        'python_decoders/packet_parser.py',
        'python_decoders/bind_extractor.py',
    ]
    
    for file_name in required_files:
        if os.path.isfile(file_name):
            test_pass(f"File: {file_name}")
        else:
            test_fail(f"Missing file: {file_name}")
            all_pass = False
    
    return all_pass


def test_decoders():
    """Test Python decoders."""
    print_header("Testing Decoders")
    
    all_pass = True
    
    # Test FEC decoder
    test_info("Testing FEC decoder...")
    sys.path.insert(0, 'python_decoders')
    
    try:
        from python_decoders.fec_decoder import FECDecoder
        fec = FECDecoder()
        
        # Quick test
        test_bits = [0, 1, 0, 1, 0, 1, 0]
        result = fec.decode_7bit(test_bits)
        
        if result is not None:
            test_pass("FEC decoder works")
        else:
            test_fail("FEC decoder returned None")
            all_pass = False
    except Exception as e:
        test_fail(f"FEC decoder error: {e}")
        all_pass = False
    
    # Test CRC
    test_info("Testing CRC calculator...")
    try:
        from python_decoders.crc import CRC16
        crc = CRC16()
        
        # Known value test
        test_data = b"123456789"
        result = crc.calculate(test_data)
        expected = 0x31C3  # FlySky CRC (init 0x0000)
        
        if result == expected:
            test_pass("CRC calculator works")
        else:
            test_fail(f"CRC mismatch: got 0x{result:04X}, expected 0x{expected:04X}")
            all_pass = False
    except Exception as e:
        test_fail(f"CRC error: {e}")
        all_pass = False
    
    # Test packet parser
    test_info("Testing packet parser...")
    try:
        from python_decoders.packet_parser import PacketParser
        parser = PacketParser()
        test_pass("Packet parser loads")
    except Exception as e:
        test_fail(f"Packet parser error: {e}")
        all_pass = False
    
    return all_pass


def test_gnuradio_scripts():
    """Test GNU Radio scripts."""
    print_header("Testing GNU Radio Scripts")
    
    all_pass = True
    
    scripts = [
        'gnuradio_flowgraphs/01_spectrum_observer.py',
        'gnuradio_flowgraphs/02_bind_capture.py',
        'gnuradio_flowgraphs/03_gfsk_demodulator.py',
    ]
    
    for script in scripts:
        if os.path.isfile(script):
            # Check if it's executable
            if os.access(script, os.X_OK):
                test_pass(f"{script} (executable)")
            else:
                test_warn(f"{script} (not executable)")
                test_info(f"Run: chmod +x {script}")
            
            # Check for syntax errors
            result = run_command(f"python3 -m py_compile {script}")
            if result is not None:
                test_pass(f"{script} (valid Python)")
            else:
                test_fail(f"{script} (syntax errors)")
                all_pass = False
        else:
            test_fail(f"Missing: {script}")
            all_pass = False
    
    return all_pass


def print_summary(results):
    """Print test summary."""
    print_header("Test Summary")
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    if passed == total:
        print(f"{GREEN}All tests passed! ({passed}/{total}){RESET}")
        print()
        print("You're ready to start decoding!")
        print()
        print("Next steps:")
        print("  1. cd gnuradio_flowgraphs")
        print("  2. python3 01_spectrum_observer.py")
        print("  3. Power on FlySky TX and look for hops")
        print()
        return True
    else:
        print(f"{RED}Some tests failed ({passed}/{total} passed, {failed} failed){RESET}")
        print()
        print("Failed tests:")
        for name, passed in results.items():
            if not passed:
                print(f"  - {name}")
        print()
        print("Fix the failed tests and run again.")
        print()
        return False


def main():
    """Main test runner."""
    print(f"{BLUE}")
    print("=" * 60)
    print("AFHDS-2A Decoder - System Test")
    print("=" * 60)
    print(f"{RESET}")
    print()
    print("This will test all components of the decoder.")
    print()
    
    results = {}
    
    # Run tests
    results['Python Imports'] = test_python_imports()
    results['HackRF'] = test_hackrf()
    results['Project Structure'] = test_project_structure()
    results['Decoders'] = test_decoders()
    results['GNU Radio Scripts'] = test_gnuradio_scripts()
    
    # Print summary
    success = print_summary(results)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
