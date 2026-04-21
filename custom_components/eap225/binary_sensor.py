from homeassistant.const import STATE_OFF, STATE_ON
import logging
from homeassistant.helpers.entity import Entity
from . import DOMAIN
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from datetime import timedelta

SCAN_INTERVAL = timedelta(seconds=15)
_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
  sensor = eap225Sensor(hass,config)
  add_devices([sensor])

class eap225Sensor(Entity):
  
  def __init__(self,hass,config):
    self.mac = config.get("mac")
    self._name = config.get("name")
    self.api = hass.data[DOMAIN]
    self.update()
    
  @property
  def is_on(self):
    """Return true if the binary sensor is on."""
    return bool(self._state)

  @property
  def state(self):
    """Return the state of the binary sensor."""
    return STATE_ON if self.is_on else STATE_OFF
  
  @property
  def name(self):
    return self._name
  
  @property
  def device_class(self):
    """Return the class of this device, from component DEVICE_CLASSES."""
    return BinarySensorDeviceClass.PRESENCE
    
  def update(self):
    #_LOGGER.warning(f"Updating {self._name}")
    self._state = self.api.validate_mac(self.mac)
    #_LOGGER.warning(f"State: {self._state}")