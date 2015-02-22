"""
PIN diode attenuator class and calibration methods
"""
import logging
import scipy

from Electronics.Interfaces.LabJack import LJTickDAC
from Electronics.Instruments import Attenuator

module_logger = logging.getLogger(__name__)

class PINattenuator(Attenuator):
  """
  Voltage-controlled PIN diode attenuator for WBDC

  The superclass is defined and described in::
    DSN-Sci-packages/Electronics/Interfaces/LabJack

  A LJTickDAC controls two voltages.

  The lower (even) number IO port provides the clock (SCK) and the odd number
  port the serial data (SDA).

  Attributes
  
  @type bias_list : list of float
  @ivar bias_list : bias voltages for calibration

  @type volts : list of float
  @ivar volts : auto-generated control voltages for calibration (V)

  @type pwrs : list of float
  @ivar pwrs : measured powers corresponding to 'volts' (dBm)

  @type bias : float
  @ivar bias : best bias value out of 'bias_list'

  @type coefs : numpy array of float
  @ivar coefs : polynomial coeffients for best calibration curve

  @type lower : float
  @ivar lower : lowest power measured

  @type upper : float
  @ivar upper : highest power measured

  @type atten_table : dictionary
  @ivar atten_table : control voltage indexed by attenuation
  """
  def __init__(self, name, voltage_source):
    """
    """
    self.name = name
    self.VS = voltage_source
    mylogger = logging.getLogger(module_logger.name+".PINattenuator")
    mylogger.debug(" Initializing attenuator %s with voltage source %s",
                   self.name, self.VS)
                   
  def define_coefs(self):
    pass

  def set_atten(self, atten):
    """
    Set the attenuation

    @param atten : attenuation in dB
    @type  atten : float
    """
    if atten > 0.0:
      atten *= -1.
    if atten > 15:
      raise "Too much attenuation requested"
    else:
      volt = self.controlVoltage(atten)
      self.setVoltages([self.bias,volt])
  
  def controlVoltage(self, pwr):
    """
    Compute control voltage for a given attenuation

    @return: float control voltage V
    """
    function = scipy.poly1d(self.coefs)
    minV = self.volts[0]
    maxV = self.volts[-1]
    return scipy.optimize.bisect(function-pwr, minV, maxV)

  def atten(self, polycoefs, controlV):
    """
    @type polycoefs : numpy array of float
    @param polycoefs : polynomial coefficients

    @type controlV : float
    @param controlV : control voltage (V)
    """
    return function - scipy.poly1d(self.coefs)(controlV)

