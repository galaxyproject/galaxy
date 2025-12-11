CWL import in Galaxy
====================

What is supported
-----------------

What is not supported
---------------------

Some CWL Expressions / Parameter references that do math on `$(resources.cores)`
or similar will likely not work.

How to enable it?
-----------------

1. List paths to CWL tools in `tool_conf.xml` .
2. Set the following in  `galaxy.yml`: 

   ```yaml
   enable_beta_tool_formats: true
   enable_beta_workflow_modules: true
   check_upload_content: false
   strict_cwl_validation: false
   ```
