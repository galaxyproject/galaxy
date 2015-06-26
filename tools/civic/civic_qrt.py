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

#Overriding system proxies for json object loads
def proxy_handler():
   proxy_handler = urllib2.ProxyHandler({})
   opener = urllib2.build_opener(proxy_handler)
   urllib2.install_opener(opener)

# entry point to the command line app, parses arguments and checks for errors. 
def civic_reader():
  try:
    # command line parameters and defaults
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_file", help="input file (assumed to be tab separated MAF format); defaults to stdin", default="-" )
    parser.add_argument("-o", "--output_file", help="output file; defaults to stdout", default="-" )
    parser.add_argument("-col", "--entrez_id_column", help="column in the input file that contains the entrez id. Defaults to 1 (0 based)", default=1,  type=int )
    args = parser.parse_args()

    # Using the tool wrappers path to access the list of civic servers available
    civic_wrapper_dir = os.path.dirname(os.path.realpath(__file__))
    civic_servers_file = civic_wrapper_dir + "/" + "civic_servers.txt"
    with open(civic_servers_file) as f:
      for line in f:
        proxy_handler()
        try: 
            response = urllib2.urlopen('http://' + line)
        except: 
            print line, 'is down!'
        else: 
            print line, 'is up!'
            host = line.rstrip()

    read(
      args.input_file,
      args.output_file,
      host,
      args.entrez_id_column
    )

  except exceptions.SystemExit as e:
    pass
  except:
    sys.stderr.write("Unexpected error:{}\n".format(sys.exc_info()[0]))
    sys.stderr.write("Parameters: input_file({}),output_file({}), entrez_id_column({})\n"
      .format( args.input_file,
      args.output_file,
      args.entrez_id_column)
    )
    raise

# Main entry point to the command line app, re-raises any exceptions amd processes the input and generates the table.
def read(input_file,output_file, host,entrez_id_column):
  """
  Reads a MAF file, calls CIViC api and render table.
  """  
  line_count = 0.0
  hit_count = 0.0
  
  #overriding system proxy settings
  #proxy_handler()

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
    sys.stdout.write("writing to " + output_file +"\n")
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
            civic_gene_id = civic_cache_entrez_lookup(line[entrez_id_column],host)
            expected_hgvs = "{}:{}-{} ({}->{})".format(  line[4]  , line[5] ,line[6],line[10],line[11] )
            if civic_gene_id > 0 :
              hit_count = hit_count + 1.0  
              variant_hgvs = civic_cache_variant_hgvs_lookup(expected_hgvs,host)
              if (len(variant_hgvs)> 0):
                civic_variant = civic_lookup(line[entrez_id_column], host)
              else:
                civic_variant = {'id':civic_gene_id,'variants':[]}  
            else:
              civic_variant = {}
            render(line,civic_variant,host,entrez_id_column,expected_hgvs)
      print('</tbody></table></body></html>')
      print("<p>hit %: {}</p>".format((hit_count/line_count)*100))

  except Exception, e:
    # Read stderr so that it can be reported:
    tmp_dir = tempfile.mkdtemp( dir='.')
    tmp_file_1 = tempfile.NamedTemporaryFile( dir=tmp_dir )
    tmp1 = tmp_file_1.name
    #tmp1 = tempfile.NamedTemporaryFile( dir='.' ).name
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
def render(line,civic_variant,host,entrez_id_column,expected_hgvs):
  """
  Render the report line from MAF file + response from civic as markdown 
  """  
  global render_header
  global not_found

  (variant_name,drugs,link) = civic_properties(line,civic_variant,host,entrez_id_column,expected_hgvs)

  if (render_header):
     print( '<html>\n<head>\n<center><title>Galaxy - CIViC Query Report Tool Summary </center></title>\n<link rel="stylesheet" href="/static/style/base.css" type="text/css" />\n</head>\n<body>\n  <p/>\n  <table border="1">\n    <CAPTION>Summary of genes/variants with links to CIViC webpage</CAPTION><thead>\n      <tr>\n' )
     print("<th>{}</th><th>{}</th><th>{}</th><th>{}</th><th>{}</th><th>{}</th></tr></thead><tbody>\n"
           .format('hugo_symbol','entrez_gene_id','location','CIViC variant name','drugs','link') )
     render_header = False
  if (not link == not_found):   
    print(  "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(line[0],line[1],expected_hgvs,variant_name,drugs,link) )
 

# get the properties of each line from civic
not_found = "<i>gene not found in civic</i>"
def civic_properties(line,response,host,entrez_id_column,expected_hgvs):
  """
  Given a line from the MAF file, and a response from civic, return (variant_name,drugs,link)
  """
  link = '' 
  drugs = ''
  variant_name = ''
  global not_found
  entrez_id = line[entrez_id_column]
  if (response):    
    civic_id = response['id']
    link = '<a href="http://{}/#/events/genes/{}/summary" target="_blank">civic gene</a>'.format(host,civic_id)
    for variant in response['variants'] :
      variant_name = variant.get('name')
      for evidence_item in variant.get('evidence_items'):           
        if evidence_item.get('variant_hgvs') == expected_hgvs:
          if(evidence_item.get('drugs')):
            drugs = ",".join(list(map(lambda e:e.get('name'), evidence_item.get('drugs'))))
          if(evidence_item.get('drug')):
            drugs = evidence_item.get('drug')
          url = "http://{}/#/events/genes/{}/summary/variants/{}/summary/evidence/{}/summary".format(host,civic_id,variant['id'],evidence_item['id'])
          link = '<a href="{}" target="_blank">civic variant</a>'.format(url)
  else:
    link = not_found
  return [variant_name,drugs,link]


entrez_ids_cache = None
def civic_cache_entrez_lookup(entrez_id,host):
  global entrez_ids_cache 
  if (entrez_ids_cache is None):
    entrez_ids_url = "http://" + host + "/api/ccc/entrez_ids" 
    entrez_ids_cache = json.loads(urllib2.urlopen(entrez_ids_url).read().decode('utf-8'))
  entrez_id = int(entrez_id)  
  hit = [x for x in entrez_ids_cache if x[0] == entrez_id ]
  if len(hit)==0:
    return -1 
  return hit[0][1]  

variant_hgvs_cache = None
def civic_cache_variant_hgvs_lookup(variant_hgvs,host):
  global variant_hgvs_cache  
  if (variant_hgvs_cache is None):
    variant_hgvs_url = "http://" + host + "/api/ccc/variant_hgvs" 
    variant_hgvs_cache = json.loads(urllib2.urlopen(variant_hgvs_url).read().decode('utf-8'))
  hit = [x for x in variant_hgvs_cache if x[0] == variant_hgvs ]
  return hit


# get the data from civic
def civic_lookup(entrez_id, host):
  """This function calls civic for the entrez_id.
  """  
  gene_url = "http://" + host + "/api/ccc/genes/" + entrez_id   
  variants_url = "http://" + host + "/api/ccc/genes/" + entrez_id  + "/variants"
  try:
    gene = json.loads(urllib2.urlopen(gene_url).read().decode('utf-8'))
    variants = json.loads(urllib2.urlopen(variants_url).read().decode('utf-8'))
    gene['variants'] = variants 
    return gene
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
