"""The example sensor integration."""
import logging
import paramiko,re

from datetime import timedelta
from datetime import datetime

DOMAIN = "eap225"
SCAN_INTERVAL = timedelta(seconds=30)

_LOGGER = logging.getLogger(__name__)

def setup(hass, config):
    _LOGGER.warning("starting")
    
    api = EAP225Client(config)
    hass.data[DOMAIN] = api

    if not api.update():
      _LOGGER.error("Cannot update (bad host/username/password/ssh not enabled?)")
      return False
    
    #_LOGGER.warning("macs: " + str(hass.data[DOMAIN].get_macs()))

    # Return boolean to indicate that initialization was successful.
    return True

class EAP225Client():
  def __init__(self,config):
    self.host = config[DOMAIN].get("host")
    self.username = config[DOMAIN].get("username")
    self.password = config[DOMAIN].get("password")
    self.interfaces = config[DOMAIN].get("interfaces")

  def get_macs(self):
    self.updateIfNeeded()
    return self.macs

  def validate_mac(self,mac):
    self.updateIfNeeded()
    for m in self.macs:
      if mac == m: return True
    return False

  def update(self):
  
    #_LOGGER.warning("updating")
  
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(self.host, username=self.username, password=self.password)

    txt = ""
    for int in self.interfaces:
      cmd = "wlanconfig %s list" % int

      stdin, stdout, stderr = ssh.exec_command(cmd)
      txt = txt + str(stdout.read())
    ssh.close()
    
    txt = re.finditer("([0-9a-z]{2}[:-]){5}[0-9a-z]{2}",txt,flags=0)

    self.macs = []
    for hex in txt:
      self.macs.append(hex.group())
      
    if self.macs:
      self.lastUpdate = datetime.now()
      return True
    else:
      return False

  def updateIfNeeded(self):
    if self.lastUpdate + SCAN_INTERVAL < datetime.now(): self.update()
        
    
  