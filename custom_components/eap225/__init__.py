"""The example sensor integration."""
import logging
import re
from datetime import timedelta
from datetime import datetime

import paramiko

DOMAIN = "eap225"
#In respect to the homeassistant appropiate polling policy the minimal polling frequency is limited by the component to 10 seconds.
#Each value under 15 seconds will default to 15
#Reference: https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/appropriate-polling/
MIN_APPROPIATE_SCAN_INTERVAL = 15

_LOGGER = logging.getLogger(__name__)

def setup(hass, config):

    _LOGGER.debug("starting")
    
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
    #Check if the new or old cli should be used - default: Old CLI
    self.cli_omada = config[DOMAIN].get("cli_omada", False)

    #Validate scan interval - see explanaition above at MIN_APPROPIATE_SCAN_INTERVAL
    try:
      validated_scan_interval = int(config[DOMAIN].get("scan_interval", 30))
      if (validated_scan_interval < MIN_APPROPIATE_SCAN_INTERVAL):
        validated_scan_interval = MIN_APPROPIATE_SCAN_INTERVAL

      self.scan_interval = timedelta(seconds=validated_scan_interval)
    except Exception as e:
      _LOGGER.warning("COnfigured scan interval is not valid - default value is used! - Error: " + str(e))
      self.scan_interval = timedelta(seconds=validated_scan_interval)


    _LOGGER.info(
    "EAP225 Integration - Using "
    + ("New CLI" if self.cli_omada else "Old CLI")
    + " mode - Scan Interval: "
    + str(self.scan_interval)
    + " Using host "
    + self.username + "@" + self.host
)

  def normalize_mac(self, mac):
    if mac is None:
      return ""
    normalized_mac = re.sub(r"[^0-9a-fA-F]", "", str(mac)).lower()
    if len(normalized_mac) != 12:
      return ""
    return normalized_mac

  def get_macs(self):
    self.updateIfNeeded()
    return self.macs

  def validate_mac(self,mac):
    self.updateIfNeeded()
    normalized_mac = self.normalize_mac(mac)
    for m in self.macs:
      if normalized_mac == self.normalize_mac(m): return True
    return False

  def update(self):
  
    _LOGGER.debug("updating")
  
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    self.macs = []

    if(not self.cli_omada):
      #Establish SSH connection in this block to prevent disrupting already configured setups with the new ssh connection configuration
      ssh.connect(self.host, username=self.username, password=self.password)

      _LOGGER.debug("Use old CLI Version (pre v5.2)")
      stdin, stdout, stderr = ssh.exec_command("iwconfig")
      interfaces = re.findall("ath[0-9]+",str(stdout.read()))

      txt = ""
      for int in interfaces:
        cmd = f"wlanconfig {int} list"

        stdin, stdout, stderr = ssh.exec_command(cmd)
        txt = txt + str(stdout.read())
      ssh.close()

      txt = re.finditer("([0-9a-z]{2}[:-]){5}[0-9a-z]{2}",txt,flags=0)
      
      for hex in txt:
        self.macs.append(hex.group())

    else:
      _LOGGER.debug("Updating via new Omada CLI")
      ssh.connect(hostname=self.host, username=self.username, password=self.password, allow_agent=False, look_for_keys=False)

      # Create a new shell
      chan = ssh.invoke_shell()
      chan.settimeout(5)
      #Wait for the interactive shell
      self.read_until(chan, (">", "#"))
      #Enable privileged mode (normally no password needed)
      enable_output = self.send_and_read(chan, "enable", ("#", "Password:"))
      #Fetch all conntected hosts
      station_info = self.send_and_read(chan, "show station info", ("#",))

      chan.close()
      ssh.close()

      station_info_macs = re.findall(r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}", station_info, flags=0)
      
      for mac in station_info_macs:
        self.macs.append(mac)

    if self.macs:
      self.lastUpdate = datetime.now()
      return True
    else:
      return False

  def updateIfNeeded(self):
    if self.lastUpdate + self.scan_interval < datetime.now(): self.update()

  #Additions for Omada CLI to use the interactive shell
  def read_until(self, channel, markers):
    output = ""
    while not output.rstrip().endswith(markers):
        output += channel.recv(65535).decode("utf-8", errors="replace")
    return output


  def send_and_read(self, channel, command, markers):
    channel.send(command + "\n")
    return self.read_until(channel, markers)
