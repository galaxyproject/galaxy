import subprocess
import sys
import os
import tempfile
import optparse
from random import randint

parser = optparse.OptionParser()
parser.add_option('-i',dest='inputs',action="append",type="string")
parser.add_option('-o',dest='output')
parser.add_option('-p',dest='pipeline')
parser.add_option('-n',dest='originalnames',action="append",type="string")
opts, args = parser.parse_args()

DEVNULL = open(os.devnull,'wb') #This is needed to supress ilastik error due to running CellProfiler in headless configuration
cp_path = os.environ['CP_PATH']
originalpath = os.getcwd()	
tempdirectory = tempfile.mkdtemp()
if(opts.pipeline == 'bcc'):
	#create output file within temporary subdirectory
	subprocess.call('mkdir '+tempdirectory+'/output',shell=True)
	os.chdir(cp_path)
	#read input files into current directory
	#the following for loop creates a symlink from galaxy's internal .dat file to the original filename (.tiff/png) that the pipeline expects 
	for filename,link in zip(opts.inputs,opts.originalnames):
		subprocess.call('ln -s '+filename+' '+tempdirectory+'/'+link, shell=True)
	subprocess.call('ln -s '+cp_path+'/bcc/* '+tempdirectory, shell=True)
	os.chdir(tempdirectory)
	subprocess.call('python createFileList.py '+tempdirectory,shell=True)
	subprocess.call('python makeHeadless.py',shell=True)
	subprocess.call('cellprofiler --do-not-fetch -c -p headless.cppipe -i '+tempdirectory+' -o '+tempdirectory+'/output --data-file imageList.csv',shell=True,stdout=DEVNULL,stderr=DEVNULL)
	subprocess.call('python curateTSV.py '+opts.output,shell=True)
	subprocess.call('rm headless.cppipe',shell=True)
	subprocess.call('python removeSymLinks.py',shell=True)
	os.chdir(originalpath)
	os.chdir(cp_path + '/bcc/')
	subprocess.call('rm -rf '+tempdirectory,shell=True)
elif(opts.pipeline == 'corl'):
	#create output file within temporary subdirectory
	subprocess.call('mkdir '+tempdirectory+'/output',shell=True)
	os.chdir(cp_path)
	#read input files into current directory
	#the following for loop creates a symlink from galaxy's internal .dat file to the original filename (.tiff/png) that the pipeline expects 
	for filename,link in zip(opts.inputs,opts.originalnames):
		subprocess.call('ln -s '+filename+' '+tempdirectory+'/'+link, shell=True)
	subprocess.call('ln -s '+cp_path+'/Corless_pipeline/* '+tempdirectory, shell=True)
	os.chdir(tempdirectory)
	subprocess.call('python createFileList.py '+tempdirectory,shell=True)
	subprocess.call('python fixOutput.py',shell=True)
	subprocess.call('cellprofiler --do-not-fetch -c -p headless.cppipe -i '+tempdirectory+' -o '+tempdirectory+'/output --file-list=filelist.txt',shell=True,stdout=DEVNULL,stderr=DEVNULL)
	subprocess.call('cp output/Test_exp3Image.csv '+opts.output,shell=True)
	subprocess.call('rm headless.cppipe',shell=True)
	os.chdir(originalpath)
	os.chdir(cp_path + '/Corless_pipeline/')
	subprocess.call('rm -rf '+tempdirectory,shell=True)
elif(opts.pipeline == 'taka'):
	#create output file within temporary subdirectory
	subprocess.call('mkdir '+tempdirectory+'/output',shell=True)
	os.chdir(cp_path)
	#read input files into current directory
	#the following for loop creates a symlink from galaxy's internal .dat file to the original filename (.tiff/png) that the pipeline expects 
	for filename,link in zip(opts.inputs,opts.originalnames):
		subprocess.call('ln -s '+filename+' '+tempdirectory+'/'+link, shell=True)
	subprocess.call('ln -s '+cp_path+'/Takahiro_Flow_Cytometry/* '+tempdirectory, shell=True)
	os.chdir(tempdirectory)
	subprocess.call('python createFileList.py '+tempdirectory,shell=True)
	subprocess.call('python fixOutput.py',shell=True)
	subprocess.call('cellprofiler --do-not-fetch -c -p headless.cppipe -i '+tempdirectory+' -o '+tempdirectory+'/output --file-list=filelist.txt',shell=True,stdout=DEVNULL,stderr=DEVNULL)
	subprocess.call('cp output/Image.cptoc '+opts.output,shell=True)
	subprocess.call('rm headless.cppipe',shell=True)
	os.chdir(originalpath)
	os.chdir(cp_path + '/Takahiro_Flow_Cytometry/')
	subprocess.call('rm -rf '+tempdirectory,shell=True)
elif(opts.pipeline == 'gray'):
	#create output file within temporary subdirectory
	subprocess.call('mkdir '+tempdirectory+'/output',shell=True)
	os.chdir(cp_path)
	#read input files into current directory
	#the following for loop creates a symlink from galaxy's internal .dat file to the original filename (.tiff/png) that the pipeline expects 
	for filename,link in zip(opts.inputs,opts.originalnames):
		subprocess.call('ln -s '+filename+' '+tempdirectory+'/'+link, shell=True)
	subprocess.call('ln -s '+cp_path+'/Gray_Lab/* '+tempdirectory, shell=True)
	os.chdir(tempdirectory)
	subprocess.call('python createFileList.py '+tempdirectory,shell=True)
	subprocess.call('python fixOutput.py',shell=True)
	subprocess.call('cellprofiler --do-not-fetch -c -p headless.cppipe -i '+tempdirectory+' -o '+tempdirectory+'/output --file-list=filelist.txt',shell=True,stdout=DEVNULL,stderr=DEVNULL)
	subprocess.call('cp output/Cells.txt '+opts.output,shell=True)
	subprocess.call('rm headless.cppipe',shell=True)
	os.chdir(originalpath)
	os.chdir(cp_path + '/Gray_Lab/')
	subprocess.call('rm -rf '+tempdirectory,shell=True)
elif(opts.pipeline == 'yant'):
	#create output file within temporary subdirectory
	subprocess.call('mkdir '+tempdirectory+'/output',shell=True)
	os.chdir(cp_path)
	#read input files into current directory
	#the following for loop creates a symlink from galaxy's internal .dat file to the original filename (.tiff/png) that the pipeline expects 
	for filename,link in zip(opts.inputs,opts.originalnames):
		subprocess.call('ln -s '+filename+' '+tempdirectory+'/'+link, shell=True)
	subprocess.call('ln -s '+cp_path+'/Yantasee_IF/* '+tempdirectory, shell=True)
	os.chdir(tempdirectory)
	subprocess.call('python createFileList.py '+tempdirectory,shell=True)
	subprocess.call('python fixOutput.py',shell=True)
	subprocess.call('cellprofiler --do-not-fetch -c -p headless.cppipe -i '+tempdirectory+' -o '+tempdirectory+'/output --file-list=filelist.txt',shell=True,stdout=DEVNULL,stderr=DEVNULL)
	subprocess.call('cp output/MyExpt_Image.csv '+opts.output,shell=True)
	subprocess.call('rm headless.cppipe',shell=True)
	os.chdir(originalpath)
	os.chdir(cp_path + '/Yantasee_IF/')
	subprocess.call('rm -rf '+tempdirectory,shell=True)
elif(opts.pipeline == 'yant2'):
	#create output file within temporary subdirectory
	subprocess.call('mkdir '+tempdirectory+'/output',shell=True)
	os.chdir(cp_path)
	#read input files into current directory
	#the following for loop creates a symlink from galaxy's internal .dat file to the original filename (.tiff/png) that the pipeline expects 
	for filename,link in zip(opts.inputs,opts.originalnames):
		subprocess.call('ln -s '+filename+' '+tempdirectory+'/'+link, shell=True)
	subprocess.call('ln -s '+cp_path+'/Yantasee_Blood_Vessel_ID/* '+tempdirectory, shell=True)
	os.chdir(tempdirectory)
	subprocess.call('python createFileList.py '+tempdirectory,shell=True)
	subprocess.call('python fixOutput.py',shell=True)
	subprocess.call('cellprofiler --do-not-fetch -c -p headless.cppipe -i '+tempdirectory+' -o '+tempdirectory+'/output --file-list=filelist.txt',shell=True,stdout=DEVNULL,stderr=DEVNULL)
	subprocess.call('cp output/MyExpt_Image.csv '+opts.output,shell=True)
	subprocess.call('rm headless.cppipe',shell=True)
	os.chdir(originalpath)
	os.chdir(cp_path + '/Yantasee_Blood_Vessel_ID/')
	subprocess.call('rm -rf '+tempdirectory,shell=True)
else:
	sys.stderr.write("Pipeline has not been implemented.")
	
