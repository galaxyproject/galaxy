<form name="${form.name}" action="${h.url_for( controller='workflow', action='editor_form_post' )}" method="post">
    <%
    from xml.sax.saxutils import escape
    label = module.label
    if label is not None:
        title = label
    else:
        title = form.title
    %>
    <div class="ui-portlet-narrow">
        <div class="portlet-header">
          <div class="portlet-title">
            <span class="portlet-title-text"><b>${title}</b></span>
          </div>
        </div>
        <div class="portlet-content">
          <div class="content">
            <div class="ui-margin-top"></div>
            <div>
            <input type="hidden" name="type" value="${module.type}" />
            <input type="hidden" name="label" value="${escape(label or '')}" />
            <table class="ui-table-plain">
              <thead></thead>
              <tbody>
            %if form.inputs:
              %for input in form.inputs:
                  <%
                  cls = "section-row"
                  if input.error:
                      cls += " form-row-error"
                  extra_attributes = ""
                  for key, value in getattr( input, "extra_attributes", {} ).iteritems():
                      extra_attributes += " %s=\"%s\"" % ( key, value )
                  type_attribute = ""
                  if input.type:
                    type_attribute = "type=\"input.type\""
                  %>
                  <tr class="${cls}"><td><div class="ui-table-form-element">
                    <div class="ui-table-form-title">
                        ${input.label}:
                    </div>
                    <div class="ui-table-form-field" style="display: block;">
                        <input ${type_attribute} name="${input.name | h}" value="${input.value | h}" size="30" ${extra_attributes}>
                        %if hasattr( input, "body_html" ):
                              ${input.body_html()}
                            </input>
                        %endif
                      %if input.error:
                      <div style="float: left; color: red; font-weight: bold; padding-top: 1px; padding-bottom: 3px;">
                          <div style="width: 300px;"><img style="vertical-align: middle;" src="${h.url_for('/static/style/error_small.png')}">&nbsp;<span style="vertical-align: middle;">${input.error}</span></div>
                      </div>
                      %endif
  
                      %if input.help:
                      <div class="ui-table-form-info">
                          ${input.help}
                      </div>
                      %endif
                    </div><!-- ui-table-form-field -->
  
                  </div></td></tr>
              %endfor
            %else:
              <div class="form-row"><i>No options</i></div>
            %endif
              </tbody>
            </table>
          </div> <!-- content -->
        </div><!-- portlet-content -->
    </div>
</form>
