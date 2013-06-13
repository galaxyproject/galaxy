<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="shared"
    self.message_box_visible=False
%>
</%def>


<%def name="center_panel()">
    <div style="overflow: auto; height: 100%;">
        <div class="page-container" style="padding: 10px;">
            <h2>Launching a Galaxy Cloud Instance</h2>
%if error:
    <p>${error}</p>
%elif instance:
    %if kp_material:
        <h3>Very Important Key Pair Information</h3>
        <p>A new key pair named '${kp_name}' has been created in your AWS
        account and will be used to access this instance via ssh. It is
        <strong>very important</strong> that you save the following private key
        as it is not saved on this Galaxy instance and will be permanently lost
        once you leave this page.  To do this, save the following key block as
        a plain text file named '${kp_name}'.</p>
        <pre>${kp_material}</pre>
    %endif
    <p>The instance '${instance.id} has been successfully launched using the
    '${instance.image_id}' AMI.<br/>  Access it at <a
    href="http://${instance.public_dns_name}">http://${instance.public_dns_name}</a></p>
    <p>SSH access is available using your private key '${kp_name}'.</p>
%else:
    <p> Unknown failure, no instance.  Please refer to your AWS console at <a
    href="https://console.aws.amazon.com">https://console.aws.amazon.com</a></p>
%endif
        </div>
    </div>
</%def>

