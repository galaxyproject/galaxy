<%inherit file="/base.mako"/>

%if msg:
    <p class="ok_bgr">${msg}</p></td></tr>
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create a new library</div>
    <div class="toolFormBody">
        <form name="library" action="/admin/library" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="New Library" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="description" value="" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="new" value="submitted" size="40"/>
                </div>
              <div style="clear: both"></div>
            </div>
            <input type="submit" name="create_library_button" value="Create"/>
        </form>
    </div>
</div>
