#!/usr/bin/env python
"""
Execute workflows from the command line.
Example calls:
python workflow_execute.py <api_key> <galaxy_url>/api/workflows f2db41e1fa331b3e 'Test API History' '38=ldda=0qr350234d2d192f'
python workflow_execute.py <api_key> <galaxy_url>/api/workflows f2db41e1fa331b3e 'hist_id=a912e9e5d84530d4' '38=hda=03501d7626bd192f'
"""

"""
python workflow_execute.py <api_key> <galaxy_url>/api/workflows f2db41e1fa331b3e 'hist_id=a912e9e5d84530d4' '38=hda=03501d7626bd192f' 'param=tool=name=value' 

'param=tool=name=value'

Example 
python workflow_execute_parameters.py 35a24ae2643785ff3d046c98ea362c7f http://localhost:8080/api/workflows 1cd8e2f6b131e891 'Test API' '69=ld=a799d38679e985db' '70=ld=33b43b4e7093c91f' 'param=peakcalling_spp=aligner=bwa' 

python workflow_execute_parameters.py 35a24ae2643785ff3d046c98ea362c7f http://localhost:8080/api/workflows 1cd8e2f6b131e891 'Test API' '69=ld=a799d38679e985db' '70=ld=33b43b4e7093c91f' 'param=peakcalling_spp=aligner=arachne' 'param=bowtie_wrapper=suppressHeader=True'

python workflow_execute_parameters.py 35a24ae2643785ff3d046c98ea362c7f http://localhost:8080/api/workflows 1cd8e2f6b131e891 'Test API' '69=ld=a799d38679e985db' '70=ld=33b43b4e7093c91f' 'param=peakcalling_spp=aligner=bowtie' 'param=bowtie_wrapper=suppressHeader=True' 'param=peakcalling_spp=window_size=1000' 

"""

import os, sys
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import submit


def main():
    try:
        print("workflow_execute:py:");
        data = {}
        data['workflow_id'] = sys.argv[3]
        data['history'] = sys.argv[4]
        data['ds_map'] = {}

        #########################################################
        ### MY EDITS ############################################
        ### Trying to pass in parameter for my own dictionary ###
        data['parameters'] = {};

        # DBTODO If only one input is given, don't require a step
        # mapping, just use it for everything?
        for v in sys.argv[5:]:
            print("Multiple arguments ");
            print(v);

            try:
                step, src, ds_id = v.split('=');
                data['ds_map'][step] = {'src':src, 'id':ds_id};

            except ValueError:
                print("VALUE ERROR:");
                wtype, wtool, wparam, wvalue = v.split('=');
                data['parameters'][wtool] = {'param':wparam, 'value':wvalue}


        #########################################################
        ### MY EDITS ############################################
        ### Trying to pass in parameter for my own dictionary ###
        #data['parameters']['bowtie'] = {'param':'stepSize', 'value':100}
        #data['parameters']['sam_to_bam'] = {'param':'genome', 'value':'hg18'}

    except IndexError:
        print 'usage: %s key url workflow_id history step=src=dataset_id' % os.path.basename(sys.argv[0])
        sys.exit(1)
    submit( sys.argv[1], sys.argv[2], data )

if __name__ == '__main__':
    main()

