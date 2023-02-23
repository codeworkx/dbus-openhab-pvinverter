#!/usr/bin/env python
 
# import normal packages
import platform 
import logging
import sys
import os
import sys
if sys.version_info.major == 2:
    import gobject
else:
    from gi.repository import GLib as gobject
import sys
import time
import requests # for http GET
import configparser # for config/ini file
 
# our own packages from victron
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))
from vedbus import VeDbusService


class DbusOpenhabService:
  def __init__(self, servicename, deviceinstance, paths):
    self._dbusservice = VeDbusService("{}.pv_{}".format(servicename, self._getInverterSerial()))
    self._paths = paths
   
    logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))
 
    productname = self._getProductName()
    connection = self._getOpenhabServer()
 
    # Create the management objects, as specified in the ccgx dbus-api document
    self._dbusservice.add_path('/Mgmt/ProcessName', __file__) # ?
    self._dbusservice.add_path('/Mgmt/ProcessVersion', '1.4.17') # fixed value from fronius-sim 1.4.17
    self._dbusservice.add_path('/Mgmt/Connection', connection)
 
    # Create the mandatory objects    
    self._dbusservice.add_path('/Connected', 1)
    self._dbusservice.add_path('/CustomName', productname)        
    self._dbusservice.add_path('/DeviceInstance', deviceinstance)
    self._dbusservice.add_path('/ErrorCode', 0)
    self._dbusservice.add_path('/FirmwareVersion', 1)
    self._dbusservice.add_path('/Position', self._getInverterPosition()) 
    self._dbusservice.add_path('/ProductId', 41284, gettextcallback = lambda p, v: ('a144')) # copy from working version - see fronius-sim
    self._dbusservice.add_path('/ProductName', productname)
    self._dbusservice.add_path('/Serial', self._getInverterSerial())
    self._dbusservice.add_path('/StatusCode', 11, gettextcallback = lambda p, v: ('Running (MPPT)'))
    self._dbusservice.add_path('/Ac/MaxPower', self._getInverterMaxPower())
    self._dbusservice.add_path('/Ac/PowerLimit', self._getInverterPowerLimit())
    self._dbusservice.add_path('/UpdateIndex', 0)

    # add path values to dbus
    for path, settings in self._paths.items():
      self._dbusservice.add_path(
        self._replacePhaseVar(path), settings['initial'], gettextcallback=settings['textformat'], writeable=True, onchangecallback=self._handlechangedvalue)
 
    # last update
    self._lastUpdate = 0
    
    # last openhab update
    self._lastOpenhabUpdate = 0
 
    # initial values
    self._lastInverterStatus = 0
    self._lastAcVoltage = 0.0
    self._lastAcCurrent = 0.0
    self._lastAcPower = 0.0
    self._lastEnergyForward = 0.0
 
    # add _update function 'timer'
    gobject.timeout_add(500, self._update) # call update routine
 
    # add _signOfLife 'timer' to get feedback in log every 5minutes
    gobject.timeout_add(self._getSignOfLifeInterval()*60*1000, self._signOfLife)


  def _getProductName(self):
    config = self._getConfig()
    value = config['DEFAULT']['ProductName']
    if not value: 
        value = "Openhab Inverter"
    return value
 
 
  def _getSignOfLifeInterval(self):
    config = self._getConfig()
    value = config['DEFAULT']['SignOfLifeLog']
    if not value: 
        value = 0
    return int(value) 
 
 
  def _getUpdateInterval(self):
    config = self._getConfig()
    value = config['DEFAULT']['UpdateInterval']
    if not value: 
        value = 5
    return int(value)
 
 
  def _getInverterPosition(self):
    config = self._getConfig()
    #Debug infos: 0=AC input 1; 1=AC output; 2=AC input 2
    return int(config['INVERTER']['Position'])


  def _getConfig(self):
    config = configparser.ConfigParser()
    config.read("%s/config.ini" % (os.path.dirname(os.path.realpath(__file__))))
    return config;
 

  def _getPhaseFromConfig(self):
    result = "L1"
    config = self._getConfig()
    result = config['INVERTER']['Phase']
    return result
    
  
  def _replacePhaseVar(self, input):
    result = input
    result = result.replace("[*Phase*]", self._getPhaseFromConfig())
    return result
    
  
  def _getOpenhabServer(self):
    config = self._getConfig()
    server = config['OPENHAB']['ServerIP']
    port = config['OPENHAB']['ServerPort']
    if server == "": 
        raise ValueError("Openhab server ip is not set/empty")
    if port == "": 
        raise ValueError("Openhab server port is not set/empty")
    URL = "http://%s:%s" % (server, port)
    return URL
 
 
  def _getOpenhabItemState(self, configItem):
    URL = self._getOpenhabServer()
    config = self._getConfig()
    item = config['ITEMS'][configItem]
    URL = "%s/rest/items/%s/state" % (URL, item)
    response = requests.get(url = URL)
    if response:
        if response.status_code == 200:
            data = response.content.decode('utf-8')
            if not data:
                raise ValueError("Error getting state for item %s" % (item))
        else:
            raise ConnectionError("Invalid response from Openhab server - %s" % (URL))
    else:
        raise ConnectionError("No response from Openhab server - %s" % (URL))
    return data
  
 
  def _getInverterSerial(self):   
    data = self._getOpenhabItemState("InverterSerial");
    return data
 
 
  def _getInverterPowerLimit(self):
    data = self._getOpenhabItemState("InverterPowerLimit");
    return int(data)
 
 
  def _getInverterStatus(self):    
    data = self._getOpenhabItemState("InverterStatus");
    # FIXME
    data = 0
    return int(data)


  def _getAcVoltage(self):
    data = self._getOpenhabItemState("AcVoltage");
    return float(data)
 
 
  def _getAcCurrent(self):
    data = self._getOpenhabItemState("AcCurrent");
    return float(data)


  def _getAcPower(self):
    data = self._getOpenhabItemState("AcPower");
    return float(data)


  def _getEnergyForward(self):
    data = self._getOpenhabItemState("EnergyForward");
    return float(data)
 
 
  def _getInverterMaxPower(self):
    config = self._getConfig()    
    return int(config['INVERTER']['MaxPower'])


  def _signOfLife(self):
    logging.info("--- Start: sign of life ---")
    logging.info("Last _update() call: %s" % (self._lastUpdate))
    logging.info("Last _updateOpenhab() call: %s" % (self._lastOpenhabUpdate))
    logging.info("--- End: sign of life ---")
    return True
  

  def _predictACPowerValue(self, lastUpdate, lastValue, lastValueChangePercSecond):
    return lastValue*((1+((time.time() - lastUpdate)*lastValueChangePercSecond)))  
 
 
  def _update(self):
    try:
       # get data from openhab
       if self._lastOpenhabUpdate == 0 or (time.time()-self._lastOpenhabUpdate) >= self._getUpdateInterval():
           self._lastInverterStatus = self._getInverterStatus()
           self._lastAcVoltage = self._getAcVoltage()
           self._lastAcCurrent = self._getAcCurrent()
           self._lastAcPower = self._getAcPower()
           self._lastEnergyForward = self._getEnergyForward()

           # logging
           logging.debug("--- OPENHAB ---");
           logging.debug("Inverter status: %s" % (self._lastInverterStatus))
           logging.debug("AC voltage: %s" % (self._lastAcVoltage))
           logging.debug("AC current: %s" % (self._lastAcCurrent))
           logging.debug("AC power: %s" % (self._lastAcPower))
           logging.debug("Energy forward: %s" % (self._lastEnergyForward))
           logging.debug("---------------");

           # extract values
           self._lastOpenhabUpdate = time.time()

       # set values       
       self._dbusservice['/StatusCode'] = self._lastInverterStatus
       self._dbusservice[self._replacePhaseVar('/Ac/[*Phase*]/Voltage')] = self._lastAcVoltage
       self._dbusservice[self._replacePhaseVar('/Ac/[*Phase*]/Current')] = self._lastAcCurrent
       self._dbusservice[self._replacePhaseVar('/Ac/[*Phase*]/Power')] = self._lastAcPower
       self._dbusservice[self._replacePhaseVar('/Ac/[*Phase*]/Energy/Forward')] = self._lastEnergyForward
       self._dbusservice['/Ac/Voltage'] = self._lastAcVoltage
       self._dbusservice['/Ac/Current'] = self._lastAcCurrent
       self._dbusservice['/Ac/Power'] = self._lastAcPower
       self._dbusservice['/Ac/Energy/Forward'] = self._lastEnergyForward
       
       # update lastupdate vars
       self._lastUpdate = time.time()   
       
       # increment UpdateIndex - to show that new data is available
       index = self._dbusservice['/UpdateIndex'] + 1  # increment index
       if index > 255:   # maximum value of the index
         index = 0       # overflow from 255 to 0
       self._dbusservice['/UpdateIndex'] = index       
       
       # logging
       logging.debug("--- DBUS ---");
       logging.debug("/StatusCode : %s" % (self._dbusservice['/StatusCode']))
       logging.debug("/Ac/Voltage : %s" % (self._dbusservice['/Ac/Voltage']))
       logging.debug("/Ac/Current : %s" % (self._dbusservice['/Ac/Current']))
       logging.debug("/Ac/Power : %s" % (self._dbusservice['/Ac/Power']))
       logging.debug("/Ac/Energy/Forward : %s" % (self._dbusservice['/Ac/Energy/Forward']))
       logging.debug("------------");

    except Exception as e:
       logging.critical('Error at %s', '_update', exc_info=e)

    # return true, otherwise add_timeout will be removed from GObject - see docs http://library.isr.ist.utl.pt/docs/pygtk2reference/gobject-functions.html#function-gobject--timeout-add
    return True
 
 
  def _handlechangedvalue(self, path, value):
    logging.debug("someone else updated %s to %s" % (path, value))
    return True # accept the change
 


def main():
  # configure logging
  logging.basicConfig(      format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.DEBUG,
                            handlers=[
                                logging.FileHandler("%s/current.log" % (os.path.dirname(os.path.realpath(__file__)))),
                                logging.StreamHandler()
                            ])
 
  try:
      logging.info("Start");
  
      from dbus.mainloop.glib import DBusGMainLoop
      # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
      DBusGMainLoop(set_as_default=True)
     
      # formatting 
      _kwh = lambda p, v: (str(round(v, 2)) + ' KWh')
      _a = lambda p, v: (str(round(v, 1)) + ' A')
      _w = lambda p, v: (str(round(v, 1)) + ' W')
      _v = lambda p, v: (str(round(v, 1)) + ' V')   
     
      # start our main-service
      pvac_output = DbusOpenhabService(
        servicename='com.victronenergy.pvinverter',
        deviceinstance=23, #pvinverters from 20-29
        paths={
          '/Ac/Energy/Forward': {'initial': 0, 'textformat': _kwh},     
          '/Ac/Power': {'initial': 0, 'textformat': _w},
          
          '/Ac/Current': {'initial': 0, 'textformat': _a},
          '/Ac/Voltage': {'initial': 0, 'textformat': _v},
          
          '/Ac/[*Phase*]/Voltage': {'initial': 0, 'textformat': _v},
          '/Ac/[*Phase*]/Current': {'initial': 0, 'textformat': _a},
          '/Ac/[*Phase*]/Power': {'initial': 0, 'textformat': _w},
          '/Ac/[*Phase*]/Energy/Forward': {'initial': 0, 'textformat': _kwh},          
        })
     
      logging.info('Connected to dbus, and switching over to gobject.MainLoop() (= event based)')
      mainloop = gobject.MainLoop()
      mainloop.run()
  except Exception as e:
    logging.critical('Error at %s', 'main', exc_info=e)
if __name__ == "__main__":
  main()
