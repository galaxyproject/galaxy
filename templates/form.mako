<%inherit file="/base.mako"/>
<%def name="title()">${form.title}</%def>

<%def name="javascripts()">
${parent.javascripts()}
<script type="text/javascript">
$(function(){
    $("input:text:first").focus();
})
</script>
</%def>

%if header:
    ${header}
%endif

<div class="form">
    <div class="form-title">${form.title}</div>
    <div class="form-body">
        <form name="${form.name}" action="${form.action}" method="post" >
            %for input in form.inputs:
                <%
                cls = "form-row"
                if input.error:
                    cls += " form-row-error"
                %>
                <div class="${cls}">
                  %if input.use_label:
                  <label>
                      ${input.label}:
                  </label>
                  %endif
                  <div class="form-row-input">
                      <input type="${input.type}" name="${input.name}" value="${input.value}" size="40">
                  </div>
                  %if input.error:
                  <div class="form-row-error-message">${input.error}</div>
                  %endif
    
                  %if input.help:
                  <div class="toolParamHelp" style="clear: both;">
                      ${input.help}
                  </div>
                  %endif
    
                  <div style="clear: both"></div>
    
                </div>
            %endfor
            <div class="form-row"><input type="submit" value="${form.submit_text}"></div>
    
        </form>
    </div>
</div>
