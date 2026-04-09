import unittest
from csv_to_flipper_ir import IRProtocolConverter

class TestIRConversion(unittest.TestCase):
    def test_nec_conversion(self):
        # NEC example: Device 1, Subdevice 0, Function 1
        # Address: 01 00 00 00
        # Command: 01 FE 00 00 (FE is bitwise NOT of 01)
        addr, cmd = IRProtocolConverter.convert("NEC", 1, 0, 1)
        self.assertEqual(addr, "01 00 00 00")
        self.assertEqual(cmd, "01 FE 00 00")

    def test_samsung_conversion(self):
        addr, cmd = IRProtocolConverter.convert("SAMSUNG", 7, 7, 2)
        self.assertEqual(addr, "07 07 00 00")
        self.assertEqual(cmd, "02 00 00 00")

    def test_sony_conversion(self):
        addr, cmd = IRProtocolConverter.convert("SONY", 1, 0, 42)
        self.assertEqual(addr, "01 00 00 00")
        self.assertEqual(cmd, "2A 00 00 00") # 42 in hex is 2A

    def test_fallback_hex(self):
        addr, cmd = IRProtocolConverter.convert("UNKNOWN", 255, 0, 10)
        self.assertEqual(addr, "00FF 00 00")
        self.assertEqual(cmd, "000A 00 00")

if __name__ == "__main__":
    unittest.main()
