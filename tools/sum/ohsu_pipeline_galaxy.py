#!/usr/bin/python
from bioblend.galaxy import GalaxyInstance
#Create a file called galaxy_key and add your key there
import galaxy_key;
import sys;

gi = GalaxyInstance(url='http://localhost:8080', key=galaxy_key.galaxy_key);

history_id = None;
#Iterate over histories and check whether there is one called dot product
for history in gi.histories.get_histories(name='dot_product'):  #iterate over list of dict - use your own history name
  history_id = history['id'];
  print("History %s %s"%(history['name'], history['id']));


#dataset libraries
#This is a shared library I created on c10 - you should be able to access these datasets
#Iterate over all datasets in the data library called 'DNA pipeline inputs'
indels = None;
dbsnp = None;
fq1 = None;
fq2 = None;
reference = None;
for library in gi.libraries.get_libraries(name='OHSU'):     #iterate over list of dict
  library_id = library['id'];
  for content in gi.libraries.show_library(library_id, contents=True):  #iterate over list of dict
    if(content['type'] == 'file'):      #could also be folder
      print('Dataset %s %s'%(content['name'], content['id']));
      if(content['name'].find('1000g_indels.vcf') != -1):
        indels = content;
      if(content['name'].find('dbsnp-all.vcf') != -1):
        dbsnp = content;
      if(content['name'].find('sim1M_pairs_1.fq') != -1):
        fq1 = content;
      if(content['name'].find('sim1M_pairs_2.fq') != -1):
        fq2 = content;
      if(content['name'].find('human_g1k_v37.fasta') != -1):
        reference = content;

print(reference);
print(indels);
print(dbsnp);
print(fq1);
print(fq2);

#workflows
#Search for workflow OHSU_3_stage in your workflows - note workflows should be imported into 
#your account 
for workflow in gi.workflows.get_workflows(name='OHSU_3_stage'):
  workflow_id = workflow['id'];
  workflow_object = gi.workflows.show_workflow(workflow_id);    #dict
  sys.stdout.write("Workflow object : ");
  print(workflow_object);
  steps_dict = workflow_object['steps'];     #dict
  for step_idx, step_spec in steps_dict.iteritems():
    print("Step %d tool %s input %s"%(int(step_idx), step_spec['tool_id'], step_spec['input_steps']));
  input_map = workflow_object['inputs'];        #get input labels for workflow
  dataset_input_map = dict();                       #dict to set inputs
  for input_idx, input_spec in input_map.iteritems():
    if(input_spec['label'] == 'reference'):
      dataset_input_map[input_idx] = { 'id' : reference['id'], 'src' : 'ld' }; 
    if(input_spec['label'] == 'indels.vcf'):
      dataset_input_map[input_idx] = { 'id' : indels['id'], 'src' : 'ld' };
    if(input_spec['label'] == 'dbsnp.vcf'):
      dataset_input_map[input_idx] = { 'id' : dbsnp['id'], 'src' : 'ld' };
    if(input_spec['label'] == 'forward_fastq_file'):
      dataset_input_map[input_idx] = { 'id' : fq1['id'], 'src' : 'ld' };
    if(input_spec['label'] == 'reverse_fastq_file'):
      dataset_input_map[input_idx] = { 'id' : fq2['id'], 'src' : 'ld' };
  #Send outputs to new history called 'OHSU_3_step_history' - HISTORY IS CREATED!
  gi.workflows.run_workflow(workflow_id, dataset_map=dataset_input_map,history_name="OHSU_3_step_history");
  #Alternately, send outputs to existing history whose id has been determined in the first 15 lines
  #gi.workflows.run_workflow(workflow_id, dataset_map=dataset_input_map,history_id=history_id);
