Common templates for visualization plugins
==========================================

Placing Mako templates in this directory will allow them to be properly
inherited and imported in plugin directories. E.g. if you have a template file
in this directory named 'config_utils.mako', you can import it in your plugin
templates using:
    <%namespace name="config_utils" file="config_utils.mako" />
