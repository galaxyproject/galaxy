layout: true
class: inverse, middle, large

---
class: special
# Galaxy Architecture

Nate, James, John, Rémi

.footnote[\#usegalaxy / @galaxyproject]

---

class: larger

### Please Interrupt!

We're here to answer your questions about Galaxy architecture!

---

## Getting involved in Galaxy

---

class: larger

**IRC:** irc.freenode.net#galaxyproject

**GitHub:** github.com/galaxyproject

**Twitter:**: #usegalaxy, @galaxyproject

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

github.com/galaxyproject/**tools-iuc**

Galaxy tools maintained by *iuc* (the "Intergalactic Utilities Commission").

A variety of tools, generally of high quality including many of the core tools for Galaxy main.

Demonstrates *current tool development best practices* - development on
github and then deployed to test/main ToolSheds

github.com/galaxyproject/**tools-devteam**

Many older tools appearing on usegalaxy.org.


---

### Tools Aside - More Repositories

Other repositories with high quality tools:

 * [Björn Grüning's repo](https://github.com/bgruening/galaxytools)
 * Peter Cock's repos:
   * [blast repo](https://github.com/peterjc/galaxy_blast)
   * [pico repo](https://github.com/peterjc/pico_galaxy)
   * [mira repo](https://github.com/peterjc/galaxy_mira)
 * [ENCODE tools](https://github.com/modENCODE-DCC/Galaxy)
 * [Biopython repo](https://github.com/biopython/galaxy_packages)
 * [Galaxy Proteomics repo](https://github.com/galaxyproteomics/tools-galaxyp)
 * [Colibread Galaxy Tools](https://github.com/genouest/tools-colibread)
 * [Greg von Kuster's repo](https://github.com/gregvonkuster/galaxy-csg)
 * [TGAC repo](https://github.com/TGAC/tgac-galaxytools)
 * [AAFC-MBB Canada repo](https://github.com/AAFC-MBB/Galaxy/tree/master/wrappers)
 * [Mark Einon's repo](https://github.com/einon/galaxy-tools)


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

Distributed job execution engine for Galaxy.

Stages data, scripts, configuration.

Can run jobs on Windows machines.

Can act as its own queuing system or access an existing cluster DRM.

---

github.com/galaxyproject/**bioblend**

Official Python client for the Galaxy, ToolShed, and CloudMan APIs.

Best documented path to scripting the Galaxy API.

---

- github.com/galaxyproject/**blend4php**
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

## Principles

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
so many different sites and targeting so many different technologies - that
flexibility is paramount.

---

### An Opinionated Frontend

- The target audience is a *bench scientist* - no knowledge of programming, paths, or command lines should be assumed.
- Consistent colors, fonts, themes, etc...
- Reusable components for presenting common widgets - from the generic (forms and grids) to the specific (tools and histories).
- Tied to specific technologies:
  - JavaScript driven
  - Backbone for MVC
  - webpack & RequireJS for modules

---

### A Plugin Driven Backend

Galaxy's backend is in many ways driven by *pluggable interfaces* and
can be adapted to many different technologies.

- SQLAlchemy allows using sqlite, postgres, or MySQL for a database.
- Many different cluster backends or job managers are supported.
- Different frontend proxies (e.g. nginx) are supported as well as web
  application containers (e.g. uWSGI).
- Different storage strategies and technologies are supported (e.g. S3).
- Tool definitions, job metrics, stat middleware, tool dependency resolution, workflow modules,
  datatype definitions are all plugin driven.

???

If the chief architectual principle guiding the frontend is a fast and accessible
experience for the bench scientist, perhaps for the backend it is allowing 
deployment on many different platforms and a different scales.

---

### A Plugin Driven Backend but...

Galaxy has long been guided by the principle that cloning it and calling
the `run.sh` should "just work" and should work quickly.

So by default Galaxy does not require:

 - Compilation - it fetches *binary wheels*.
 - A job manager - Galaxy can act as one.
 - An external database server - Galaxy can use an sqlite database.
 - A web proxy or external Python web server.

---

## Web Frameworks

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

class: white
background-image: url(images/server_client_old.mermaid.svg)

???

User management and admin things, Reports and Tool Shed
Webapp

---

background-image: url(images/wsgi_app.svg)

### Galaxy WSGI

---

### WSGI

- Python interface for web servers defined by PEP 333 - https://www.python.org/dev/peps/pep-0333/.
- Galaxy moving from Paster to uwsgi to host the application.
  - http://pythonpaste.org/
  - https://uwsgi-docs.readthedocs.io/

---

background-image: url(images/wsgi_request.svg)

---

### Galaxy WSGI Middleware

A WSGI function:

`def app(environ, start_response):`

- Middleware act as filters, modify the `environ` and then pass through to the next webapp
- Galaxy uses several middleware components defined in the `wrap_in_middleware`
  function of `galaxy.webapps.galaxy.buildapp`.

---

class: normal

### Galaxy's WSGI Middleware

Middleware configured in `galaxy.webapps.galaxy.buildapp#wrap_in_middleware`.

- `paste.httpexceptions#make_middleware`
- `galaxy.web.framework.middleware.remoteuser#RemoteUser` (if configured)
- `paste.recursive#RecursiveMiddleware`
- `galaxy.web.framework.middleware.sentry#Sentry` (if configured)
- Various debugging middleware (linting, interactive exceptions, etc...)
- `galaxy.web.framework.middleware.statsd#StatsdMiddleware` (if configured)
- `galaxy.web.framework.middleware.xforwardedhost#XForwardedHostMiddleware`
- `galaxy.web.framework.middleware.request_id#RequestIDMiddleware`

---

background-image: url(images/webapp.plantuml.svg)

---

class: normal

### Routes

Setup on `webapp` in `galaxy.web.webapps.galaxy.buildapp.py`.

```python
webapp.add_route(
    '/datasets/:dataset_id/display/{filename:.+?}',
    controller='dataset', action='display',
    dataset_id=None, filename=None
)
```

URL `/datasets/278043/display` matches this route, so `handle_request` will

- lookup the controller named “dataset”
- look for a method named “display” that is exposed
- call it, passing dataset_id and filename as keyword arg

Uses popular Routes library (https://pypi.python.org/pypi/Routes).

---

class: normal

Simplified `handle_request` from `lib/galaxy/web/framework/base.py`.

```python
def handle_request(self, environ, start_response):
    path_info = environ.get( 'PATH_INFO', '' )
    map = self.mapper.match( path_info, environ )
    if path_info.startswith('/api'):
        controllers = self.api_controllers
    else:
        controllers = self.controllers

    trans = self.transaction_factory( environ )

    controller_name = map.pop( 'controller', None )
    controller = controllers.get( controller_name, None )

    # Resolve action method on controller
    action = map.pop( 'action', 'index' )
    method = getattr( controller, action, None )

    kwargs = trans.request.params.mixed()
    # Read controller arguments from mapper match
    kwargs.update( map )

    body = method( trans, **kwargs )
    # Body may be a file, string, etc... respond with it.
```

---

### API Controllers

- `lib/galaxy/webapps/galaxy/controllers/api/`
- Exposed method take `trans` and request parameters and return a JSON response.
- Ideally these are *thin*
  - Focused on "web things" - adapting parameters and responses and move
    "business logic" to components not bound to web functionality.

---

### Legacy Controllers

- `lib/galaxy/webapps/galaxy/controllers/`
- Return arbitrary content - JSON, HTML, etc...
- Render HTML components using [mako](http://www.makotemplates.org/) templates (see `templates/`)
- The usage of these should decrease over time.

---

## Application Components

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

### Object Store

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

### Visualization Examples

All in `config/plugins/visualizations`:

- `csg` - Chemical structure viewer
- `graphviz` - Visualize graph data using [cytoscape.js](http://www.cytoscape.org/)
- `charts` - A more elobrate builds on more Galaxy abstractions.
- `trackster` - Genome browser, deeply tied to Galaxy internals.

---

### Data Providers

Provide efficient access to data for viz & API

Framework provides direct link to read the raw dataset
or use data providers to adapt it

In config, assert that visualization requires a given type of data providers

Data providers process data before sending to browser - slice, filter, reformat, ...

---

### Interactive Environments

Similar to vizualizations: config and template

Within the base template, launch a Docker container running a web accessible
process

Build a UI that accesses that process through a proxy

---

### Interactive Environments - Examples

All in `config/plugins/interactive_environments`:

- `jupyter`
- `rstudio`
- `phinch`
- `bam_iobio`

---

### Client Directories

- Source stylesheets and JavaScript in `client/galaxy/{style|scripts}`
- "Packed" scripts served by Galaxy stored in `static/{style|scripts}`
  - webpack builds these "compiled" artifacts

Upshot - modify files in `client` and rebuild with `make client` before
deployment.

---

class: normal

### Building the Client - Makefile Targets

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

Build tool for node/JavaScript, tasks in `client/Gruntfile.js`. Default task is

.smaller[```grunt.registerTask( 'default', [ 'check-modules', 'uglify', 'webpack' ] );```]

- `check-modules` Verifies node dependencies are correct and exact.
- [`uglify`](https://github.com/mishoo/UglifyJS) Compresses JavaScript modules in `client` and move to `static` and creates source maps.
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

RequireJS an implementation of AMD.


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

background-image: url(images/cluster_support.svg)

### Cluster Support

---

background-image: url(images/usegalaxy_webservers.svg)

---

background-image: url(images/usegalaxyorg.svg)

---

## Q & A

---
