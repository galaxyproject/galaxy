<%inherit file="/base.mako"/>

%if msg:
    <p class="ok_bgr">${msg}</p></td></tr>
%endif

<div class="toolForm">
    <div class="toolFormTitle">Edit library name and description</div>
    <div class="toolFormBody">
        <form name="library" action="/admin/library" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="${library.name}" size="40">
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="description" value="${library.description}" size="40">
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Also change the root folder's name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="checkbox" name="root_folder" value="" size="40">
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="rename" value="submitted" size="40">
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="id" value="${library.id}" size="40">
                </div>
                <div style="clear: both"></div>
            </div>
            <input type="submit" name="rename_library_button" value="Save">
        </form>
    </div>
</div>
