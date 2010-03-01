import ez_setup
ez_setup.use_setuptools()
from setuptools import setup, find_packages
import re, os

version = '1.7.3'

news = os.path.join(os.path.dirname(__file__), 'docs', 'news.txt')
news = open(news).read()
parts = re.split(r'([0-9\.]+)\s*\n\r?-+\n\r?', news)
found_news = ''
for i in range(len(parts)-1):
    if parts[i] == version:
        found_news = parts[i+i]
        break
if not found_news:
    print 'Warning: no news for this version found'

long_description="""\
This is a pluggable command-line tool.

It includes some built-in features;

* Create file layouts for packages.  For instance, ``paste create
  --template=basic_package MyPackage`` will create a `setuptools
  <http://peak.telecommunity.com/DevCenter/setuptools>`_-ready
  file layout.

* Serving up web applications, with configuration based on
  `paste.deploy <http://pythonpaste.org/deploy/paste-deploy.html>`_.

The latest version is available in a `Subversion repository
<http://svn.pythonpaste.org/Paste/Script/trunk#egg=PasteScript-dev>`_.

For the latest changes see the `news file
<http://pythonpaste.org/script/news.html>`_.
"""

if found_news:
    title = 'Changes in %s' % version
    long_description += "\n%s\n%s\n" % (title, '-'*len(title))
    long_description += found_news

setup(
    name="PasteScript",
    version=version,
    description="A pluggable command-line frontend, including commands to setup package file layouts",
    long_description=long_description,
    classifiers=[
      "Development Status :: 5 - Production/Stable",
      "Intended Audience :: Developers",
      "License :: OSI Approved :: MIT License",
      "Programming Language :: Python",
      "Topic :: Internet :: WWW/HTTP",
      "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
      "Topic :: Software Development :: Libraries :: Python Modules",
      "Framework :: Paste",
      ],
    keywords='web wsgi setuptools framework command-line setup',
    author="Ian Bicking",
    author_email="ianb@colorstudy.com",
    url="http://pythonpaste.org/script/",
    namespace_packages=['paste'],
    license='MIT',
    packages=find_packages(exclude='tests'),
    package_data={
      'paste.script': ['paster-templates/basic_package/setup.*',
                       'paster-templates/basic_package/tests/*.py',
                       # @@: docs/ doesn't have any files :(
                       'paster-templates/basic_package/+package+/*.py'],
      },
    zip_safe=False,
    scripts=['scripts/paster'],
    extras_require={
      'Templating': [],
      'Cheetah': ['Cheetah'],
      'Config': ['PasteDeploy'],
      'WSGIUtils': ['WSGIUtils'],
      'Flup': ['Flup'],
      # the Paste feature means the complete set of features;
      # (other features are truly optional)
      'Paste': ['PasteDeploy', 'Cheetah'],
      },
    entry_points="""
    [paste.global_paster_command]
    help=paste.script.help:HelpCommand
    create=paste.script.create_distro:CreateDistroCommand [Templating]
    serve=paste.script.serve:ServeCommand [Config]
    request=paste.script.request:RequestCommand [Config]
    post=paste.script.request:RequestCommand [Config]
    exe=paste.script.exe:ExeCommand
    points=paste.script.entrypoints:EntryPointCommand
    make-config=paste.script.appinstall:MakeConfigCommand
    setup-app=paste.script.appinstall:SetupCommand

    [paste.paster_command]
    grep = paste.script.grep:GrepCommand

    [paste.paster_create_template]
    basic_package=paste.script.templates:BasicPackage

    [paste.server_runner]
    wsgiutils=paste.script.wsgiutils_server:run_server [WSGIUtils]
    flup_ajp_thread=paste.script.flup_server:run_ajp_thread [Flup]
    flup_ajp_fork=paste.script.flup_server:run_ajp_fork [Flup]
    flup_fcgi_thread=paste.script.flup_server:run_fcgi_thread [Flup]
    flup_fcgi_fork=paste.script.flup_server:run_fcgi_fork [Flup]
    flup_scgi_thread=paste.script.flup_server:run_scgi_thread [Flup]
    flup_scgi_fork=paste.script.flup_server:run_scgi_fork [Flup]
    cgi=paste.script.cgi_server:paste_run_cgi
    cherrypy=paste.script.cherrypy_server:cpwsgi_server
    twisted=paste.script.twisted_web2_server:run_twisted

    [paste.app_factory]
    test=paste.script.testapp:make_test_application

    [paste.entry_point_description]
    paste.entry_point_description = paste.script.epdesc:MetaEntryPointDescription
    paste.paster_create_template = paste.script.epdesc:CreateTemplateDescription
    paste.paster_command = paste.script.epdesc:PasterCommandDescription
    paste.global_paster_command = paste.script.epdesc:GlobalPasterCommandDescription
    paste.app_install = paste.script.epdesc:AppInstallDescription

    # These aren't part of Paste Script particularly, but
    # we'll document them here
    console_scripts = paste.script.epdesc:ConsoleScriptsDescription
    # @@: Need non-console scripts...
    distutils.commands = paste.script.epdesc:DistutilsCommandsDescription
    distutils.setup_keywords = paste.script.epdesc:SetupKeywordsDescription
    egg_info.writers = paste.script.epdesc:EggInfoWriters
    # @@: Not sure what this does:
    #setuptools.file_finders = paste.script.epdesc:SetuptoolsFileFinders
    
    [console_scripts]
    paster=paste.script.command:run

    [distutils.setup_keywords]
    paster_plugins = setuptools.dist:assert_string_list

    [egg_info.writers]
    paster_plugins.txt = setuptools.command.egg_info:write_arg
    """,
    install_requires=[
      ],
    )
