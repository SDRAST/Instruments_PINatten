"""
Obtains spline interpolators for the PIN diode attenuators

Data were obtained in the lab using a single frequency from a signal generator.

Creates a file with the spline interpolators and their ranges of validity.
There are splines for interpolating attenuation, given control voltage, and for
interpolating control voltage given attenuation. The file has::
  (att_spline, V_sample_range), (ctlV_spline, att_sample_range)
where sample_range consists of (start, stop, step).  All quantities are indexed
by data set number.
"""
from pylab import *
from scipy.interpolate import interp1d
import dill as pickle
import logging

packages_base = "/usr/local/lib/python2.7/DSN-Sci-packages/"
destination = packages_base+"MonitorControl/Receivers/WBDC/WBDC2/"

module_logger = logging.getLogger(__name__)

def load_data(filename):
  """
  Read data from a comma-separated data file

  Row 1 - reference (input) power level
  Row 2 - bias voltage
  Row 3 - total resistance in control voltage circuit
  Row 4 - serial number
  Row 5 - Receiver chain
  Row 6 - Frequency and polarization of channel
  Rows 7+ contain the data, with control voltage in column 0.

  @return: labels (dict of str), refpower, power, ctlvolts (dicts of float)
  """
  data =    loadtxt(filename, delimiter=',', skiprows=6)
  rxs =     loadtxt(filename, delimiter=',', skiprows=4, dtype=str)[0,:]
  headers = loadtxt(filename, delimiter=',', skiprows=5, dtype=str)[0,:]
  refs =    loadtxt(filename, delimiter=',', dtype=str)[0,1:]
  ncols = data.shape[1]
  V = {}
  att = {}
  labels = {}
  for column in range(1,ncols): # [1,2,3,4]
    rx = rxs[column + column%2 -1]
    label = rx+' '+headers[column]
    label = label.replace(' ','-')
    V[label] = data[:,0]
    att[label] = data[:,column]-float(refs[column-1])
  return V, att, refs

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
    module_logger.debug("get_splines: for %s between %f and %f",
                        index, minx, maxx)
    if x[index][0] > x[index][-1]:
      x[index] = x[index][::-1]
      y[index] = y[index][::-1]
    spl[index] = interp1d(x[index], y[index], kind='cubic')
    sample_range[index] = sampling_points(minx,maxx)
  return spl, sample_range
  
def sampling_points(vmin, vmax, vstep=None):
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
  slopes = {}
  for index in indices:
    slopes[index] = (db[index][1:]-db[index][:-1])/Vstep
  return slopes

#----------------------- functions for plotting results -----------------------

colors = ['b','g','r','c','m','y','k']

def column_marker(column):
  if (column)//7 == 0:
    marker = 'x'
  elif (column)//7 == 1:
    marker = '+'
  else:
    marker = 'd'
  return marker

def plot_data(V, att):
  keys = V.keys()
  keys.sort()
  for key in keys:
    index = keys.index(key)
    #att[key] = P[key] -float(refs[index])
    plot(V[key], att[key], ls='-', marker=column_marker(index),
         label=key)
  grid()
  xlim(-13,1)
  xlabel('Control Volts (V)')
  ylabel('Insertion Loss (dB)')
  title("Attenuation Curves")
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
  # get the data
  V, att, refs = load_data('wbdc2_data.csv')
  keys = V.keys()
  keys.sort()
  # plot the data
  figure(1)
  plot_data(V, att)
  
  # fit the data
  att_spline,  V_sample_range   = get_splines(V, att, keys)
  ctlV_spline, att_sample_range = get_splines(att, V, keys)

  # save the data
  splfile = open(destination+"splines-lab.pkl","wb")
  pickle.dump(((att_spline, V_sample_range),
               (ctlV_spline,att_sample_range)), splfile)
  splfile.close()

  # verify the fits
  v, dB    = interpolate(att_spline,  ['R1-18-E','R2-20-H','R1-24-H'],
                         V_sample_range)
  db, ctlV = interpolate(ctlV_spline, ['R1-18-E','R2-20-H','R1-24-H'],
                         att_sample_range)
  
  # plot the fits
  figure(2)
  plot_fit(V, att, v, dB, keys, ['R1-18-E','R2-20-H','R1-24-H'],
           toplabel='Cubic spline interpolation on dB')
  figure(3)
  plot_fit(V, att, ctlV, db, keys, ['R1-18-E','R2-20-H','R1-24-H'],
           toplabel='Cubic spline interpolation on V')
  # get the slopes
  att_gradient = get_derivative(dB,['R1-18-E','R2-20-H','R1-24-H'])
  # analyze the slopes
  figure(4)
  plot_gradients(v, att_gradient, ['R1-18-E','R2-20-H','R1-24-H'])
  show()

