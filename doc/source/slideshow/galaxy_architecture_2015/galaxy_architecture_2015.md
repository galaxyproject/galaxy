layout: true
class: inverse, center, middle
---
class: special
# Galaxy Architecture 2015

Nate, James

<!--- Add the logo and the Twitter / IRC  mentions --->

---

class: inverse, center, middle

### Please Interrupt!

We're here to answer your question about Galaxy architecture!

---

## 0. Getting involved in Galaxy

---

**IRC**: irc.freenode.net#galaxyproject
<br />
.special2[**GitHub**].special[:] github.com/galaxyproject
<br />
**Trello**: https://trello.com/b/75c1kASa/
<br />
**Twitter**: #usegalaxy, @galaxyproject

---

### Contributing

All Galaxy development has moved to GitHub
<br />
over the last year
<br />
New official contribution guidelines:  https://github.git com/galaxyproject/galaxy/blob/dev/CONTRIBUTING.md

---

## 1. The family of /galaxyproject projects

---

<!-- TODO: Work again on the image -->
![Default-aligned image](images/family/team.png)

---

github.com/galaxyproject/**galaxy**
<br />
#### The main Galaxy application. Web interface, database model, job running, etc. Also includes other web applications including the **ToolShed** and **Reports**

---

github.com/galaxyproject/**cloudlaunch**
#### CloudLaunch web application to make it wasy to launch images on a cloud, drives *http://launch.usegalaxy.org*

---

github.com/galaxyproject/**tools-{devteam,iuc}**
#### Galaxy tools maintained by *devteam* (ths PSU/Hopkins group) and *iuc* (the "Intergalactic Utilities Commission"). A variety of tools, generally of high qualitym including the core tools for Galaxy main. Demonstrates **current tool development best practices** - development on github and then deployed to test/main ToolSheds

---

github.com/galaxyproject/**docker-build**
#### Build Galaxy Tool dependencies for the ToolShed in Docker containers
#### Build Galaxy framework dependencies as Python wheels

---

github.com/galaxyproject/**planemo**
#### Commande line utilities to assist in the development of Galaxy tools. Linting, testing, deploying to ToolSheds... ***The best practice approach for Galaxy tool development!***
github.com/galaxyproject/**planemo-machine**
#### Builds Galaxy environments for Galaxy tool development including Docker container, virtual machines, Google compute images

---

github.com/galaxyproject/**{ansible-\*, \*-playbook}**
#### Ansible components to automate almost every aspect of Galaxy installation and maintenance.
#### Ansible is an advanced configuration management system
#### These playbooks are used to maintain Galaxy main, cloud images, virtual machines, ...

---

github.com/galaxyproject/**pulsar**
#### Distributed job execution engine for Galaxy. Allows staging data, scripts, configuration. Can run jobs on Windows machines. Can act as its own queuing system or access an existing cluster DRM

---

github.com/galaxyproject/**bioblend**
#### Official Python client for the Galaxy and CloudMan APIs

---

## 2. Galaxy app architecture

---

<!-- TODO: Work again on the image -->
background-image: url(images/app_architecture/client_server.png)
background-position: center;
background-repeat: no-repeat;
background-size: contain;

---

background-image: url(images/app_architecture/front_management.png)
background-position: center;
background-repeat: no-repeat;
background-size: contain;

---

background-image: url(images/app_architecture/chunks.png)
background-position: center;
background-repeat: no-repeat;
background-size: contain;

---

background-image: url(images/app_architecture/chunks_2.png)
background-position: center;
background-repeat: no-repeat;
background-size: contain;

---

background-image: url(images/app_architecture/engine.png)
background-position: center;
background-repeat: no-repeat;
background-size: contain;

---

background-image: url(images/app_architecture/job_management.png)
background-position: center;
background-repeat: no-repeat;
background-size: contain;

---

## 3. Galaxy components and object model

---

Galaxy data model is not database entity driven

Entities are defined in galaxy.model as objects

SQLAlchemy is used for object relation mapping

Mappings are defined in galaxy.model.mapping in two
<br />
parts - a table definition and a mapping between
<br />
objects and table including relationships

Migrations allow the schema to be migrated forward
<br />
automatically

---

![Default-aligned image](images/galaxy_components/data_model.png)
https://wiki.galaxyproject.org/Admin/Internals/DataModel

---

![Default-aligned image](images/galaxy_components/data_model2.png)

---

### Core components
![Default-aligned image](images/galaxy_components/core_components.png)

---

### Core components: run analysis
![Default-aligned image](images/galaxy_components/run_analysis.png)

---

### Metadata
Structured data

Different keys/types for different datatypes

Can be used by tools to dynamically control the
<br />
tool form

---

### Core components: workflow
![Default-aligned image](images/galaxy_components/workflow.png)

---

### Core components: workflow run
![Default-aligned image](images/galaxy_components/workflow_run.png)

---

### Data Libraries
![Default-aligned image](images/galaxy_components/data_libraries.png)

---

### Data Libraries: Permissions
![Default-aligned image](images/galaxy_components/permissions.png)

---

### Reference data "cache"
![Default-aligned image](images/galaxy_components/data_cache.png)

---

### .special2[Visualization Plugins]

Adding new visualizatons to a Galaxy instance:
- Configuration file (XML)
- Base template (Mako)
- Additional static data *if needed* (CSS, JS, ...)

---

### .special2[Visualization Plugins: Charts]
![Default-aligned image](images/galaxy_components/viz_plugin_charts.png)

---

### .special2[Visualization Plugins: Data]

How do I *efficiently* access data for my viz?
- Framework provides direct link to read the raw dataset
- *or* use Data providers
    - In config, assert that visualization requires a given type of data provider
    - Data providers process data before sending to browser. Slice, filter, reformat, ...

---

### .special2[Interactive Environments]
Galaxy side is identical to interactive
<br />
environments: config and base template
- Within the base template, launch a Docker container running a web accessible process
- Build a UI that accesses that process through a proxy

---

### .special2[Dataset Collections]
Hundreds or **thousands** of similar datasets are
<br />
unwiedly, how do you get a handle on them?
- Group datasets into a single unit
- Perform complex operations on that unit
    - Operations are performed on each group element
    - Output of each operation is a new group

---

![Default-aligned image](images/galaxy_components/dataset_collections.png)

---

### Map/reduce in workflows
![Default-aligned image](images/galaxy_components/map_workflow.png)

---

### Histories
![Default-aligned image](images/galaxy_components/histories.png)

---

### .special2[Dataset Collections]
![Default-aligned image](images/galaxy_components/dataset_collections_history.png)

---

### Object Store
![Default-aligned image](images/galaxy_components/object_store1.png)

---

### Object Store
![Default-aligned image](images/galaxy_components/object_store2.png)

---

## 4. Galaxy startup

---

### Pre-startup
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### First run: Initialize configs
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### First run: Fetch eggs
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### Every run: Load the application
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### Every run: Load database migrations
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### First run: Initialize database
![Default-aligned image](images/galaxy_components/object_store2.png)

---

Everything after here happens every time

---

### Load tool migrations
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### Load datatypes
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### Load datatypes sniffers
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### Load build (display) sites
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### Load data tables
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### Read job configuration file
![Default-aligned image](images/galaxy_components/object_store2.png)
* config/job_conf.xml will automatically be read if created, see
<br />
job_conf_xml.sample_advanced for fully documented examples of all
<br />
possible configurations

---

### Load tools
![Default-aligned image](images/galaxy_components/object_store2.png)
* shed_tool_conf.xml is empty on the first run so
<br />
only tools provided with Galaxy are loaded, but
<br />
after tools are installed from the Tool Shed, they
<br />
will load here

---

### Associate display apps with datatypes
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### Load implicit datatype converters
![Default-aligned image](images/galaxy_components/object_store2.png)
* A few internal operations are defined as tools to allow them to run via Galaxy'
<br />
s job system, and are loaded here as well

---

### Load visualization plugins
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### Initialize job handlers
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### Initialize web controllers
![Default-aligned image](images/galaxy_components/object_store2.png)

---

### Load WSGI middleware
![Default-aligned image](images/galaxy_components/object_store2.png)

---

serving on http://127.0.0.1:8080

---

## 5. A Galaxy request

---

### Beginning of request
- TCP connection from client on port 80
- WSGI server is responsible for picking up the
<br />
connection, parsing HTTP headers, and
<br />
reformatting them into a dictionary according
<br />
to the WSGI spec, this dict is called "environ"
- In a default Galaxy install this is *currently*
Paste#http

---

### Middleware
- The WSGI interface is based around function
<br />
calls: def app( environ, start_response ): ...
- Middleware act as filters, modify the environ
<br />
and then pass through to the next webapp
- Galaxy uses several middleware components
galaxy.webapps.galaxy.buildapp#wrap_in_middleware
<br />
error handling, logging, proxy hostname, debug, static, ...

---

### WebApplication (galaxy.web.framework.base#WebApplication)
- Galaxy's custom web framework, shares a lot
<br />
of ideas with Pylons
- __call__ method supports the WSGI spec
    - Takes environ and creates a wrapper object
    <br />
    GalaxyWebTransaction -- ** this is the ubiquitous trans! **

---



---



---



---



---



---



---



---



---



---



---



---



---



---
