layout: true
class: inverse, middle, large

---
class: special
# Galaxy Architecture

Nate, James, John, Rémi

.footnote[\#usegalaxy / @galaxyproject]

---

### Please Interrupt!

We're here to answer your question about Galaxy architecture!

---

## Getting involved in Galaxy

---

**IRC**: irc.freenode.net#galaxyproject
<br />
.special2[**GitHub**].special[:] github.com/galaxyproject
<br />
**Twitter**: #usegalaxy, @galaxyproject

---

### Contributing

All Galaxy development happens on GitHub

Contribution guidelines: http://bit.ly/gx-CONTRIBUTING-md

---

## The **/galaxyproject** projects

---

class: white

background-image: url(images/family/team.png)

---

github.com/galaxyproject/**galaxy**

The main Galaxy application. Web interface, database model, job running, etc. Also includes other web applications including the **ToolShed** and **Reports**

---

github.com/galaxyproject/**cloudman**

Galaxy CloudMan - a web application which manages a Galaxy cluster in
the cloud.

github.com/galaxyproject/**cloudlaunch**

CloudLaunch web application to make it wasy to launch images on a cloud, drives *https://launch.usegalaxy.org*

---

github.com/galaxyproject/**tools-{devteam,iuc}**

Galaxy tools maintained by *devteam* (ths PSU/Hopkins group) and *iuc* (
the "Intergalactic Utilities Commission"). A variety of tools, 
generally of high quality including the core tools for Galaxy main. 
Demonstrates *current tool development best practices* - development on 
github and then deployed to test/main ToolSheds

---

github.com/galaxyproject/**starforge**

Build Galaxy Tool dependencies for the ToolShed in Docker containers

Build Galaxy framework dependencies as Python wheels

---

github.com/galaxyproject/**planemo**

Commande line utilities to assist in the development of Galaxy tools. 
Linting, testing, deploying to ToolSheds... *The best practice approach 
for Galaxy tool development!*

github.com/galaxyproject/**planemo-machine**

Builds Galaxy environments for Galaxy tool development including Docker 
container, virtual machines, Google compute images

---

github.com/galaxyproject/**{ansible-\*, \*-playbook}**

Ansible components to automate almost every aspect of Galaxy installation and maintenance.

Ansible is an advanced configuration management system

These playbooks are used to maintain Galaxy main, cloud images, virtual machines, ...

---

github.com/galaxyproject/**pulsar**

Distributed job execution engine for Galaxy. Allows staging data, scripts, configuration. Can run jobs on Windows machines. Can act as its own queuing system or access an existing cluster DRM

---

github.com/galaxyproject/**bioblend**

Official Python client for the Galaxy, ToolShed, and CloudMan APIs.

Best documented path to scripting the Galaxy API.

---

- github.com/**tripal/blend4php**
- github.com/**jmchilton/blend4j**
- github.com/**chapmanb/clj-blend**

Galaxy API bindings for other languages.

---

github.com/**bgruening/docker-galaxy-stable**

High quality Docker containers for stable Galaxy environments.

Releases corresponding to each new version of Galaxy.

Many flavors available.

---

class: white
background-image: url(images/docker-chart.png)
  
---

## Galaxy app architecture

---

### Aspirational Principles of Galaxy Architecture

Whereas the architecture of the frontend (Web UI) aims for consistency and is
highly opinionated, the backend (Python server) is guided by flexibility and is meant to be driven by plugins whenever possible.

???

Though an imperfect abstraction... maybe it is beneficial to think of the organizational
principles that guide frontend and backend development of Galaxy as
diametrically opposite.

The frontend architecture is guided by the principle that the end user experience
should be as simple and consistent as possible. The backend has been deployed at
so many different sites and targetting so many different technologies - that 
flexibility is paramount.

---

### An Opinionated Frontend

- The target audience is a bench scientist - no knowledge of programming, paths, or command lines should be assumed.
- Consistent colors, fonts, themes, etc...
- Reusable libraris for presenting common widgets such as forms and grids.
- Tied to specific technologies:
  - JavaScript driven.
  - Backbone for MVC.
  - RequireJS for module loading.

---

### A Plugin Driven Backend

Galaxy's backend is in many ways driven by pluggable interfaces and
can be adapted to many different technologies.

- SQLAlchemy allows using sqlite, postgres, or MySQL for a database.
- Many different cluster backends or job managers are supported.
- Different frontend proxies (e.g. nginx) are supported as well as web
  application containers (e.g. uWSGI).
- Different storage strategies and technologies are supported (e.g. S3).
- Tools, job metrics, tool dependency resolution, workflow modules, 
  datatype definitions are all plugin driven.

---

### A Plugin Driven Backend but...

Galaxy has long been guided by the principle that cloning it and calling
the `run.sh` should "just work" and should work quickly.

So by default Galaxy does not require:

 - Compilation - it fetches binary wheels.
 - A job manager - Galaxy can act as one.
 - An external database server - Galaxy can use an sqlite database.
 - A web proxy or external Python web server.

---

class: white
background-image: url(images/server_client_old.mermaid.svg)

???

User management and admin things, Reports and Tool Shed 
Webapp

---

class: white

background-image: url(images/server_client.mermaid.svg)

???

Workflow, Data Libraries, Visualization, History, Tool Menu, 
Many Grids

---

class: white

background-image: url(images/backbone-model-view.svg)

### Backbone MVC

---

background-image: url(images/wsgi_app.svg)

### Galaxy WSGI

---

### WSGI

- Python interface for web servers defined by PEP 333 - https://www.python.org/dev/peps/pep-0333/.
- Galaxy slowly moving from Paster to uwsgi to host the application.
  - http://pythonpaste.org/
  - https://uwsgi-docs.readthedocs.io/

---

background-image: url(images/wsgi_request.svg)

---

### Galaxy Models

- Database interactions powered by SQLAlchemy - http://www.sqlalchemy.org/.
- Galaxy doesn't think in terms "rows" but "objects".
- Classes for Galaxy model objects in `lib/galaxy/model/__init__.py`.
- Classes mapped to tables in `lib/galaxy/model/mapping.py`
  - Describes table definitions and relationships.

---

class: white

background-image: url(images/sqla_arch_small.png)

---

### Galaxy Model Migrations

- A migration describes a linear list of database "diff"s to
  end up with the current Galaxy model.
- Allow the schema to be migrated forward automatically.
- Powered by sqlalchemy-migrate - https://sqlalchemy-migrate.readthedocs.io/en/latest/.
- Each file in `lib/galaxy/model/migrate/versions/`
  - `0124_job_state_history.py`
  - `0125_workflow_step_tracking.py`
  - `0126_password_reset.py`

---

class: white
background-image: url(images/galaxy_schema.png)

### Database Diagram

https://wiki.galaxyproject.org/Admin/Internals/DataModel

---

background-image: url(images/hda.svg)

---

background-image: url(images/hda_dataset.plantuml.svg)

---

### Metadata

- Typed key-value pairs attached to HDA.
- Keys and types defined at the datatype level.
- Can be used by tools to dynamically control the tool form.

???

Slides for datatypes, example of meta data definitions...

---

background-image: url(images/hda_hdca.plantuml.svg)

---

background-image: url(images/workflow_definition.svg)

---

background-image: url(images/workflow_run.svg)

---

background-image: url(images/libraries.svg)

---

background-image: url(images/library_permissions.svg)

---

background-image: url(images/data_managers.svg)

---

class: normal

.strike[```
>>> fh = open( dataset.file_path, 'w' )
>>> fh.write( ‘foo’ )
>>> fh.close()
>>> fh = open( dataset.file_path, ‘r’ )
>>> fh.read()
```]

```
>>> update_from_file( dataset, file_name=‘foo.txt’ )
>>> get_data( dataset )
>>> get_data( dataset, start=42, count=4096 )
```

---

background-image: url(images/objectstore_diagram.svg)

---

background-image: url(images/objectstore.plantuml.svg)

---

### Visualization Plugins

Adding new visualizations to a Galaxy instance

- Configuration file (XML)
- Base template (Mako or JavaScript)
- Additional static data if needed (CSS, JS, …)

---

class: smaller

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE visualization SYSTEM "../../visualization.dtd">
<visualization name="Charts">
    <data_sources>
        <data_source>
            <model_class>HistoryDatasetAssociation</model_class>
            <test type="isinstance" test_attr="datatype" result_type="datatype">tabular.Tabular</test>
            <test type="isinstance" test_attr="datatype" result_type="datatype">tabular.CSV</test>
            <to_param param_attr="id">dataset_id</to_param>
        </data_source>
    </data_sources>
    <params>
        <param type="dataset" var_name_in_template="hda" required="true">dataset_id</param>
    </params>
    <entry_point entry_point_type="mako">charts.mako</entry_point>
</visualization>
```

---

### Data Providers

How do I efficiently access data for my viz?
Framework provides direct link to read the raw dataset
or use Data providers
In config, assert that visualization requires a given type of data providers
Data providers process data before sending to browser. Slice, filter, reformat, ...

---

### Interactive Environments

Galaxy side is identical to interactive environments: config and base template
Within the base template, launch a Docker container running a web accessible process
Build a UI that accesses that process through a proxy

---

### Dataset Collections

Hundreds or thousands of similar datasets are unwieldy, how do you get a handle on them?
Group datasets into a single unit
Perform complex operations on that unit
Operations are performed on each group element
Output of each operation is a new group

---

### Client Directories

- Source stylesheets and JavaScript in `client/galaxy/{style|scripts}`
- "Packed" scripts served by Galaxy stored in `static/{style|scripts}`
  - webpack builds these "compiled" artifacts

Upshot - modify files in `client` and rebuild with `make client` before 
deployment.

---

### Building the Client - Makefile Targets

class: normal

```
client: grunt style ## Rebuild all client-side artifacts

grunt: npm-deps ## Calls out to Grunt to build client
  cd client && node_modules/grunt-cli/bin/grunt

style: npm-deps ## Calls the style task of Grunt
  cd client && node_modules/grunt-cli/bin/grunt style

npm-deps: ## Install NodeJS dependencies.
  cd client && npm install
```

---

### grunt

Build tool for JavaScript, tasks are defined in `client/Gruntfile.js`. The default task is
  
.smaller[```grunt.registerTask( 'default', [ 'check-modules', 'uglify', 'webpack' ] );```]

- `check-modules` Verifies node dependencies are correct and exact.
- `uglify` Compresses JavaScript modules in `client` and move to `static` and creates source maps.
   - https://github.com/mishoo/UglifyJS
   - JavaScript loads much faster but difficult to debug by default
   - Source maps re-enable proper stack traces.
- `webpack` Bundles modules together into a single JavaScript file - quickly loadable.

---

### JavaScript Modules - The Problem

From http://requirejs.org/docs/why.html:

- Web sites are turning into Web apps
- Code complexity grows as the site gets bigger
- Assembly gets harder
- Developer wants discrete JS files/modules
- Deployment wants optimized code in just one or a few HTTP calls

---

### JavaScript Modules - The Solution

From http://requirejs.org/docs/why.html:

 - Some sort of #include/import/require
 - Ability to load nested dependencies
 - Ease of use for developer but then backed by an optimization tool that helps deployment

Enter RequireJS an implementation of AMD.


---

class: normal

### JavaScript Modules - Galaxy AMD Example

```javascript
/**
    This is the workflow tool form.
*/
define(['utils/utils', 'mvc/tool/tool-form-base'],
    function(Utils, ToolFormBase) {

    // create form view
    var View = ToolFormBase.extend({
      ...
    });

    return {
        View: View
    };
});
```

---

class: white
background-image: url(images/what-is-webpack.svg)

---

### webpack in Galaxy

- Turns Galaxy modules into an "app".
- Builds two bundles currently - a common set of libraries and an analysis "app".
- https://github.com/galaxyproject/galaxy/issues/1041
- https://github.com/galaxyproject/galaxy/pull/1144

---

class: white
background-image: url(images/jsload.png)

---

### Stylesheets

- Galaxy uses the less CSS preprocessor - http://lesscss.org/
- Rebuild style with `make style`
- Less files in `client/galaxy/style/less`
- Build happens with grunt recipe in `client/grunt-tasks/style.js`

---

## Dependencies

---
  
### Dependencies - Python

`script/common_startup.sh` sets up a `virtualenv` with required dependencies in `$GALAXY_ROOT/.venv` (or `$GALAXY_VIRTUAL_ENV` if set).

- Check for existing virtual environment, if it doesn't exist check for `virtualenv`.
- If `virtualenv` exists, use it. Otherwise download it as a script and setup a virtual environment using it.
- `. "$GALAXY_VIRTUAL_ENV/bin/activate"`
- Upgrade to latest `pip` to allow use of binary wheels.
- `pip install -r requirements.txt --index-url https://wheels.galaxyproject.org/simple`
- Install dozens of dependencies.

---

### Dependencies - JavaScript

These come bundled with Galaxy, so do not need to be fetched at runtime.

- Dependencies are defined `galaxy/client/bower.json`.
- Bower (https://bower.io/) is used to re-fetch these.
- `cd client; grunt install-libs`

---

## Galaxy Startup Process

---

## Production Galaxy - usegalaxy.org

---

class: centered

.pull-left[
#### Default

SQLite

Paste#http

Single process

Single host

Local jobs

]

.pull-right[
#### Production

PostgreSQL

uWSGI / nginx

Multiple processes

Multiple hosts

Jobs across many clusters
]

*http://usegalaxy.org/production*

---

### postgres

- Database server can scale way beyond default sqlite
- https://www.postgresql.org/
- github.com/galaxyproject/usegalaxy-playbook -> `roles/galaxyprojectdotorg.postgresql`

---

### nginx (or Apache)

- Optimized servers for static content
- https://www.nginx.com/resources/wiki/
- github.com/galaxyproject/usegalaxy-playbook -> `templates/nginx/usegalaxy.j2`

---

### Multi-processes

Threads in Python are limited by the [GIL](https://wiki.python.org/moin/GlobalInterpreterLock).

Running multiple processes of Galaxy and seperate processes for web handling
and job processing works around this.

This used to be an important detail - but uWSGI makes things a lot easier.

---

### Cluster Support

background-image: url(images/cluster_support.svg)

???

Pulsar discussion?

---

background-image: url(images/usegalaxy_webservers.svg)

---

background-image: url(images/usegalaxyorg.svg)

---

## Q & A

---
