"""
PIN diode attenuator class and calibration methods
"""
import logging
import scipy
import dill as pickle

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
  def __init__(self, name, voltage_source, ctlV_spline,
               min_gain, max_gain):
    """
    """
    self.name = name
    self.VS = voltage_source
    self.spline = ctlV_spline
    self.min_gain = min_gain
    self.max_gain = max_gain
    self.max_atten = self.max_gain - self.min_gain
    mylogger = logging.getLogger(module_logger.name+".PINattenuator")
    mylogger.debug(" Initializing attenuator %s with voltage source %s",
                   self.name, self.VS)
    Attenuator.__init__(self, self.name)
    self.atten = None
    self.logger = mylogger
    
  def get_atten(self):
    """
    Returns attenuation for `pol' inputs of pol section.

    Unfortunately, we cannot read the commanded voltage of a TickDAC.
        """
    return self.atten

  def set_atten(self, atten):
    """
    Set the attenuation

    @param atten : attenuation in dB
    @type  atten : float
    """
    if atten < 0.0:
      self.logger.error("set_atten: attenuation can not be negative")
      return False
    if atten > self.max_atten:
      self.logger.error("set_atten: maximum attenuation is %f", self.max_atten)
      return False
    else:
      requested = self.max_gain - atten
      self.logger.debug("set_atten: %f dB attenuation is %f dB gain",
                        atten, requested)
      ctl_volts = self.spline(requested)
      self.logger.debug("set_atten: requires %f volts", ctl_volts)
      status = self.VS.setVoltage(ctl_volts)
      if status:
        self.atten = atten
      return status

  def __str__(self):
    return self._base_()+' "'+self.name+'"'

  def __repr__(self):
    return self._base_()+' "'+self.name+'"'

  def _base_(self):
    """
    String representing the class instance type
    """
    return str(type(self)).split()[-1].strip('>').strip("'").split('.')[-1]
  

# ---------------------------- module methods ---------------------------------

def get_splines(filename):
  """
  Get the spline interpolators and ranges of validity

  Spline interpolator foles are of the form::
    ( ( {'R1-18-E': <scipy.interpolate.interpolate.interp1d at 0xc1de90>,
         'R1-18-H': <scipy.interpolate.interpolate.interp1d at 0xc1d990>,
         ...
         'R2-26-E': <scipy.interpolate.interpolate.interp1d at 0xc1db90>,
         'R2-26-H': <scipy.interpolate.interpolate.interp1d at 0xc1d890>},
        {'R1-18-E': (-10.0, 0.8, 0.1),
         'R1-18-H': (-10.0, 0.8, 0.1),
          ...
         'R2-26-E': (-10.0, 0.8, 0.1),
         'R2-26-H': (-10.0, 0.8, 0.1)} ),
     ( {'R1-18-E': <scipy.interpolate.interpolate.interp1d at 0xc7d030>,
        'R1-18-H': <scipy.interpolate.interpolate.interp1d at 0xc74b90>,
        ...
        'R2-26-E': <scipy.interpolate.interpolate.interp1d at 0xc74d50>,
        'R2-26-H': <scipy.interpolate.interpolate.interp1d at 0xc74ab0>},
       {'R1-18-E': (-27.5, -8.1, 0.1),
        'R1-18-H': (-27.400000000000002, -7.800000000000001, 0.1),
        ...
        'R2-26-E': (-27.6, -9.200000000000001, 0.1),
        'R2-26-H': (-27.400000000000002, -9.200000000000001, 0.1) } ) )
  Each tuple has a dict of splines and a dict of valid ranges for the
  independent variable, which is control voltage in the first and attenuation
  in the second.

  @param fikename : full path to dill pickle file
  @type  filename : str

  @return: tuple of tuples of dicts
  """
  fd = open(filename,'rb')
  splines = pickle.load(fd)
  return splines
  