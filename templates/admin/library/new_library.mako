<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create a new data library</div>
    <div class="toolFormBody">
        <form name="library" action="${h.url_for( controller='library_admin', action='create_library' )}" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="New data library" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="description" value="" size="40"/>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    Displayed when browsing all libraries
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Synopsis:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="synopsis" value="" size="40"/>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    Displayed when browsing this library
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="create_library_button" value="Create"/>
            </div>
        </form>
    </div>
</div>
