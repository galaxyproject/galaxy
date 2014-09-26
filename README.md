Galaxy RStudio Integration
==========================

This projects integrates [RStudio](http://www.rstudio.com/), a interactive computational environment, with [Galaxy](http://galaxyproject.org).
We hope to make Galaxy more attractive for bioinformaticians and to combine the power of both projects to unlock creativity in data analysis


Requirements
============

The only requirement is to have [Docker](https://www.docker.com) installed on your system.
For a detailed instruction how to install docker, please look at the [docker website](https://docs.docker.com/installation/).


Installation
============

Copy the template and config folder in your ``GALAXY_ROOT/config/plugins/visualizations/rstudio`` folder and restart Galaxy.
Alternatively, you can clone the repository with

```bash
git clone https://github.com/erasche/galaxy-rstudio.git config/plugins/visualizations/rstudio
````

The RStudio visualisation option should be visible next to the usual Charts or Trackster options in your visualisation menue.

![Starting RStudio in Galaxy](https://raw.githubusercontent.com/erasche/galaxy-ipython/master/static/images/start_rstudio.png)


Features
========

 * run RStudio directly in your Galaxy main window or in Galaxy Scratchbook
 * complete encapsulated R environment
 * access to all datasets from your current history via pre-defined RStudio function
 * manipulate and plot data as you like and export your new files back into the Galaxy history
 * self-closing and cleaning RStudio docker container

How does it work
================

The mako template from the Galaxy visualisation framework renders the interface and builds all files and commands needed to lunch the docker container. A config file is saved under ``/import/`` inside the docker container. The RStudio webpage running in docker will be included in a HTML object and displayed to the user. 
Depending on your configuration some JavaScript magic is done to add an object to the DOM, which will be loaded by the browser and conditionally handles login.
Iside of docker TCP connections are monitored using cron. As soon as the user quits using the notebook, the dropping TCP connections are recognised and the cotainer cleans up after itself and kills itself.



Functions and variables
=======================

For your convience, we have added a few pre-defined functions to the IPython profile.

### gx_get

   The get function will copy a dataset, identified by the history_id, from your current Galaxy 
   into the docker container. It will return the file path to the copied file.

   *Example*:
   ```R
      data <- read.csv(gx_get(44), sep="\t")
      View(data)
   ``` 

### gx_put

   The put function takes a file path and transfers the file to the current history of your Galaxy session.

   *Example*:
   ```R
      put('./my_file.tsv')
      put('./my_file.tsv', file_type="tabular")
   ```


Security
========

By default, no security is turned on.

In production, `apache_urls` variable should be set to `True`, and containers should be secured via Apache+SSL for production usage. Please see the [setup](INSTALL.md) document for more information.

Authors
=======

 * Björn Grüning <bjoern.gruening@gmail.com>
 * Eric Rasche <rasche.eric@yandex.ru>


History
=======

- v0.1: Initial public release


Licence (MIT)
=============

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
