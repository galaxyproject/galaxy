<%namespace file="/message.mako" import="render_msg" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="title()">Tool Help</%def>

<h2>Tool Help</h2>

%if message:
    ${render_msg( message, status )}
%endif

<h3>Uploading Tools</h3>

<p><strong>Tool File Format</strong></p>
<p>

    A tool file is a tar-format (bzipped or gzipped tar are valid) archive
    containing all the files necessary to load the tool in Galaxy.  At the very
    least, it must contain a
    <a href="http://bitbucket.org/galaxy/galaxy-central/wiki/ToolConfigSyntax" target="_blank">Tool XML File</a>,
    and will probably also include a tool script.  If any steps are necessary
    to install your tool beyond the basic instructions below, please include a
    README file which details these steps.  If the tool (or parts of it) are
    written in C, the source code can be included (or put links to the source
    in the README).  Please do not include precompiled binaries without source,
    since Galaxy is run on a wide variety of platforms.  Also, if you are only
    wrapping or providing a Galaxy config for a tool that is not your own,
    please be sure the license allows for redistribution before including any
    part of that tool in the tar archive!
</p>
<p>
    There are no requirements about the directory structure inside the tar
    archive, but for ease of use, it's generally a good idea to put everything
    inside of a subdirectory, instead of directly at the top level.
</p>

<p><strong>Tool File Example</strong></p>
<p>
    To package up the LASTZ tool's config file, Galaxy wrapper, and the C source:
    <pre>
    user@host:~% tar jcvf ~/Desktop/galaxy_lastz_tool.tar.bz2 lastz
    lastz/
    lastz/README
    lastz/lastz_wrapper.py
    lastz/lastz_wrapper.xml
    lastz/lastz-distrib-1.02.00/
    lastz/lastz-distrib-1.02.00/src/
    lastz/lastz-distrib-1.02.00/src/Makefile
    lastz/lastz-distrib-1.02.00/src/version.mak
    lastz/lastz-distrib-1.02.00/src/lastz.c
    lastz/lastz-distrib-1.02.00/src/lastz.h
    ...
    </pre>
    <code>~/Desktop/galaxy_lastz_tool.tar.bz2</code> is now ready to be uploaded.
</p>

<p><strong>Editing Information, Categories, and Submitting For Approval</strong></p>

<p>
    Simply uploading a tool to the Community will not allow other users to find
    and download your tool.  It will need to be approved by an administrator
    before it appears in the tool list.
</p>
<p>
    After the tool has successfully uploaded, you will be redirected to the
    Edit Tool page.  Please provide a detailed description of what the tool
    does - this will be used by administrators to understand the tool before
    approving it for display on the site.  Once approved, this information will
    be displayed to users who view your tool.  In addition, the site
    administrators will have configured a number of categories with which you
    can associate your tool to make it easily findable by users looking to
    solve specific problems.  Please associate as many categories as are
    relevant to your tool.  You may change the description and associated
    categories as often as you'd like until you click the "<strong>Submit for
    approval</strong>" button.  Once submitted, the tool will be approved or
    rejected by an administrator.  Once approved, it will be visible to
    everyone.  At that point, the description and associated categories can
    only be changed by an administrator.
</p>
<p>
    Once the tool has been approved or rejected, you may upload a new version
    by browsing to the tool's "View Tool" page, clicking the context menu to
    the right of the tool's name, and selecting "Upload a new version."
</p>

<hr/>

<h3>Downloading and Installing Tools</h3>

<p>
    A tool's download link will send you the tool tar archive.  Once
    downloaded, unpack the tool on your local Galaxy instance's server:
    <pre>
    user@host:~% tar xvf galaxy_tool.tar
    ...
    user@host:~% tar zxvf galaxy_tool.tar.gz
    ...
    user@host:~% tar jxvf galaxy_tool.tar.bz2
    ...
    </pre>
    If the tar archive includes a README file, consult it for installation
    instructions.  If not, follow these basic steps:
    <ol>
        <li>Create a directory under <code>galaxy_dist/tools/</code> to house downloaded tool(s).</li>
        <li>In the new directory, place the XML and any script file(s) which were contained in the tar archive.</li>
        <li>If the tool includes binaries, you'll need to copy them to a directory on your <code>$PATH</code>.  If the tool depends on C binaries but does not come with them (only source), you'll need to compile the source first.</li>
        <li>Add the tool to <code>galaxy_dist/tool_conf.xml</code>.</li>
        <li>Restart the Galaxy server process.</li>
    </ol>
</p>

<p>
    We plan to implement a more direct method to install tools via the Galaxy
    administrator user interface instead of placing files on the filesystem and
    managing the <code>tool_conf.xml</code> file by hand.  In the meantime,
    this is the process.
</p>
