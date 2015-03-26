#!/usr/bin/env python

from drmaa import *
from drmaa import const as c
from os import environ

Session.initialize();
jt = Session.createJobTemplate();

common_dir='/mnt/lustre1/HTCondor';
jt.remoteCommand = common_dir+'/programs/sum.py';

jt.args = [ common_dir+'/outputs/products', common_dir+'/outputs/sum' ];

#stdout and stderr
jt.outputPath = ':'+common_dir+'/logs/stdout.sum';
jt.errorPath = ':'+common_dir+'/logs/stderr.sum';

#request resources and set log file
jt.nativeSpecification = 'request_cpus=8\n';

jid = Session.runJob(jt);
print('Job id: '+jid);

#wait for job completion
Session.synchronize([jid], Session.TIMEOUT_WAIT_FOREVER);


Session.deleteJobTemplate(jt);
Session.exit()


