'''
Created on Jun 8, 2013

@author: crisr
'''
from __future__ import division, print_function, unicode_literals, absolute_import
import warnings
warnings.simplefilter('default',DeprecationWarning)

import os
import copy
import shutil
import Datas
import numpy as np
import ast
from BaseType import BaseType

class RavenInterface:
  '''this class is used as part of a code dictionary to specialize Model.Code for RAVEN'''
  def generateCommand(self,inputFiles,executable):
    '''seek which is which of the input files and generate According the running command'''
    if inputFiles[0].endswith('.i'): index = 0
    else: index = 1
    outputfile = 'out~'+os.path.split(inputFiles[index])[1].split('.')[0]
    executeCommand = (executable+' -i '+os.path.split(inputFiles[index])[1]+' Output/postprocessor_csv=true' + 
    ' Output/file_base='+ outputfile)
    return executeCommand,outputfile

  def appendLoadFileExtension(self,fileRoot):
    '''  '''
    return fileRoot + '.csv'
  def __createRestartFileName(self,prefix,suffix,parentID,end_ts):
    end_ts_str = str(end_ts)
    output_parent = prefix + '~' + parentID + '~' + suffix
    if(int(end_ts) <= 9999):
      n_zeros = 4 - len(end_ts_str)
      for i in range(n_zeros):
        end_ts_str = "0" + end_ts_str
    restart_file_base = output_parent + "_restart_" + end_ts_str 
    return restart_file_base
    
  def createNewInput(self,currentInputFiles,oriInputFiles,samplerType,**Kwargs):
    '''this generate a new input file depending on which sampler has been chosen'''
    import MOOSEparser
    newInputFiles = []
    self.samplersDictionary                          = {}
    self.samplersDictionary['MonteCarlo']            = self.MonteCarloForRAVEN
    self.samplersDictionary['EquallySpaced']         = self.EquallySpacedForRAVEN
    self.samplersDictionary['LatinHyperCube']        = self.LatinHyperCubeForRAVEN
    self.samplersDictionary['DynamicEventTree']      = self.DynamicEventTreeForRAVEN
    self.samplersDictionary['StochasticCollocation'] = self.StochasticCollocationForRAVEN
    if currentInputFiles[0].endswith('.i'): index = 0
    else: index = 1
    parser = MOOSEparser.MOOSEparser(currentInputFiles[index])
    modifDict = self.samplersDictionary[samplerType](**Kwargs)
    parser.modifyOrAdd(modifDict,False)
    temp = str(oriInputFiles[index][:])
    newInputFiles = copy.deepcopy(currentInputFiles)
    #TODO fix this? storing unwieldy amounts of data in 'prefix'
    if type(Kwargs['prefix']) in [str,type("")]:#Specifing string type for python 2 and 3
      newInputFiles[index] = copy.deepcopy(os.path.join(os.path.split(temp)[0],Kwargs['prefix']+"~"+os.path.split(temp)[1]))
    else:
      newInputFiles[index] = copy.deepcopy(os.path.join(os.path.split(temp)[0],str(Kwargs['prefix'][1][0])+"~"+os.path.split(temp)[1]))
    parser.printInput(newInputFiles[index])
    return newInputFiles

  def StochasticCollocationForRAVEN(self,**Kwargs):
    try: counter = Kwargs['prefix']
    except: raise IOError('a counter is (currently) needed for the StochColl sampler for RAVEN')
    #try: qps = Kwargs['qps']
    #except: raise IOError('a qp index is required for the StochColl sampler for RAVEN')
    listDict = []
    varValDict = Kwargs['vars'] #come in as a string of a list, need to re-list
    #print('\nvarValDict type:',type(varValDict),varValDict,'\n')
    #qps   = Kwargs['qps']
    #names = ast.literal_eval(varValDict.keys()) #turns string of list/tuple into list
    #vals = ast.literal_eval(var
    #qps   = ast.literal_eval(qps)
    for key in varValDict.keys():
      modifDict={}
      modifDict['name']=key.split(':')
      modifDict['value']=varValDict[key]
      #print('interface: set',key.split(':'),'to',varValDict[key])
      listDict.append(modifDict)
      del modifDict
    return listDict

  def MonteCarloForRAVEN(self,**Kwargs):
    try: counter = Kwargs['prefix']
    except: raise IOError('a counter is needed for the Monte Carlo sampler for RAVEN')
    try: init_seed = Kwargs['initial_seed']
    except: init_seed = 1
    
    listDict = []
    modifDict = {}
    modifDict['name'] = ['Distributions']
    RNG_seed = int(counter) + int(init_seed) - 1
    modifDict['RNG_seed'] = str(RNG_seed)
    listDict.append(modifDict)
    return listDict
  
  def DynamicEventTreeForRAVEN(self,**Kwargs):
    listDict = []
    # Check the initiator distributions and add the next threshold
    if 'initiator_distribution' in Kwargs.keys():
      for i in range(len(Kwargs['initiator_distribution'])):
        listDict.append({'name':['Distributions',Kwargs['initiator_distribution'][i]],'ProbabilityThreshold':Kwargs['PbThreshold'][i]})
    # add the initial time for this new branch calculation
    if 'start_time' in Kwargs.keys():
      if Kwargs['start_time'] != 'Initial':
        st_time = Kwargs['start_time']
        listDict.append({'name':['Executioner'],'start_time':st_time})
    # create the restart file name root from the parent branch calculation
    # in order to restart the calc from the last point in time
    if 'end_ts' in Kwargs.keys():
      if str(Kwargs['start_time']) != 'Initial':
        restart_file_base = self.__createRestartFileName(Kwargs['outfile'].split('~')[0],
                                                         Kwargs['outfile'].split('~')[1],
                                                         Kwargs['parent_id'],Kwargs['end_ts'])
        #end_ts_str = str(Kwargs['end_ts'])
        #if(Kwargs['end_ts'] <= 9999):
        #  n_zeros = 4 - len(end_ts_str)
        #  for i in range(n_zeros):
        #    end_ts_str = "0" + end_ts_str
        #splitted = Kwargs['outfile'].split('~')
        #output_parent = splitted[0] + '~' + Kwargs['parent_id'] + '~' + splitted[1]
        #restart_file_base = output_parent + "_restart_" + end_ts_str
        print('CODE INTERFACE: Restart file name base is "' + restart_file_base + '"')
        listDict.append({'name':['Executioner'],'restart_file_base':restart_file_base})
    # max simulation time (if present)
    if 'end_time' in Kwargs.keys():
      end_time = Kwargs['end_time']
      listDict.append({'name':['Executioner'],'end_time':end_time})
    # enable restarting
    listDict.append({'name':['Output'],'num_restart_files':1})
    # in this way we erase the whole block in order to neglect eventual older info
    # remember this "command" must be added before giving the info for refilling the block
    listDict.append({'name':['RestartInitialize'],'erase_block':True})
    # check and add the variables that have been changed by a distribution trigger
    # add them into the RestartInitialize block
    if 'branch_changed_param' in Kwargs.keys():
      if Kwargs['branch_changed_param'][0] not in ('None',b'None'): 
        for i in range(len(Kwargs['branch_changed_param'])):
          listDict.append({'name':['RestartInitialize',Kwargs['branch_changed_param'][i]],'value':Kwargs['branch_changed_param_value'][i]})
    return listDict  

  def EquallySpacedForRAVEN(self,**Kwargs):
    raise IOError('EquallySpacedForRAVEN not yet implemented')
    listDict = []
    return listDict
  
  def LatinHyperCubeForRAVEN(self,**Kwargs):
    raise IOError('LatinHyperCubeForRAVEN not yet implemented')
    listDict = []
    return listDict

class MooseBasedAppInterface:
  '''this class is used as part of a code dictionary to specialize Model.Code for RAVEN'''
  def generateCommand(self,inputFiles,executable):
    '''seek which is which of the input files and generate According the running command'''
    if inputFiles[0].endswith('.i'): index = 0
    else: index = 1
    outputfile = 'out~'+os.path.split(inputFiles[index])[1].split('.')[0]
    executeCommand = (executable+' -i '+os.path.split(inputFiles[index])[1]+' Output/postprocessor_csv=true' + 
    ' Output/file_base='+ outputfile)
    return executeCommand,outputfile

  def appendLoadFileExtension(self,fileRoot):
    '''  '''
    return fileRoot + '.csv'

  def createNewInput(self,currentInputFiles,oriInputFiles,samplerType,**Kwargs):
    '''this generate a new input file depending on which sampler has been chosen'''
    import MOOSEparser
    newInputFiles = []
    self.samplersDictionary                          = {}
    self.samplersDictionary['MonteCarlo']            = self.MonteCarloForMooseBasedApp
    self.samplersDictionary['EquallySpaced']         = self.EquallySpacedForMooseBasedApp
    self.samplersDictionary['LatinHyperCube']        = self.LatinHyperCubeForMooseBasedApp
    self.samplersDictionary['DynamicEventTree']      = self.DynamicEventTreeForMooseBasedApp
    self.samplersDictionary['StochasticCollocation'] = self.StochasticCollocationForMooseBasedApp
    if currentInputFiles[0].endswith('.i'): index = 0
    else: index = 1
    parser = MOOSEparser.MOOSEparser(currentInputFiles[index])
    modifDict = self.samplersDictionary[samplerType](**Kwargs)
    parser.modifyOrAdd(modifDict,False)
    temp = str(oriInputFiles[index][:])
    newInputFiles = copy.deepcopy(currentInputFiles)
    #TODO fix this? storing unwieldy amounts of data in 'prefix'
    if type(Kwargs['prefix']) in [str,type("")]:#Specifing string type for python 2 and 3
      newInputFiles[index] = copy.deepcopy(os.path.join(os.path.split(temp)[0],Kwargs['prefix']+"~"+os.path.split(temp)[1]))
    else:
      newInputFiles[index] = copy.deepcopy(os.path.join(os.path.split(temp)[0],str(Kwargs['prefix'][1][0])+"~"+os.path.split(temp)[1]))
    parser.printInput(newInputFiles[index])
    return newInputFiles

  def StochasticCollocationForMooseBasedApp(self,**Kwargs):
    raise IOError('StochasticCollocationForMooseBasedApp not yet implemented')
    listDict = []
    return listDict

  def MonteCarloForMooseBasedApp(self,**Kwargs):
    listDict = []
    modifDict = {}
    # the position in, eventually, a vector variable is not available yet...
    # the MOOSEparser needs to be modified in order to accept this variable type
    # for now the position (i.e. ':' at the end of a variable name) is discarded
    for var in Kwargs['sampledVars']:
        key = var.split(':')
        if len(key) > 1: position = key[1]
        else:            position = 1
        listDict.append({'name':key[0].split('|')[:-1],key[0].split('|')[-1]:Kwargs['sampledVars'][var],'position':position})
        listDict.append({'name':['Postprocessors',key[0]],'type':'Reporter'})
        listDict.append({'name':['Postprocessors',key[0]],'default':Kwargs['sampledVars'][var]})
        #print (listDict)
    return listDict
  
  def DynamicEventTreeForMooseBasedApp(self,**Kwargs):
    raise IOError('DynamicEventTreeForMooseBasedApp not yet implemented')
    listDict = []
    return listDict

  def EquallySpacedForMooseBasedApp(self,**Kwargs):
    raise IOError('EquallySpacedForMooseBasedApp not yet implemented')
    listDict = []
    return listDict
  
  def LatinHyperCubeForMooseBasedApp(self,**Kwargs):
    raise IOError('LatinHyperCubeForMooseBasedApp not yet implemented')
    listDict = []
    return listDict
  

class RelapInterface:
  '''this class is used a part of a code dictionary to specialize Model.Code for RELAP5-3D Version 4.0.3'''
  def generateCommand(self,inputFiles,executable):
    '''seek which is which of the input files and generate According the running command'''
    if inputFiles[0].endswith('.i'): index = 0
    else: index = 1
    outputfile = 'out~'+os.path.split(inputFiles[index])[1].split('.')[0]
    #   executeCommand will consist of a simple RELAP script that runs relap for inputfile
    #   extracts data and stores in csv file format
    executeCommand = (executable+' '+os.path.split(inputFiles[index])[1]+' ' + 
    outputfile)
    return executeCommand,outputfile

  def appendLoadFileExtension(self,fileRoot):
    '''  '''
    return fileRoot + '.csv'


  def createNewInput(self,currentInputFiles,oriInputFiles,samplerType,**Kwargs):
    '''this generate a new input file depending on which sampler is chosen'''
    import RELAPparser
    newInputFiles = []
    self.samplersDictionary                     = {}
    self.samplersDictionary['MonteCarlo']       = self.MonteCarloForRELAP
    self.samplersDictionary['EquallySpaced']    = self.EquallySpacedForRELAP
    self.samplersDictionary['LatinHyperCube']   = self.LatinHyperCubeForRELAP
    self.samplersDictionary['DynamicEventTree'] = self.DynamicEventTreeForRELAP
    if currentInputFiles[0].endswith('.i'): index = 0
    else: index = 1
    parser = RELAPparser.RELAPparser(currentInputFiles[index])
    modifDict = self.samplersDictionary[samplerType](**Kwargs)
    parser.modifyOrAdd(modifDict,True)
    temp = str(oriInputFiles[index][:])
    newInputFiles = copy.deepcopy(currentInputFiles)
    newInputFiles[index] = copy.deepcopy(os.path.join(os.path.split(temp)[0],Kwargs['prefix']+"~"+os.path.split(temp)[1]))
    parser.printInput(newInputFiles[index])
    return newInputFiles
    
  def MonteCarloForRELAP(self,**Kwargs):
    modifDict = {}
    for keys in Kwargs['sampledVars']:
      key = keys.split(':')
      try:    Kwargs['sampledVars'][keys]['position'] = int(key[1])
      except: Kwargs['sampledVars'][keys]['position'] = 0
      modifDict[key[0]]=Kwargs['sampledVars'][keys]
    return modifDict
    
  def DynamicEventTreeForRELAP(self,**Kwargs):
    raise IOError('DynamicEventTreeForRELAP not yet implemented')
    listDict = []
    return listDict

  def EquallySpacedForRELAP(self,**Kwargs):
    raise IOError('EquallySpacedForRAVEN not yet implemented')
    listDict = []
    return listDict
  
  def LatinHyperCubeForRELAP(self,**Kwargs):
    raise IOError('LatinHyperCubeForRAVEN not yet implemented')
    listDict = []
    return listDict

  
class ExternalTest:
  def generateCommand(self,inputFiles,executable):
    return '', ''

  def findOutputFile(self,command):
    return ''
  
def returnCodeInterface(Type):
  '''this allow to the code(model) class to interact with a specific
     code for which the interface is present in the CodeInterfaces module'''
  base = 'Code'
  codeInterfaceDict = {}
  codeInterfaceDict['RAVEN'        ] = RavenInterface
  codeInterfaceDict['MooseBasedApp'] = MooseBasedAppInterface
  codeInterfaceDict['ExternalTest' ] = ExternalTest
  codeInterfaceDict['RELAP5'       ] = RelapInterface
  try: return codeInterfaceDict[Type]()
  except: raise NameError('not known '+base+' type '+Type)

