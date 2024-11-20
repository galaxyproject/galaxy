This is a planning and discussion issue for enhancements I would like to make to Galaxy's logging system.  

# TL;DR

I want to add a ton of `logger.trace()` calls to the Galaxy codebase, but before doing that we need to get some infrastructure in place.

# What is proposed

1. Enhance support for the `trace()` method that is already present in `galaxy.util.custom_logging`
1. Add a simplified logging configuration section to either `galaxy.yml` or a separate logging config file
1. Add API endpoints to query and set logging levels at runtime
1. Add an admin panel that gives administrators a GUI for setting log levels on a running instance.

# What is not proposed

1. Providing an API that allows arbitrary logger reconfiguration.  We only need (want) to change the logging level at runtime.  No other configuration changes will be allowed.
1. Changing the way loggers are currently configured.  The logging configuration changes proposed here work transparently with the current logging configuration methods.
1. Catching all corner cases.  Good enough is good enough. At least for now.
2. Doing everything now.  This is a first pass and we can add more features and enhancements later.

# Rationale

Debugging Galaxy on Kubernetes clusters is difficult as there is no way to attach a debugger to a running instance and making code changes is time-consuming.  Log messages are the best tool for obtaining runtime information and we don't do enough logging to trace program execution. 

# Proof of concept

I have a proof of concept running that implements the first three items (everything but the admin panel), but before I start submitting PRs there are a number of design decisions to resolve.

## The trace() method

My proof of concept is based on the collective wisdom of [StackOverflow](https://stackoverflow.com/a/35804945/1691778).  If we monkeypatch Python's `logging` library early enough in the code loading process then the `trace()` method is automagically available to all loggers.  There are ~750  configured loggers in a running Galaxy instance.

This works well in a running Galaxy instance, but presents problems for Galaxy packages meant to be used as libraries as we need to be sure that `galaxy.util.logging.addTraceLoggingLevel()` has been called before the first `logger.trace()` statement is encountered at runtime. 

We can:

1. Require that package users call the `addTraceLoggingLevel()` method explicitly before doing anything else.
1. Find a way to ensure `addTraceLoggingLevel()` is called whenever a Galaxy package is imported.
1. Change almost every source file in the Galaxy code base to use `galaxy.util.custom_logging.get_logger()` or similar.

The first option might be good enough until a better solution is decided on.  
I lean towards -1 on the last option.  One of the goals of this proposal is to make these enhancements as seamless and transparent as possible; changing almost every source file in the Galaxy codebase seems to be at odds with that goal. The `addTraceLoggingLevel` method is idempotent, so there should be a way to do #2. Perhaps simply calling `addTraceLoggingLevel()` in the [package.__init__.py](https://github.com/galaxyproject/galaxy/blob/dev/packages/package.__init__.py) file would be sufficient.

## Logging configuration

The proof of concept implementation adds a `logging_levels` section to the `galaxy.yml` file, although this could also be done in a separate configuration file.  The purpose of the `logging_levels` section is not to replace any current methods for configuring logging, it just provides an additional and easier way to set the logging levels for groups of loggers in a single statement.

```
logging_levels:
  galaxy.*: INFO
  galaxy.jobs.runners.*: DEBUG
  galaxy.jobs.runners.kubernetes: TRACE
```
In this example the first statement sets the level for all loggers in the `galaxy` package and all sub-packages (`galaxy`, `galaxy.datatypes`, `galaxy.datatypes.converters`, `galaxy.datatypes.util`, and so on) to the INFO level.  The second statement sets all loggers in the `galaxy.jobs.runners` packages, and the final statement sets the level for a single logger.

## Changes at runtime

Adding `trace()` level logging statements has the potential to blow up log files and Galaxy should not be configured to use `TRACE` as the default logging level. So we will need some way to enable `TRACE` level logging at runtime.  Options include, but are not limited to:

1. set up a file watcher on the config file and reconfigure loggers when changes are detected
2. provide an API that allows log levels to be changed.  

These are not mutually exclusive options, but in some situations, e.g. AnVIL, users may not have access to the configuration files. 

The proof of concept provides a simple API that allows the level to be changed at runtime. Adding a config watcher can be added at a later date if needed.

<img width="835" alt="Screenshot 2024-11-20 at 3 59 52 PM" src="https://github.com/user-attachments/assets/df0b6689-5832-4d7b-98b1-ada2fc5a5b97">

```
curl http://localhost:8080/api/logging
curl http://localhost:8080/api/logging/galaxy.jobs.runners.* 
curl -X POST http://localhost:8080/api/logging/galaxy.jobs.runners.*?level=DEBUG
curl -X POST http://localhost:8080/api/logging/galaxy.jobs.runners.kubernetes?level=TRACE
```
The first `GET` method returns JSON containing information for all currently configured loggers.  The second `GET` method returns information for a single logger or all loggers in a particular package.  The `POST` method can be used to set the logging level for a single logger or all the loggers in a package. 

Are there other endpoints that should be included?  Should we use different endpoints?

# TODO

## Authorization

All API endpoints specify `require_admin=True` in the `@router` decorator.  Is this sufficient? I was thinking of adding checks in relevant `galaxy.util.logging` methods, but is this necessary?

## Admin GUI

I have not started on an admin panel yet, but I envision it would be a new option in the *Server* section of the admin panel.  The logging panel would contain a table and/or a tree view of all the loggers and their current levels and the ability to set the levels for loggers.  I will definitely need some help and guidance with this task.  

## Naming

I've used that I thought were reasonable names for the names of packages, API endpoints, function names, and configuration options, but I'm open to suggestions. This also applies to general code layout and structure.
