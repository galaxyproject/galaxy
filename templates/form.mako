<%!
    def inherit(context):
        if context.get('use_panels') is True:
            print "here"
            return '/webapps/galaxy/base_panels.mako'
        else:
            return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>
<% _=n_ %>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view=active_view
    self.message_box_visible=False
%>
</%def>


<%def name="title()">${form.title}</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        $(function(){
            $("input:text:first").focus();
        })
    </script>
</%def>

<%def name="center_panel()">
    ${render_form( )}
</%def>

<%def name="body()">
    ${render_form( )}
</%def>

<%def name="render_form()">
    %if header:
        ${header}
    %endif
    
    <div class="form" style="margin: 1em">
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
                      ${_(input.label)}:
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
</%def>