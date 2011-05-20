<%namespace file="/message.mako" import="render_msg" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>

<%inherit file="${inherit(context)}"/>

<%
    if selected_upload_type == 'tool':
        title = 'Upload a tool archive'
        type_label = 'tool'
    elif selected_upload_type == 'toolsuite':
        title = 'Upload a tool suite archive'
        type_label = 'tool suite'
%>

<%def name="title()">
    ${title}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
    $( function() {
        $( "select[refresh_on_change='true']").change( function() {
            $( "#upload_form" ).submit();
        });
    });
    </script>
</%def>

<h2>${title}</h2>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${title}</div>
    <div class="toolFormBody">
    ## TODO: nginx
    <form id="upload_form" name="upload_form" action="${h.url_for( controller='tool_upload', action='upload' )}" enctype="multipart/form-data" method="post">
    %if replace_id is not None:
        <input type='hidden' name="replace_id" value="${replace_id}"/>
    %endif
    <div class="form-row">
        <label>Upload Type</label>
        <div class="form-row-input">
            ${upload_type_select_list.get_html()}
        </div>
        <div class="toolParamHelp" style="clear: both;">
            Need help creating a ${type_label} archive?  See details below.
        </div>
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>File:</label>
        <div class="form-row-input"><input type="file" name="file_data"/></div>
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Category</label>
        <div class="form-row-input">
            <select name="category_id" multiple>
                %for category in categories:
                    %if category.id in selected_categories:
                        <option value="${trans.security.encode_id( category.id )}" selected>${category.name}</option>
                    %else:
                        <option value="${trans.security.encode_id( category.id )}">${category.name}</option>
                    %endif
                %endfor
            </select>
        </div>
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>URL:</label>
        <div class="form-row-input"><input type="text" name="url" style="width: 100%;"/></div>
        <div class="toolParamHelp" style="clear: both;">
            Instead of uploading directly from your computer, you may instruct Galaxy to download the file from a Web or FTP address.
        </div>
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <input type="submit" class="primary-button" name="upload_button" value="Upload">
    </div>
    </form>
    </div>
</div>
<p/>
<div class="toolFormTitle">Creating an archive containing a tool or a suite of tools</div>
<p>
    A tool or tool suite archive is a tar-format file (bzipped or gzipped tar are valid) 
    containing all the files necessary to load the tool(s) into a Galaxy instance.
</p>
%if selected_upload_type == 'toolsuite':
    <h3>Tool Suite Archive</h3>
    <p>
        A tools suite must include a file named <code>suite_config.xml</code> which provides information about the id, name,
        version and description of the tool suite, as well as the id, name, version and description of each tool 
        in the suite.  Here is an example <code>suite_config.xml</code> file.
    </p>
    <p>
<pre>
    &lt;suite id="lastz_toolsuite" name="Suite of Lastz tools" version="1.0.0"&gt;
        &lt;description&gt;This suite contains all of my Lastz tools for Galaxy&lt;/description&gt;
        &lt;tool id="lastz_wrapper_2" name="Lastz" version="1.1.0"&gt;
            &lt;description&gt; map short reads against reference sequence&lt;/description&gt;
        &lt;/tool&gt;
        &lt;tool id="lastz_paired_reads_wrapper" name="Lastz paired reads" version="1.0.0"&gt;
            &lt;description&gt; map short paired reads against reference sequence&lt;/description&gt;
        &lt;/tool&gt;
    &lt;/suite&gt;
</pre>
    </p>
    </p>
    <p>
        New versions of the suite can be uploaded, replacing an older version of the suite, but the version attribute
        of the <suite> tag must be altered the same way that the version attribute of a single tool config must be altered
        if uploading a new version of a tool.
    </p>
    <p>
        The id, name and version attributes of each <tool> tag in the <code>suite_config.xml</code> file must exactly match the same
        attributes in each associated tool config in the archive or you will not be allowed to upload the archive.
    </p>
    <p>
        In addition to the <code>suite_config.xml</code> file, the archive must include all
        <a href="http://bitbucket.org/galaxy/galaxy-central/wiki/ToolConfigSyntax" target="_blank">tool config files</a>,
        executables, functional test data (if your tool config includes functional tests) and other files needed for each
        of the tools in your suite to function within Galaxy.  See the information about single tool archives below for
        additional hints to enable ease-of-use when others download your suite of tools.
    </p>
    <p>
        For example, to package the above Lastz suite of tools:
<pre>
    user@host:~% tar jcvf ~/Desktop/galaxy_lastz_toolsuite.tar.bz2 lastzsuite
    lastzsuite/
    lastzsuite/README
    lastzsuite/suite_config.xml
    lastzsuite/lastz_paired_reads_wrapper.py
    lastzsuite/lastz_paired_reads_wrapper.xml
    lastzsuite/lastz_wrapper.py
    lastzsuite/lastz_wrapper.xml
    lastzsuite/lastz-distrib-1.02.00/
    lastzsuite/lastz-distrib-1.02.00/src/
    lastzsuite/lastz-distrib-1.02.00/src/Makefile
    lastzsuite/lastz-distrib-1.02.00/src/version.mak
    lastzsuite/lastz-distrib-1.02.00/src/lastz.c
    lastzsuite/lastz-distrib-1.02.00/src/lastz.h
    ...
</pre>
        ~/Desktop/galaxy_lastz_tool.tar.bz2 is now ready to be uploaded.
    </p>
%endif
<h3>Single Tool Archive</h3>
<p>
    A single tool archive must include a
    <a href="http://bitbucket.org/galaxy/galaxy-central/wiki/ToolConfigSyntax" target="_blank">tool config file</a>
    and will probably also include a tool script.  If any steps are necessary to install your tool beyond the basic
    instructions below, include a README file to provide details.  If the tool (or parts of it) are written in C,
    the source code can be included (or put links to the source in the README).  Do not include pre-compiled binaries
    without source since Galaxy is run on a wide variety of platforms.  Also, if you are only wrapping or providing a
    Galaxy config for a tool that is not your own, be sure the license allows for redistribution before including any
    part of that tool in the archive.
</p>
<p>
    There are no requirements about the directory structure inside the archive, but for ease of use it's generally
    a good idea to put everything inside a sub-directory, instead of directly at the top level.
</p>
<p>
    For example, to package the Lastz tool's config file, Galaxy wrapper, and the C source:
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
    ~/Desktop/galaxy_lastz_tool.tar.bz2 is now ready to be uploaded.
</p>
<h3>Editing Information, Categories, and Submitting For Approval</h3>
<p>
    Simply uploading a tool to the Galaxy too shed will not allow other users to find and download your tool.  It will
    need to be approved by an administrator before it appears in the tool list.
</p>
<p>
    After your archive has successfully uploaded, you will be redirected to the Edit Tool page.  Provide a detailed
    description of what the tool does - this will be used by administrators to understand the tool before approving it
    for display on the site.  Once approved, this information will be displayed to users who view your tool.  In addition,
    the site administrators will have configured a number of categories with which you can associate your tool to make it
    easy to find by users looking to solve specific problems.  Associate as many categories as are relevant to your tool.
    You may change the description and associated categories as often as you'd like until you click the "<strong>Submit for
    approval</strong>" button.  Once submitted, the tool will be approved or rejected by an administrator.  If the tool is
    rejected, you will see information about why it was rejected, and you can make appropriate changes to the archive and
    re-submit it for approval.  When it is approved, your archive will be visible to everyone.  At that point, the description
    and associated categories can only be changed by an administrator.
</p>
<p>
    When the tool has been approved or rejected, you may upload a new version by browsing to the tool's "View Tool" page,
    clicking the "Tool actions" menu in the upper right corner of the page, and selecting "Upload a new version" from the
    menu.
</p>
<hr/>
<h3>Downloading and Installing Tools</h3>
<p>
    A tool's download link will send you the tool archive.  Once downloaded, unpack the tool on your local Galaxy instance's server:
<pre>
    user@host:~% tar xvf galaxy_lastz_tool.tar
    ...
    user@host:~% tar zxvf galaxy_lastz_tool.tar.gz
    ...
    user@host:~% tar jxvf galaxy_lastz_tool.tar.bz2
    ...
</pre>
    If the archive includes a README file, consult it for installation instructions.  If not, follow these basic steps:
    <ol>
        <li>Create a directory under <code>galaxy_dist/tools/</code> to house downloaded tool(s).</li>
        <li>In the new directory, place the XML and any script file(s) which were contained in the archive.</li>
        <li>
            If the tool includes binaries, you'll need to copy them to a directory on your <code>$PATH</code>.  If the tool depends on
            C binaries but does not come with them (only source), you'll need to compile the source first.
        </li>
        <li>Add the tool to <code>galaxy_dist/tool_conf.xml</code>.</li>
        <li>Restart your Galaxy server process.</li>
    </ol>
</p>
<p>
    In the near future, we plan to implement a more direct method to install tools via the Galaxy administrator user interface instead
    of placing files on the filesystem and manually managing the <code>tool_conf.xml</code> file.
</p>
