#!/usr/bin/python
from bioblend.galaxy import GalaxyInstance
#Create a file called galaxy_key and add your key there
import galaxy_key;

gi = GalaxyInstance(url='http://localhost:8080', key=galaxy_key.galaxy_key);

#histories
for history in gi.histories.get_histories(name='dot_product'):  #iterate over list of dict - use your own history name
  history_id = history['id'];
  print("History %s %s"%(history['name'], history['id']));
  #print(gi.histories.show_history(history_id, details='all'));

#dataset libraries
#This is a shared library I created on c10 - you should be able to access these datasets
vA = None;
vB = None;
for library in gi.libraries.get_libraries(name='Testing_vectors'):     #iterate over list of dict
  library_id = library['id'];
  for content in gi.libraries.show_library(library_id, contents=True):  #iterate over list of dict
    if(content['type'] == 'file'):      #could also be folder
      print('Dataset %s %s'%(content['name'], content['id']));
      if(content['name'].find('vA.val') != -1):
        vA = content;
      if(content['name'].find('vB.val') != -1):
        vB = content;

#print("vA = %s"%vA);
#print("vB = %s"%vB);

#workflows
#Search for your workflows
for workflow in gi.workflows.get_workflows(name='dot_product'):
  workflow_id = workflow['id'];
  workflow_object = gi.workflows.show_workflow(workflow_id);    #dict
  print(workflow_object);
  steps_dict = workflow_object['steps'];     #dict
  for step_idx, step_spec in steps_dict.iteritems():
    print("Step %d tool %s input %s"%(int(step_idx), step_spec['tool_id'], step_spec['input_steps']));
  input_map = workflow_object['inputs'];        #get input labels for workflow
  dataset_input_map = dict();                       #dict to set inputs
  for input_idx, input_spec in input_map.iteritems():
    if(input_spec['label'] == 'vA'):
      dataset_input_map[input_idx] = { 'id' : vA['id'], 'src' : 'ld' }; 
    if(input_spec['label'] == 'vB'):
      dataset_input_map[input_idx] = { 'id' : vB['id'], 'src' : 'ld' };
  gi.workflows.run_workflow(workflow_id, dataset_map=dataset_input_map,history_id=history_id);
