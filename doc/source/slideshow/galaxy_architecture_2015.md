# Galaxy Architecture 2015

Nate, James

<!--- Add the logo and the Twitter / IRC  mentions --->

---

### Please Interrupt!

We're here to answer your question about Galaxy architecture!

---

## 0. Getting involved in Galaxy

---

**IRC**: irc.freenode.net#galaxyproject
<br />
**GitHub**: github.com/galaxyproject
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

<!--- TODO: Insert Galaxy Project Github Image -->

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
