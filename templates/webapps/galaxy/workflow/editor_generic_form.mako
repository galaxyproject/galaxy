<form name="${form.name}" action="${h.url_for( action='editor_form_post' )}" method="post">
    <div class="toolForm">
        <div class="toolFormTitle">${form.title}</div>
        <div class="toolFormBody">
            <input type="hidden" name="type" value="${module.type}" />
            %if form.inputs:
              %for input in form.inputs:
                  <%
                  cls = "form-row"
                  if input.error:
                      cls += " form-row-error"
                  %>
                  <div class="${cls}">
                    <label>
                        ${input.label}:
                    </label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="${input.type}" name="${input.name | h}" value="${input.value | h}" size="30">
                    </div>
                    %if input.error:
                    <div style="float: left; color: red; font-weight: bold; padding-top: 1px; padding-bottom: 3px;">
                        <div style="width: 300px;"><img style="vertical-align: middle;" src="${h.url_for('/static/style/error_small.png')}">&nbsp;<span style="vertical-align: middle;">${input.error}</span></div>
                    </div>
                    %endif
  
                    %if input.help:
                    <div class="toolParamHelp" style="clear: both;">
                        ${input.help}
                    </div>
                    %endif
  
                    <div style="clear: both"></div>
  
                  </div>
              %endfor
            %else:
              <div class="form-row"><i>No options</i></div>
            %endif
            </table>
        </div>
    </div>
</form>
