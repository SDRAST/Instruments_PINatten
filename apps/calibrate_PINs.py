"""
Calibrate PIN diode attenuators


"""
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
