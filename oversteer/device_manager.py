import logging
import os
import pyudev
import time
from .device import Device
from . import wheel_ids as wid

class DeviceManager:

    def __init__(self):
        self.supported_wheels = {
            wid.LG_G29: 900,
            wid.LG_G29PS4: 900,
            wid.LG_G920: 900,
            wid.LG_G923X: 900,
            wid.LG_G923P: 900,
            wid.LG_DF: 270,
            wid.LG_MOMO: 270,
            wid.LG_DFP: 900,
            wid.LG_G25: 900,
            wid.LG_DFGT: 900,
            wid.LG_G27: 900,
            wid.LG_SFW: 270,
            wid.LG_MOMO2: 270,
            wid.LG_WFG: 180,
            wid.LG_WFFG: 180,
            wid.TM_FFRW: 180,
            wid.TM_T150: 1080,
            wid.TM_T248: 900,
            wid.TM_T300RS: 1080,
            wid.TM_T300RS_FF1: 1080,
            wid.TM_T500RS: 1080,
            wid.TM_TX: 900,
            wid.FT_CSL_ELITE: 1080,
            wid.FT_CSL_ELITE_PS4: 1080,
            wid.FT_CSV2: 900,
            wid.FT_CSV25: 900,
            wid.FT_PDD1: 1080,
            wid.FT_PDD2: 1080,
            wid.FT_CSL_DD: 1080,
            wid.XX_FFBOARD: 1080,
        }
        self.devices = {}
        self.changed = True

    def start(self):
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by('input')
        self.observer = pyudev.MonitorObserver(monitor, self.register_event)
        self.init_device_list()
        self.observer.start()

    def stop(self):
        self.observer.stop()

    def register_event(self, action, udevice):
        usb_id = str(udevice.get('ID_VENDOR_ID')) + ':' + str(udevice.get('ID_MODEL_ID'))
        if usb_id not in self.supported_wheels:
            return
        seat_id = udevice.get('ID_FOR_SEAT')
        logging.debug("%s: %s", action, seat_id)
        if seat_id is None:
            return
        if action == 'add':
            self.update_device_list(udevice)
            device = self.get_device(seat_id)
            if device and device.dev_name:
                device.enable()
                time.sleep(5)
                self.changed = True
        if action == 'remove':
            device = self.get_device(seat_id)
            if device:
                device.disable()
                self.changed = True

    def init_device_list(self):
        context = pyudev.Context()
        for udevice in context.list_devices(subsystem='input', ID_INPUT_JOYSTICK=1):
            usb_id = str(udevice.get('ID_VENDOR_ID')) + ':' + str(udevice.get('ID_MODEL_ID'))
            if usb_id in self.supported_wheels:
                self.update_device_list(udevice)

        logging.debug('Devices: %s', self.devices)

        self.changed = True

    def update_device_list(self, udevice):
        seat_id = udevice.get('ID_FOR_SEAT')
        logging.debug("update_device_list: %s", seat_id)
        if seat_id is None:
            return

        if seat_id not in self.devices:
            self.devices[seat_id] = Device(self, {
                'seat_id': seat_id,
            })

        device = self.devices[seat_id]

        if 'DEVNAME' in udevice:
            if 'event' in udevice.get('DEVNAME'):
                logging.debug("DEVNAME: %s ID_VENDOR_ID: %s ID_MODEL_ID: %s", udevice.get('DEVNAME'),
                udevice.get('ID_VENDOR_ID'), udevice.get('ID_MODEL_ID'))
                usb_id = str(udevice.get('ID_VENDOR_ID')) + ':' + str(udevice.get('ID_MODEL_ID'))
                device.set({
                    'vendor_id': udevice.get('ID_VENDOR_ID'),
                    'product_id': udevice.get('ID_MODEL_ID'),
                    'usb_id': usb_id,
                    'dev_name': udevice.get('DEVNAME'),
                    'max_range': self.supported_wheels[usb_id],
                })
        else:
            logging.debug("NAME: %s", udevice.get('NAME'))
            device.set({
                'dev_path': os.path.realpath(os.path.join(udevice.sys_path, 'device')),
                'name': udevice.get('NAME').strip('"'),
            })

    def first_device(self):
        if self.devices:
            return self.get_device(next(iter(self.devices)))
        return None

    def get_devices(self):
        self.changed = False
        return list(self.devices.values())

    def get_device(self, did):
        if did is None:
            return None
        if did in self.devices:
            return self.devices[did]
        return next((item for item in self.devices.values() if item.dev_name == did), None)

    def is_changed(self):
        return self.changed
