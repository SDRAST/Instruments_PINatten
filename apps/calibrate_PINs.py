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
    att[key] = P[key] -float(refs[index])
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
  legend(loc='lower left', numpoints=1)
  for key in keys:
    plot(V[key], att[key], ls='-', marker=column_marker(index),
         label=key)

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
  allkeys = V.keys()
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
  mylogger.setLevel(logging.DEBUG)
  
  if gethostname() == 'dss43wbdc2':
    ## Needed when data are to be acquired
    fe = get_device_server("FE_server-krx43", "crux")
    print "Feed 1:",fe.set_WBDC(13) # set feed 1 to sky
    print "Feed 2:",fe.set_WBDC(15) # set feed 2 to sky
    #print fe.set_WBDC(14) # set feed 1 to load
    #print fe.set_WBDC(16) # set feed 2 to load
    for pm in ['PM1', 'PM2', 'PM3', 'PM4']:
      # set PMs to dBm
      print fe.set_WBDC(400+int(pm[-1]))
    
  # this goes from mininum attenuation to manimum attenuation
  ctl_volts = [ -10,-9, -8, -7, -6, -5, -4, -3, -2, -1, -0.75, -0.5, -0.25,
                  0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

  if gethostname() == 'dss43wbdc2':
    # get data with direct WBDC control
    rx = WBDC2hwif('WBDC2')
    crossed = rx.get_Xswitch_state()
    if crossed:
      mylogger.warning(" cross-switch in set")
    pol_secs = {'R1-22': rx.pol_sec['R1-22'],
		'R2-22': rx.pol_sec['R2-22']}
    attenuators = {'R1-22-E': pol_secs['R1-22'].atten['R1-22-E'],
		   'R1-22-H': pol_secs['R1-22'].atten['R1-22-H'],
		   'R2-22-E': pol_secs['R2-22'].atten['R2-22-E'],
		   'R2-22-E': pol_secs['R2-22'].atten['R2-22-H']}
  
    pkeys = pol_secs.keys(); pkeys.sort()
    akeys = attenuators.keys(); akeys.sort()
    mylogger.debug(" pol section keys: %s", pkeys)
    mylogger.debug(" attenuator keys: %s", akeys)
  
    powers  = {} # dict of lists of measured powers
    for atn in akeys():
      powers[atn] = []
    for ctlV in ctl_volts:
      for atn in attenuators.keys():
	attenuators[atn].VS.setVoltage(ctlV)
      time.sleep(0.5)
      # read all the power meters
      response = fe.read_pms()
      data =  []
      for index in range(len(response)):
	key = akeys[index]
	powers[akeys[index]].append(response[index][2])
    
    for pm in ['PM1', 'PM2', 'PM3', 'PM4']:
      # set PMs to W
      print fe.set_WBDC(390+int(pm[-1]))
  elif gethostname() == 'kuiper':
    powers = NP.array(
      [[-27.577, -26.127, -27.643, -27.899],
       [-27.644, -26.21 , -27.719, -27.982],
       [-27.823, -26.422, -27.927, -28.206],
       [-28.305, -27.025, -28.514, -28.875],
       [-29.235, -28.197, -29.658, -30.176],
       [-30.379, -29.627, -31.047, -31.747],
       [-31.358, -30.825, -32.207, -33.027],
       [-32.123, -31.721, -33.035, -33.925],
       [-32.883, -32.534, -33.749, -34.67 ],
       [-34.136, -33.775, -34.774, -35.684],
       [-34.708, -34.341, -35.236, -36.126],
       [-35.556, -35.18 , -35.937, -36.794],
       [-36.948, -36.591, -37.14 , -37.932],
       [-39.593, -39.331, -39.663, -40.311],
       [-41.351, -41.138, -41.444, -41.984],
       [-43.543, -43.287, -43.753, -44.165],
       [-45.362, -44.936, -45.789, -46.066],
       [-46.156, -45.595, -46.66 , -46.835],
       [-46.502, -45.834, -46.956, -47.099],
       [-46.632, -45.942, -47.078, -47.216],
       [-46.69 , -45.995, -47.139, -47.269],
       [-46.731, -46.025, -47.163, -47.293]])
  else:
    print "Need code for host", gethostname()
  
  cv = NP.array([ctl_volts]*4)
  P = powers.transpose()
  # re-zero the data
  att = rezero_data(cv, P, powers[0])

  # Now do the fitting:
  att_spline,  V_sample_range   = get_splines(cv, P, range(4))
  ctlV_spline, att_sample_range = get_splines(P, cv, range(4))

  # verify the fits
  v, dB    = interpolate(att_spline,  range(4), V_sample_range)
  db, ctlV = interpolate(ctlV_spline, range(4), att_sample_range)

  
  