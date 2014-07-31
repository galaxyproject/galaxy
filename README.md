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
git clone https://github.com/erasche/galaxy-rstudio.git config/plugins/viz/rstudio
````

The RStudio visualisation option should be visible next to the usual Charts or Trackster options in your visualisation menue.


Authors
=======

 * Björn Grüning
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
