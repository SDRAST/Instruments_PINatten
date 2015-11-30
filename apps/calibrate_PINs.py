"""
Calibrate PIN diode attenuators

This is for the canonical TAMS  22F1EL, 22F1HU, 22F2EU and 22F2HL configuration
which is 1: F1P1 21-22, 2: F1P2 22-23, 3: F2P1 22-23 and 4: F2P2 21-22, shown
here::
                         .---.
       .----.      +--I--|\ /|--IF1--PM1
 R1E --|----|--P1--M     | X |
       |    |      +--Q--|/ \|--IF2
       |    |            '---' 
       |    |            .---.
       |    |      +--I--|\ /|--IF1
 R1H --|----|--P2--M     | X |
       '----'      +--Q--|/ \|--IF2--PM2
                         '---'
                          
                         .---.
       .----.      +--I--|\ /|--IF1--PM3
 R2E --|----|--P1--M     | X |
       |    |      +--Q--|/ \|--IF2
       |    |            '---' 
       |    |            .---.
       |    |      +--I--|\ /|--IF1
 R2H --|----|--P2--M     | X |
       '----'      +--Q--|/ \|--IF2--PM4
                         '---'
So the WBDC2 configuration is::
* cross-over switch (not shown) uncrossed (default).
* polarization hybrids bypassed (default).
* IF hybrids crossed (default).
"""
import logging
import numpy as NP
import time
import sys
from pylab import *
from scipy.interpolate import interp1d
import dill as pickle

from support.pyro import get_device_server

from MonitorControl import ClassInstance
from MonitorControl.Receivers.WBDC.WBDC2.WBDC2hwif import WBDC2hwif

module_logger = logging.getLogger(__name__)

def get_calibration_data(Pinatten, pm,
                           limits=None,
                           bias=None,
                           save=True,
                           filename=None,
                           show_progress=False):
  """
  Obtains measured power as a function of control voltage and bias voltage

  This gets the data needed to calibrate a PIN diode attenuator
  between 'limits' ( = (lower,upper) ) control voltages.
  'bias' is an optional list of bias voltages.

  Generates these public attributes:
    - Pinatten.bias_list
    - Pinatten.volts
    - Pinatten.pwrs

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
  if True:
    # just to compensate for old indentation
    pwrs = {}
    if bias == None:
      Pinatten.bias_list = [2, 2.5, 3, 3.5, 4]
    elif type(bias) == float or type(bias) == int:
      Pinatten.bias_list = [bias]
    else:
      Pinatten.bias_list = bias
    if limits == None:
      minV, maxV = -5, 1.75
    else:
      # arrange for 0.25 V steps
      minV = round(limits[0]*4)/4.
      maxV = round(limits[1]*4)/4.
    num_steps = int((maxV - minV)/.25)+1
    Pinatten.volts = NP.linspace(minV,maxV,num_steps)
    for bias in Pinatten.bias_list:
      if show_progress:
        print "Doing bias of",bias,"V",
      Pinatten.pwrs[bias] = []
      for volt in Pinatten.volts:
        Pinatten.setVoltages([bias,volt])
        if show_progress:
          print ".",
          sys.stdout.flush()
        # Give the power meter time to range and settle
        time.sleep(1)
        Pinatten.pwrs[bias].append(float(pm.read().strip()))
      if show_progress:
        print

    text = "# Attenuator "+str(Pinatten.ID)+"\n"
    text += "# Biases: "+str(Pinatten.bias_list)+"\n"
    for index in range(len(Pinatten.volts)):
      text += ("%5.2f " % Pinatten.volts[index])
      for bias in Pinatten.bias_list:
        text += ("  %7.3f" % Pinatten.pwrs[bias][index])+"\n"
    if filename != None:
      if filename:
        datafile = open(filename,"w")
      else:
        datafile = open("atten-"+str(Pinatten.ID)+".txt","w")
      datafile.write(text)
      datafile.close()
    return text

def get_atten_IDs(filename):
  """
  Read data from a comma-separated data file

  Row 1 - reference (input) power level
  Row 2 - bias voltage
  Row 3 - total resistance in control voltage circuit
  Row 4 - serial number
  Row 5 - Receiver chain
  Row 6 - Frequency and polarization of channel
  Rows 7+ contain the data, with control voltage in column 0.

  @return:  power (dict of floats), ctlvolts (dict of floats), refpower (list of str)
  """
  serialnos = loadtxt(filename, delimiter=',', skiprows=3, dtype=str)[0,1:]
  rxs =       loadtxt(filename, delimiter=',', skiprows=4, dtype=str)[0,1:]
  headers =   loadtxt(filename, delimiter=',', skiprows=5, dtype=str)[0,1:]
  ID = {}
  for index in range(0, len(headers), 2):
    chanIDa = rxs[index]+'-'+headers[index].replace(' ','-')
    chanIDb = rxs[index]+'-'+headers[index+1].replace(' ','-')
    ID[chanIDa] = serialnos[index]+'A'
    ID[chanIDb] = serialnos[index]+'B'
  return ID

#---------------------------- functions for obtaining splines -----------------

def get_splines(x, y, indices):
  """
  Get spline interpolator and limits on its validity

  @param x : dict of X values
  @type  x : dict of float

  @param y : dict of Y values
  @type  y : dict of float

  @param indices : keys of the X and Y arrays to be fitted
  @type  indices : type of X and Y keys

  @return: dict of interp1d instances, sample points (min, max, step)
  """
  spl = {}
  sample_range = {}
  for index in indices:
    minx = x[index].min()
    maxx = x[index].max()
    module_logger.debug("get_splines: for %d between %f and %f",
                        index, minx, maxx)
    if x[index][0] > x[index][-1]:
      module_logger.debug("inverting data order so x[0] < x[-1]")
      x[index] = x[index][::-1]
      y[index] = y[index][::-1]
    module_logger.debug("%s", x[index])
    spl[index] = interp1d(x[index], y[index], kind='cubic')
    sample_range[index] = sampling_points(minx,maxx)
  return spl, sample_range
  
def sampling_points(vmin, vmax, vstep=None):
  """
  Create a nicely spaced set of sampling points at which to evaluate
  
  @param vmin : minimum abscissa
  @type  vmin : float
  
  @param vmax : maximum abscissa
  @type  vmax : float
  
  @param vstep : optional abscissa step size
  @type  vstep : float or None
  
  @return: tuple
  """
  if vstep == None:
    vrange = float(vmax)-float(vmin)
    module_logger.debug("sampling_points: range=%f", vrange)
    appr_vstep = abs(vrange/100.)
    module_logger.debug("sampling_points: appr. step = %f", appr_vstep)
    vstep_order_of_magnitude = int(floor(log10(appr_vstep)))
    module_logger.debug("sampling_points: order of magnitude = %d",
                        vstep_order_of_magnitude)
    vstep = pow(10.,vstep_order_of_magnitude)
    module_logger.debug("sampling_points: step=%f", vstep)
  i_start = int(vmin/vstep)
  i_stop = int(vmax/vstep)
  module_logger.debug("sampling points: multiplier from %d to %d",
                      i_start,i_stop)
  if i_stop > i_start:
    if i_start*vstep < vmin:
      i_start = i_start+1
    if i_stop*vstep > vmax:
      i_stop = i_stop-1
    return i_start*vstep, i_stop*vstep, vstep
  else:
    if i_stop*vstep < vmax:
      i_stop = i_stop+1
    return i_start*vstep, i_stop*vstep, -vstep
  
def interpolate(att_spline, indices, range_info=None):
  """
  Interpolate a dict of splines over their ranges

  @param att_spline : dict of spline interpolators
  @type  att_spline : dict of interp1d instances

  @param indices : keys of the X and Y arrays to be fitted
  @type  indices : type of X and Y keys

  @param range_info : (start, stop, step); default: (-10, 0.5, 0.1)
  @type  range_info : dict of tuples of floats
  @return: dict of interp1d instances, sample points (min, max, step)
  """
  v = {}
  db = {}
  module_logger.debug("interpolate: ranges are %s", range_info)
  for index in indices:
    if range_info:
      v[index] = arange(*range_info[index])
    else:
      v[index] = arange(-10, 0.5, 0.1)
    module_logger.debug("interpolate: %s at \n%s", index, v[index])
    db[index] = att_spline[index](v[index])
  return v, db

def get_derivative(db, indices, Vstep=0.1):
  """
  Gets the derivatives of a set of vectors
  """
  slopes = {}
  for index in indices:
    slopes[index] = (db[index][1:]-db[index][:-1])/Vstep
  return slopes

#----------------------- functions for plotting results -----------------------

colors = ['b','g','r','c','m','y','k']

def column_marker(column):
  """
  Unique markers modulo 7
  """
  if (column)//7 == 0:
    marker = 'x'
  elif (column)//7 == 1:
    marker = '+'
  else:
    marker = 'd'
  return marker

def rezero_data(V, P, refs):
  """
  Plot measured data
  """
  att = {}
  keys = V.keys()
  keys.sort()
  for key in keys:
    index = keys.index(key)
    att[key] = []
    for pwr in P[key]:
      att[key].append(pwr - float(refs[index]))
    att[key] = NP.array(att[key])
  return att

def plot_data(V, P, refs):
  """
  Plot measured data
  """
  grid()
  xlim(-13,1)
  xlabel('Control Volts (V)')
  ylabel('Insertion Loss (dB)')
  title("Attenuation Curves")
  keys = V.keys()
  keys.sort()
  for key in keys:
    index = keys.index(key)
    plot(V[key], att[key], ls='-', marker=column_marker(index),
         label=key)
  legend(loc='lower left', numpoints=1)
  
def plot_fit(V, att, v, db, labels, keys, Vstep=0.1, toplabel=""):
  # plot data
  allkeys = V.keys()
  allkeys.sort()
  for key in keys:
    index = allkeys.index(key)
    plot(V[key], att[key], color=colors[index % 7],
         marker=column_marker(index), ls='', label=key)
  # plot fits
  for key in keys:
    index = allkeys.index(key)
    plot(v[key], db[key],  color=colors[index % 7], ls='-')
  grid()
  legend(numpoints=1)
  xlabel('Control Volts (V)')
  ylabel('Insertion Loss (dB)')
  title(toplabel) # title('Cubic spline interpolation on dB')                                        #!

def plot_gradients(v, gradient, keys):
  """
  """
  allkeys = v.keys()
  allkeys.sort()
  for key in keys:
    index = allkeys.index(key)
    plot(v[key][1:], gradient[key], color=colors[index % 7],
         marker=column_marker(index), ls='-', label=key)
  grid()
  xlabel('Control Volts (V)')
  ylabel('Insertion Loss Gradient (dB/V)')
  title('Attenuation interpolation')
  legend(loc='lower left')


 
if __name__ == "__main__":
  from socket import gethostname
  logging.basicConfig(level=logging.WARNING)
  mylogger = logging.getLogger()
  mylogger.setLevel(logging.INFO)
  
  if gethostname() == 'dss43wbdc2':
    ## Needed when data are to be acquired
    fe = get_device_server("FE_server-krx43", "crux")
    print "Feed 1 load is:",fe.set_WBDC(13) # set feed 1 to sky
    print "Feed 2 load is:",fe.set_WBDC(15) # set feed 2 to sky
    #print fe.set_WBDC(14) # set feed 1 to load
    #print fe.set_WBDC(16) # set feed 2 to load
    for pm in ['PM1', 'PM2', 'PM3', 'PM4']:
      # set PMs to dBm
      print fe.set_WBDC(400+int(pm[-1]))
    

  if gethostname() == 'dss43wbdc2':
    # get data with direct WBDC control
    rx = WBDC2hwif('WBDC2')
    crossed = rx.get_Xswitch_state()
    if crossed:
      mylogger.warning(" cross-switch in set")
    pol_secs = {'R1-22': rx.pol_sec['R1-22'], 'R2-22': rx.pol_sec['R2-22']}
    attenuators = {
       'R1-22-E': pol_secs['R1-22'].atten['R1-22-E'],
		   'R1-22-H': pol_secs['R1-22'].atten['R1-22-H'],
		   'R2-22-E': pol_secs['R2-22'].atten['R2-22-E'],
		   'R2-22-H': pol_secs['R2-22'].atten['R2-22-H']}
  
    pkeys = pol_secs.keys(); pkeys.sort()
    akeys = attenuators.keys(); akeys.sort()
    mylogger.debug(" pol section keys: %s", pkeys)
    mylogger.debug(" attenuator keys: %s", akeys)
  
    # this goes from mininum attenuation to manimum attenuation
    ctl_volts = range(-10,0) + list(NP.arange(-0.9,0,0.1)) \
                             + list(NP.arange(0,0.8,0.05))
    powers  = {} # dict of lists of measured powers
    for atn in akeys:
      powers[atn] = []
    for ctlV in ctl_volts:
      for atn in akeys:
	      attenuators[atn].VS.setVoltage(ctlV)
      time.sleep(0.5)
      # read all the power meters
      response = fe.read_pms()
      data =  []
      for index in range(len(response)):
	      powers[akeys[index]].append(response[index][2])
    print powers
 
    for pm in ['PM1', 'PM2', 'PM3', 'PM4']:
      # set PMs to W
      print fe.set_WBDC(390+int(pm[-1]))
  elif gethostname() == 'kuiper':
    # this goes from mininum attenuation to manimum attenuation
    ctl_volts = [ -10,  -9,  -8, -7, -6, -5, -4, -3, -2, -1, -0.75, -0.5, -0.25,
                    0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    powers = {
    'R2-22-E': [-27.31599, -27.395,   -27.59499, -28.17099, -29.297,   -30.69099,
                -31.863,   -32.704,   -33.42099, -34.451,   -34.91199, -35.613,
                -36.813,   -39.328,   -41.103,   -43.40599, -45.441,   -46.31600,
                -46.61099, -46.740,   -46.79399, -46.81799],
    'R1-22-E': [-27.341,   -27.414,   -27.581,   -28.047,   -28.959,   -30.099,
                -31.091,   -31.875,   -32.64399, -33.90899, -34.487,   -35.347,
                -36.749,   -39.39999, -41.154,   -43.32699, -45.134,   -45.92799,
                -46.234,   -46.39399, -46.44299, -46.47399],
    'R1-22-H': [-25.696,   -25.77,    -25.974,   -26.550,   -27.69999, -29.13299,
                -30.349,   -31.263,   -32.090,   -33.34499, -33.91599, -34.762,
                -36.17499, -38.92399, -40.713,   -42.834,   -44.47099, -45.130,
                -45.368,   -45.47599, -45.527,   -45.54299],
    'R2-22-H': [-27.67399, -27.75499, -27.972,   -28.62399, -29.919,   -31.47899,
                -32.771,   -33.68699, -34.438,   -35.468,   -35.91599, -36.591,
                -37.74499, -40.136,   -41.81199, -43.966,   -45.856,   -46.622,
                -46.892,   -46.997,   -47.058,   -47.088]}
  else:
    print "Need code for host", gethostname()
    sys.exit()

  cv = {}
  pkeys = powers.keys()
  pkeys.sort()
  refs = []
  for key in pkeys:
    cv[key] = NP.array(ctl_volts)
    refs.append(powers[key][0])
  ID = get_atten_IDs('wbdc2_data.csv')

  # re-zero the data
  att = rezero_data(cv, powers, refs)

  # Now do the fitting:
  att_spline,  V_sample_range   = get_splines(cv, att, pkeys)
  ctlV_spline, att_sample_range = get_splines(att, cv, pkeys)

  # verify the fits
  v, dB    = interpolate(att_spline,  pkeys, V_sample_range)
  db, ctlV = interpolate(ctlV_spline, pkeys, att_sample_range)

  # save the data
  module_path = "/usr/local/lib/python2.7/DSN-Sci-packages/MonitorControl/Receivers/WBDC/WBDC2/"
  splfile = open(module_path+"splines.pkl","wb")
  pickle.dump(((att_spline, V_sample_range),
               (ctlV_spline,att_sample_range)), splfile)
  splfile.close()

  # plot the data
  figure(1)
  plot_data(cv, powers, refs)
  xlim(-10,+1)

  # plot the fits
  figure(2)
  plot_fit(cv, att, v, dB, pkeys, pkeys,
           toplabel='Cubic spline interpolation on dB')
  figure(3)
  plot_fit(cv, att, ctlV, db, pkeys, pkeys,
           toplabel='Cubic spline interpolation on V')

  # get the slopes
  att_gradient = get_derivative(dB, pkeys)
  # analyze the slopes
  figure(4)
  plot_gradients(v, att_gradient, pkeys)

  show()
  
  
