#!/usr/bin/env python2.7
import os 
import sys 
import shutil 
import argparse 
import tempfile
import csv 
import json 
import urllib2 
import exceptions

#Printing error msgs
def stop_err( msg ):
   sys.stderr.write( '%s\n' % msg )
   sys.exit()

# entry point to the command line app, parses arguments and checks for errors. 
def civic_reader():
  try:
    # command line parameters and defaults
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_file", help="input file (assumed to be tab separated MAF format); defaults to stdin", default="-" )
    parser.add_argument("-o", "--output_file", help="output file; defaults to stdout", default="-" )
    parser.add_argument("-c", "--host", help="url of reference civic host (default: %(default)s)", default="civic.genome.wustl.edu"  )
    parser.add_argument("-col", "--entrez_id_column", help="column in the input file that contains the entrez id. Defaults to 1 (0 based)", default=1,  type=int )
    args = parser.parse_args()

    read(
      args.input_file,
      args.output_file,
      args.host,
      args.entrez_id_column
    )
  except exceptions.SystemExit as e:
    pass
  except:
    sys.stderr.write("Unexpected error:{}\n".format(sys.exc_info()[0]))
    sys.stderr.write("Parameters: input_file({}),output_file({}), host({}), entrez_id_column({})\n"
      .format( args.input_file,
      args.output_file,
      args.host,
      args.entrez_id_column)
    )
    raise

# Main entry point to the command line app, re-raises any exceptions amd processes the input and generates the table.
def read(input_file,output_file, host,entrez_id_column):
  """
  Reads a MAF file, calls CIViC api and render table.
  """  
  line_count = 0
  #process input file 
  if input_file == '-':
    sys.stderr.write('reading from stdin\n')

  #setup temporary output file 
  tmp_dir = tempfile.mkdtemp( dir='.')
  tmp_file = tempfile.NamedTemporaryFile( dir=tmp_dir )
  tmp = tmp_file.name
  tmp_file.close()
  #write to the temp file and copy over to the output_file once done
  if output_file != '-':
    #sys.stderr.write("writing to " + tmp +"\n")
    sys.stdout.write("writing to " + tmp +"\n")
    sys.stdout = open(tmp, 'w')
  shutil.move( tmp, output_file )
  # cleanup temp files
  if os.path.exists( tmp_dir ):
    shutil.rmtree( tmp_dir )
  
  try:  
    with open(input_file, 'r') if input_file != '-' else sys.stdin as tsv:
      for line in csv.reader(tsv,delimiter='\t'):
        line_count = line_count + 1
        # skip comments
        if  ((not line[0].strip().startswith('#')) and (not line[0].strip().startswith('Hugo')) ):
          # entrez_id assumed to be in second column
          if (len(line) > 2):
            civic_variant = civic_lookup(line[entrez_id_column], host)
            #  
            render(line,civic_variant,host,entrez_id_column)
  
  except Exception, e:
    # Read stderr so that it can be reported:
    tmp1 = tempfile.NamedTemporaryFile( dir='.' ).name
    print tmp1
    tmp_stderr = open( tmp1, 'rb' )
    stderr = ''
    buffsize = 1048576
    try:
       while True:
         stderr += tmp_stderr.read( buffsize )
         if not stderr or len( stderr ) % buffsize != 0:
            break
    except OverflowError:
       pass
    tmp_stderr.close()
    stop_err( 'Error running CIViC QRT.\n%s\n%s' % ( str( e ), stderr ) )


# render the output in a markdown format
render_header = True
def render(line,civic_variant,host,entrez_id_column):
  """
  Render the report line from MAF file + response from civic as markdown 
  """  
  global render_header

  (variant_name,drugs,link) = civic_properties(line,civic_variant,host,entrez_id_column)

  if (render_header):
     print("| {}  | {}  | {}  | {}  | {}  |\n"
           "|---  |---  |---  |---  |---  |".format('hugo_symbol','entrez_gene_id','CIViC variant name','drugs','link') )
     render_header = False
  print(  "| {}  | {}  | {}  | {}  | {}  |".format(line[0],line[1],variant_name,drugs,link) )
 

# get the properties of each line from civic
def civic_properties(line,response,host,entrez_id_column):
  """
  Given a line from the MAF file, and a response from civic, return (variant_name,drugs,link)
  """
  link = '' 
  drugs = ''
  variant_name = ''
  entrez_id = line[entrez_id_column]
  if (response):    
    link = "[civic gene](http://{}/#/events/genes/{}/summary)".format(host,entrez_id) 
  else:
    link = "_gene not found in civic_"
  expected_hgvs = "{}:{}-{} ({}->{})".format(  line[4]  , line[5] ,line[6],line[10],line[11] )
  for variant in response:
    variant_name = variant.get('name')
    for evidence_item in variant.get('evidence_items'):           
      if evidence_item.get('variant_hgvs') == expected_hgvs:
        if(evidence_item.get('drugs')):
          drugs = ",".join(list(map(lambda e:e.get('name'), evidence_item.get('drugs'))))
        if(evidence_item.get('drug')):
          drugs = evidence_item.get('drug')
        url = "http://{}/#/events/genes/{}/summary/variants/{}/summary/evidence/{}/summary".format(host,entrez_id,variant.get('id'),evidence_item.get('id'))
        link = "[civic variant]({})".format(url)      
  return [variant_name,drugs,link]


# get the data from civic
def civic_lookup(entrez_id, host):
  """This function calls civic for the entrez_id.
  """  
  #overriding system proxy settings using the 3 lines below
   #proxies = {'http': ''}
  proxy_handler = urllib2.ProxyHandler({})
  opener = urllib2.build_opener(proxy_handler)
  urllib2.install_opener(opener)
  url = "http://" + host + "/api/genes/" + entrez_id  + "/variants"
  try:
    return  json.loads(urllib2.urlopen(url).read().decode('utf-8'))
  except urllib2.HTTPError  as e :    
    if e.code != 404:
      print(e)
      raise e
  except urllib2.URLError  as e :    
    print("URLError:", e.reason)
    raise
  except:
    et, ei, tb = sys.exc_info()
    print("Unexpected error reading from "+host+":", et)
    raise ei
  return None

if __name__ == '__main__':   
  civic_reader()



  # for testing
  # read("resources/simple.maf","-","civic.genome.wustl.edu",1)


# WIP ..............................
# 
# http://grch37.ensembl.org/Homo_sapiens/Location/View?r=17:7578407-7578417
# http://grch37.ensembl.org/Homo_sapiens/Location/View?r=11:9608371-9608371

# def genenames_properties(response):
#   return response.get('docs')[0].get('ensembl_gene_id')


# def genenames_lookup(entrez_id):
#   url = "http://rest.genenames.org/fetch/entrez_id/{}".format(entrez_id)
#   try:
#     sys.stderr.write('g')
#     sys.stderr.flush()
#     req = urllib.request.Request(url)
#     req.add_header('Accept', 'application/json')
#     response = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
#     return  response.get('response') 
#   except urllib.error.HTTPError  as e :    
#     if e.code != 404:
#       print(e)
#       raise e
#   except urllib.error.URLError  as e :    
#     print("URLError:", e.reason)
#     raise
#   except:
#     print("Unexpected error:", sys.exc_info()[0])
#     raise
#   return None
