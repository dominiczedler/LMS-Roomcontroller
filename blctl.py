# Based on ReachView code from Egor Fedorov (egor.fedorov@emlid.com)
# Updated for Python 3.6.8 on a Raspberry  Pi


import time
import pexpect
import logging


logger = logging.getLogger("btctl")


class Bluetoothctl:
    """A wrapper for bluetoothctl utility."""

    def __init__(self):
        self.process = pexpect.spawnu("bluetoothctl", echo=False, timeout=8)

    def send(self, command, pause=0):
        self.process.send(f"{command}\n")
        time.sleep(pause)
        self.process.expect([r"0;94m", pexpect.TIMEOUT, pexpect.EOF])

    def get_output(self, command):
        """Run a command in bluetoothctl prompt, return output as a list of lines."""
        self.send(command)
        return self.process.before.split("\r\n")

    def start_discover(self):
        """Start bluetooth scanning process."""
        try:
            self.process.send(f"scan on\n")
            time.sleep(2)
        except Exception as e:
            logger.error(e)
            return False
        else:
            # TODO: This gives an error messsage if repeated
            res = self.process.expect(
                ["Failed to start discovery", "Discovery started", pexpect.EOF, pexpect.TIMEOUT], 3
            )
            return res == 1

    def make_discoverable(self):
        """Make device discoverable."""
        try:
            self.send("discoverable on")
        except Exception as e:
            logger.error(e)

    def parse_device_info(self, info_string):
        """Parse a string corresponding to a device."""
        device = {}
        block_list = ["[\x1b[0;", "removed"]
        if not any(keyword in info_string for keyword in block_list):
            try:
                device_position = info_string.index("Device")
            except ValueError:
                pass
            else:
                if device_position > -1:
                    attribute_list = info_string[device_position:].split(" ", 2)
                    device = {
                        "mac_address": attribute_list[1],
                        "name": attribute_list[2],
                    }
        return device

    def wait_for_disconnect(self, addr):
        self.process.expect([f"{addr} Connected: no"], timeout=None)

    def get_available_devices(self):
        """Return a list of tuples of paired and discoverable devices."""
        available_devices = []
        try:
            out = self.get_output("devices")
            print(out)
        except Exception as e:
            logger.error(e)
        else:
            for line in out:
                device = self.parse_device_info(line)
                if device:
                    available_devices.append(device)
        return available_devices

    def get_paired_devices(self):
        """Return a list of tuples of paired devices."""
        paired_devices = []
        try:
            out = self.get_output("paired-devices")
        except Exception as e:
            logger.error(e)
        else:
            for line in out:
                device = self.parse_device_info(line)
                if device:
                    paired_devices.append(device)
        return paired_devices

    def get_discoverable_devices(self):
        """Filter paired devices out of available."""
        available = self.get_available_devices()
        paired = self.get_paired_devices()
        return [d for d in available if d not in paired]

    def get_device_info(self, mac_address):
        """Get device info by mac address."""
        try:
            out = self.get_output(f"info {mac_address}")
        except Exception as e:
            logger.error(e)
            return False
        else:
            return out

    def pair(self, mac_address):
        """Try to pair with a device by mac address."""
        try:
            self.send(f"pair {mac_address}", 4)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["Failed to pair", "Pairing successful", pexpect.EOF, pexpect.TIMEOUT]
            )
            return res == 1

    def trust(self, mac_address):
        try:
            self.send(f"trust {mac_address}\n", 4)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["Failed to trust", "Trusted: yes", pexpect.EOF, pexpect.TIMEOUT]
            )
            return res == 1

    def untrust(self, mac_address):
        try:
            self.send(f"untrust {mac_address}\n", 4)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["Failed to untrust", "untrust succeeded", pexpect.EOF, pexpect.TIMEOUT]
            )
            return res == 1

    def remove(self, mac_address):
        """Remove paired device by mac address, return success of the operation."""
        try:
            self.send(f"remove {mac_address}\n", 3)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["not available", "Device has been removed", pexpect.EOF, pexpect.TIMEOUT]
            )
            return res == 1

    def connect(self, mac_address):
        """Try to connect to a device by mac address."""
        self.process.send(f"connect {mac_address}\n")
        res = self.process.expect(["Failed to connect", "Connection successful", pexpect.TIMEOUT, pexpect.EOF], 5) == 1
        return res

    def disconnect(self, mac_address):
        """Try to disconnect to a device by mac address."""
        self.process.send(f"disconnect {mac_address}\n")
        res = self.process.expect(["Failed to disconnect", "Connected: no", "Successful disconnected",
                                   pexpect.TIMEOUT, pexpect.EOF], 5) in [1, 2]
        return res
