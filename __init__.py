"""
PIN diode attenuator class and calibration methods
"""
import logging

from Electronics.Interfaces.LabJack import LJTickDAC
from Electronics.Instruments import Attenuator

module_logger = logging.getLogger(__name__)

class PINattenuator(Attenuator):
  """
  Voltage-controlled PIN diode attenuator for WBDC

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
  def __init__(self, name, voltage_source, IOchan):
    """
    """
    self.name = name
    self.VS = voltage_source
    mylogger = logging.getLogger(module_logger.name+".PINattenuator")
    mylogger.debug("Initializing attenuator %s with voltage source %s",LabJack.localID
    self.pwrs = {}
    self.bias = 3.0
    # The IDs match the WBDC receiver channels
    if pin == 0:
      self.ID = 1
      self.coefs = NP.array([2.24305829e-03,  3.47608278e-02,
                             1.91564653e-01,  3.57628078e-01,
                            -4.44852926e-01, -2.43563471e+00,
                            -4.14345128,     -8.16101008])
      self.lower = -5.0
      self.upper =  1.75
    elif pin == 2:
      self.ID = 2
      self.coefs = NP.array([1.97246882e-03,  3.15527700e-02,
                             1.80115477e-01,  3.54211343e-01,
                            -3.82845997e-01, -2.30612599,
                            -4.14205717,     -8.34552823    ])
      self.lower = -5.0
      self.upper =  1.75
    elif pin == 4:
      self.ID = 3
      self.coefs = NP.array([2.06521060e-03,  3.27308482e-02,
                             1.84436385e-01,  3.52212701e-01,
                            -4.20502519e-01,  -2.32719384,
                            -4.05112656,      -8.39222065   ])
      self.lower = -5.0
      self.upper =  1.75
    elif pin == 6:
      if LabJack.localID == 2:
        self.ID = 4
        self.coefs = NP.array([2.13996316e-03,  3.34458388e-02,
                               1.85709249e-01,  3.46131441e-01,
                              -4.43162863e-01, -2.31329518,
                              -3.91949192,     -8.55680332])
        self.lower = -5.0
        self.upper =  1.75
      elif LabJack.localID == 3:
        self.ID = 5
        self.coefs = NP.array([-1.11465757e-04, -9.83309141e-04,
                                1.73887763e-03,  2.92728140e-02,
                                3.68747270e-02, -4.86525897e-02,
                               -4.63506048e-01,  -2.74735018])
        self.lower = -6.0
        self.upper =  1.75
    else:
      self.ID = None
    self.volts = [self.lower,self.upper]

  def set_default(self):
    """
    This sets all attenuators to 5 dB, based on a previous
    calibration.
    """
    if self.ID == 1:
      self.setVoltages([3.0,-0.370])
    elif self.ID == 2:
      self.setVoltages([3.0,-0.539])
    elif self.ID == 3:
      self.setVoltages([3.0,-0.490])
    elif self.ID == 4:
      self.setVoltages([3.0,-0.724])
    elif self.ID == 5:
      self.setVoltages([3.0,-0.5])

  def get_calibration_data(self, pm,
                           limits=None,
                           bias=None,
                           save=True,
                           filename=None,
                           show_progress=False):
    """
    Obtains measured power as a function of control voltage

    This gets the data needed to calibrate a PIN diode attenuator
    between 'limits' ( = (lower,upper) ) control voltages.
    'bias' is an optional list of bias voltages.

    Generates these public attributes:
      - self.bias_list
      - self.volts
      - self.pwrs

    @type pm : Gpib.Gpib instance
    @param pm : power meter for the power readings

    @type limits : tuple of float
    @param limits : (lower test voltage, upper test voltage). If limits
    is not provided, (-5,1.75) will be used.

    @type bias : list of float
    @param bias : bias voltages for the PIN diode. ints are acceptable.
    If bias is not a list but a number it will be converted to a list.
    So far, the diodes tested have a best bias of 3.0 V.

    @type save : bool
    @param save : True to save data to a file

    @type filename : str
    @param filename : name of text file for data.  If it is not provided
    the data will not be saved.  If it is "", the file will be in the
    current directory with a default name

    @return: dictionary of control voltage lists, dictionary of measured
    powers, both indexed by bias voltage, and a list of biases.
    """
    pwrs = {}
    if bias == None:
      self.bias_list = [2, 2.5, 3, 3.5, 4]
    elif type(bias) == float or type(bias) == int:
      self.bias_list = [bias]
    else:
      self.bias_list = bias
    if limits == None:
      minV, maxV = -5, 1.75
    else:
      # arrange for 0.25 V steps
      minV = round(limits[0]*4)/4.
      maxV = round(limits[1]*4)/4.
    num_steps = int((maxV - minV)/.25)+1
    self.volts = NP.linspace(minV,maxV,num_steps)
    for bias in self.bias_list:
      if show_progress:
        print "Doing bias of",bias,"V",
      self.pwrs[bias] = []
      for volt in self.volts:
        self.setVoltages([bias,volt])
        if show_progress:
          print ".",
          sys.stdout.flush()
        # Give the power meter time to range and settle
        time.sleep(1)
        self.pwrs[bias].append(float(pm.read().strip()))
      if show_progress:
        print

    text = "# Attenuator "+str(self.ID)+"\n"
    text += "# Biases: "+str(self.bias_list)+"\n"
    for index in range(len(self.volts)):
      text += ("%5.2f " % self.volts[index])
      for bias in self.bias_list:
        text += ("  %7.3f" % self.pwrs[bias][index])+"\n"
    if filename != None:
      if filename:
        datafile = open(filename,"w")
      else:
        datafile = open("atten-"+str(self.ID)+".txt","w")
      datafile.write(text)
      datafile.close()
    return text

  def controlVoltage(self,pwr):
    """
    Compute control voltage for a given attenuation

    @return: float control voltage V
    """
    function = scipy.poly1d(self.coefs)
    minV = self.volts[0]
    maxV = self.volts[-1]
    return scipy.optimize.bisect(function-pwr,minV,maxV)

  def set_atten(self,atten):
    """
    Set the attenuation


    """
    if atten > 0.0:
      atten *= -1.
    if atten > 15:
      raise "Too much attenuation requested"
    else:
      volt = self.controlVoltage(atten)
      self.setVoltages([self.bias,volt])

  def useful_range(self,polycoefs):
    """
    Report minimum and maximum measurable attenuation.

    @type polycoefs : numpy array of float
    @param polycoefs : polynomial coefficients
    """
    function = scipy.poly1d(polycoefs)
    return Math.ceil(function(self.volts[-1])*10)/10, \
           Math.floor(function(self.volts[0])*10)/10

  def atten(self,polycoefs,controlV):
    """
    @type polycoefs : numpy array of float
    @param polycoefs : polynomial coefficients

    @type controlV : float
    @param controlV : control voltage (V)
    """
    return function - scipy.poly1d(polycoefs)(controlV)

  def fit_calibration_data(self):
    """
    Fit the power vs voltage curves taken with self.get_calibration_data().

    Generates these public attributes:
      - bias
      - coefs
      - lower
      - upper
      - atten_table
    """
    pwr_range = 0
    for bias in self.bias_list:
      polycoefs = scipy.polyfit(self.volts, self.pwrs[bias], 7)
      yfit = scipy.polyval(polycoefs,self.volts)
      lower,upper = self.useful_range(polycoefs)
      if (upper-lower) > pwr_range:
        pwr_range = upper-lower
        best_coefs = polycoefs
        self.coefs = scipy.polyfit(self.volts,
                                   NP.array(self.pwrs[bias])-upper,
                                   7)
        best_lower, best_upper = lower, upper
        self.bias = self.bias_list
    if pwr_range:
      # self.bias should now have the best bias (if there was more than
      # one to try, and a set of polynomial coefficients
      self.lower = best_lower
      self.upper = best_upper
      self.atten_table = {}
      for pwr in NP.arange(self.lower,self.upper,1):
        ctrlVolts = self.controlVoltage(pwr-self.upper)
        self.atten_table[self.upper-pwr] = ctrlVolts
      self.atten_table[0] = self.controlVoltage(0)
      return True
    else:
      return False

