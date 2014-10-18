Galaxy IPython Integration
==========================

IPython Integration into Galaxy


Requirements
============

For security reasons you need to have docker installed.
For a detailed instruction how to install docker, please look at the docker website.


Installation
============

Copy the template and config folder in your <GALAXY_ROOT>/config/plugins/visualizations/ipython folder and restart Galaxy.

or

``git clone https://github.com/bgruening/galaxy-ipython.git config/plugins/viz/ipython``

The IPython Visualisation Option should be visible next to the usual Charts or Trackster Options in your Visualisation menue.


Features
========

 * run IPython directly in your Galaxy main window or in Galaxy Scratchbook
 * complete encapsulated python environment with matplotlib, pandas and friends installed
 * access to all datasets from your current history via pre-defined IPython function
 * manipulate and plot data as you like and export your new files back into the Galaxy history
 * save the IPython Notebook into your Galaxy history
 * saved IPython Notebook files can be viewed in HTML and re-opened
 * self-closing and cleaning IPython docker container


Security
========

 * Containers can be secured via Apache+SSL. Please see the [setup](INSTALL.md) document for more
   information.
 * Containers will soon have `iptables` based security to provide a minimum attempt at preventing
   users from accessing one another's notebooks.


Authors
=======

 * Bjoern Gruening
 * Eric Rasche


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
