<%inherit file="/base.mako"/>
<% from galaxy.util import nice_size %>

<style>
    .inherit {
        border: 1px solid #bbb;
        padding: 15px;
        text-align: center;
        background-color: #eee;
    }
</style>

<%def name="inputs_recursive( input_params, param_values, depth=1 )">
  %for input_index, input in enumerate( input_params.itervalues() ):
    %if input.type == "repeat":
      %for i in range( len(param_values[input.name]) ):
        ${ inputs_recursive(input.inputs, param_values[input.name][i], depth=depth+1) }
      %endfor
    %elif input.type == "conditional":
      <% current_case = param_values[input.name]['__current_case__'] %>
        <tr>
          <td>${input.label}</td>
          <td>${current_case}</td>
        </tr>
        ${ inputs_recursive(input.cases[current_case].inputs, param_values[input.name], depth=depth+1) }
    %elif getattr(input, "label", None):
      <tr>
        <td>${input.label}</td>
        <td>${input.value_to_display_text(param_values[input.name], trans.app)}</td>
      </tr>
    %endif
  %endfor
</%def>

<table class="tabletip">
    <thead>
        <tr><th colspan="2" style="font-size: 120%;">
            % if tool:
                Tool: ${tool.name}
            % else:
                Unknown Tool
            % endif
        </th></tr>
    </thead>
    <tbody>
        <tr><td>Name:</td><td>${hda.name}</td></tr>
        <tr><td>Created:</td><td>${hda.create_time.strftime("%b %d, %Y")}</td></tr>
        ##      <tr><td>Copied from another history?</td><td>${hda.source_library_dataset}</td></tr>
        <tr><td>Filesize:</td><td>${nice_size(hda.dataset.file_size)}</td></tr>
        <tr><td>Dbkey:</td><td>${hda.dbkey}</td></tr>
        <tr><td>Format:</td><td>${hda.ext}</td></tr>
        <tr><td>Tool Version:</td><td>${hda.tool_version}</td></tr>
        <tr><td>Tool Standard Output:</td><td><a href="${h.url_for( controller='dataset', action='stdout')}">stdout</a></td></tr>
        <tr><td>Tool Standard Error:</td><td><a href="${h.url_for( controller='dataset', action='stderr')}">stderr</a></td></tr>
        %if trans.user_is_admin() or trans.app.config.expose_dataset_path:
            <tr><td>Full Path:</td><td>${hda.file_name}</td></tr>
        %endif
</table>
<br />
<table class="tabletip">
    <thead>
        <tr>
            <th>Input Parameter</th>
            <th>Value</th>
        </tr>
    </thead>
    <tbody>
        % if params_objects and tool:
            ${ inputs_recursive(tool.inputs, params_objects, depth=1) }
        % else:
            <tr><td colspan="2">No parameters.</td></tr>
        % endif
    </tbody>
</table>


    <h3>Inheritance Chain</h3>
    <div class="inherit" style="background-color: #fff; font-weight:bold;">${hda.name}</div>

    % for dep in inherit_chain:
    <div style="font-size: 36px; text-align: center;">&uarr;</div>
    <div class="inherit">${dep[0].name}<br/>${dep[1]}</div>
    % endfor

