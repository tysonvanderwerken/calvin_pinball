"""ZeDMD.

Use PPUC
https://github.com/PPUC

Use libZeDMD Python extension
https://github.com/PPUC/libzedmd-python-pybind11-extension

"""
import logging
import ctypes
import pathlib
import platform
try:
    import numpy
except ImportError as e:
    IMPORT_NUMPY_FAILED = e
else:
    IMPORT_NUMPY_FAILED = None    # type: ignore

from PIL import Image

from mpf.core.platform import RgbDmdPlatform
from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface

# Load ZeDMD libraries
try:
    DIR_PATH = str(pathlib.Path(__file__).parent.resolve())
    if platform.machine in ("arm64", "aarch64"):
        ARCH = "arm64"
    else:
        ARCH = "x64"
    if platform.system() == "Windows":
        libzedmd = ctypes.CDLL(DIR_PATH + '/zedmd_lib/win_x64/zedmd64.dll')
        from mpf.platforms.zedmd_lib.win_x64.extending import ZeDMD_ext
    elif platform.system() == "Darwin":
        LIB_DIR = '/zedmd_lib/macos_' + ARCH
        libsockpp = ctypes.CDLL(DIR_PATH + LIB_DIR + '/libsockpp.dylib')
        libserialport = ctypes.CDLL(DIR_PATH + LIB_DIR + '/libserialport.dylib')
        libzedmd = ctypes.CDLL(DIR_PATH + LIB_DIR + '/libzedmd.dylib')
        if ARCH == "arm64":
            from mpf.platforms.zedmd_lib.macos_arm64.extending import ZeDMD_ext
        else:
            from mpf.platforms.zedmd_lib.macos_x64.extending import ZeDMD_ext
    else:    # platform.system() == Linux
        libzedmd = ctypes.CDLL(DIR_PATH + '/zedmd_lib/linux_' + ARCH + '/libzedmd.so')
        if ARCH == "arm64":
            from mpf.platforms.zedmd_lib.linux_arm64.extending import ZeDMD_ext
        else:
            from mpf.platforms.zedmd_lib.linux_x64.extending import ZeDMD_ext
except ImportError as e:
    IMPORT_LIB_FAILED = e
else:
    IMPORT_LIB_FAILED = None    # type: ignore


class ZeDmdPlatform(RgbDmdPlatform):

    """ZeDmd."""

    __slots__ = ["device", "config"]

    def __init__(self, machine):
        """Initialize ZeDmd."""
        if IMPORT_NUMPY_FAILED:
            raise AssertionError('Failed to load numpy. Did you install numpy ? '
                                 'Try: "pip3 install numpy".') from IMPORT_NUMPY_FAILED
        if IMPORT_LIB_FAILED:
            raise AssertionError('Failed to load ZeDMD libraries.') from IMPORT_LIB_FAILED
        super().__init__(machine)
        self.device = None
        self.config = None
        self.config = self.machine.config_validator.validate_config(
            config_spec='zedmd',
            source=self.machine.config.get('zedmd', {})
        )
        self._configure_device_logging_and_debug('ZeDMD', self.config)

    async def initialize(self):
        """Initialize platform."""

    def stop(self):
        """Stop platform."""
        if self.device:
            self.device.stop()

    def __repr__(self):
        """Return string representation."""
        return '<Platform.ZeDmd>'

    def configure_rgb_dmd(self, name: str):
        """Configure rgb dmd."""
        if not self.device:
            self.device = ZeDmdDevice(self.config)
        return self.device


# noinspection PyCallingNonCallable
class ZeDmdDevice(DmdPlatformInterface):

    """A ZeDmd device."""

    __slots__ = ["config", "log", "matrix"]

    def __init__(self, config):
        """Initialize ZeDmd device."""
        self.config = config
        self.matrix = ZeDMD_ext()
        self.log = logging.getLogger('ZeDMDDevice')
        self.log.debug('Numpy version : %s', numpy.__version__)

    def update(self, data):
        """Update DMD data."""
        image = Image.frombytes('RGB', (self.config["width"], self.config["height"]), data)
        self.matrix.RenderRgb888(image)

    def set_brightness(self, brightness):
        """Set brightness.

        Range is [0.0 ... 1.0].
        """
        if brightness < 0.0 or brightness > 1.0:
            raise AssertionError("Brightness has to be between 0 and 1.")
        new_brightness = round(brightness * 15)
        self.log.info("Set brightness = {0:d}".format(new_brightness))
        self.matrix.SetBrightness(new_brightness)

    def stop(self):
        """Stop device."""
        self.matrix.Close()
