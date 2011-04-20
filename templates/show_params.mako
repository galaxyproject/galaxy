<%inherit file="/base.mako"/>
<% from galaxy.util import nice_size %>

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
    <tr><th colspan="2" style="font-size: 120%;">${tool.name}</th></tr>
  </thead>
  <tbody>
    <tr><td>Created:</th><td>${history.create_time.strftime("%b %d, %Y")}</td></tr>
##      <tr><td>Copied from another history?</td><td>${hda.source_library_dataset}</td></tr>
    <tr><td>Filesize:</th><td>${nice_size(hda.dataset.file_size)}</td></tr>
    <tr><td>Dbkey:</th><td>${hda.dbkey}</td></tr>
    <tr><td>Format:</th><td>${hda.ext}</td></tr>
    
</table><br />
<table class="tabletip">
  <thead>
    <tr>
      <th>Input Parameter</th>
      <th>Value</th>
    </tr>
  </thead>
  <tbody>
      ${ inputs_recursive(tool.inputs, params_objects, depth=1) }
  </tbody>
</table>
