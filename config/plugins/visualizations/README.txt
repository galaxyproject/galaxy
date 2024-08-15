Custom visualization plugins
----------------------------

Visualizations can be added to your Galaxy instance by creating
sub-directories, templates, and static files here.

Properly configured and written visualizations will be accessible to
the user when they click the 'visualizations' icon for a dataset
in their history panel.

For more information, see https://training.galaxyproject.org/archive/2019-06-01/topics/dev/tutorials/visualization-generic/tutorial.html


Sub-directory structure
-----------------------

In general, sub-directories should follow the pattern:

    my_visualization/
        config/
            my_visualization.xml
        static/
            ... any static files the visualization needs (if any)
        templates/
            ... any Mako templates the visualization needs

The XML config file for a visualization plugin can be validated on the command
line using (from your plugin directory):

    xmllint my_visualization/config/my_visualization.xml --valid --noout
