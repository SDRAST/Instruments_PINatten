"""
For now this runs in the apps directory so import is simple
"""
from calibrate_PINs import *

import logging
import numpy as NP
import time

from support.pyro import get_device_server

 
if __name__ == "__main__":
  logging.basicConfig(level=logging.WARNING)
  mylogger = logging.getLogger()
  mylogger.setLevel(logging.INFO)
  
  fe = get_device_server("FE_server-krx43", "crux")
  print "Feed 1:",fe.set_WBDC(13) # set feed 1 to sky
  print "Feed 2:",fe.set_WBDC(15) # set feed 2 to sky
  #print fe.set_WBDC(14) # set feed 1 to load
  #print fe.set_WBDC(16) # set feed 2 to load
  for pm in ['PM1', 'PM2', 'PM3', 'PM4']:
    # set PMs to dBm
    print fe.set_WBDC(400+int(pm[-1]))

  rx = get_device_server("wbdc2hw_server-dss43wbdc2", "crux")
  crossed = rx.get_Xswitch_state()
  if crossed:
    mylogger.warning(" cross-switch in set")
  polsec_keys = rx.request("self.pol_sec.keys()")
  polsec_keys.sort()
  attenuator_keys = {}
  for polsec in polsec_keys:
    attenuator_keys[polsec] = rx.request("self.pol_sec['"+polsec+"'].atten.keys()")
  for ctlV in ctl_volts:
    for polsec in polsec_keys:
      for key in attenuator_keys[polsec]:
        rx.requestattenuators[atn].VS.setVoltage(ctlV)
  
