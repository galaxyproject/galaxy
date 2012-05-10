<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="shared"
    self.message_box_visible=False
%>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging" )}
    <style type="text/css">
    #new_history_p{
        line-height:2.5em;
        margin:0em 0em .5em 0em;
    }
    #new_history_cbx{
        margin-right:.5em;
    }
    #new_history_input{
        display:none;
        line-height:1em;
    }
    #ec_button_container{
        float:right;
    }
    div.toolForm{
        margin-top: 10px;
        margin-bottom: 10px;
    }
    div.toolFormTitle{
        cursor:pointer;
    }
    .title_ul_text{
        text-decoration:underline;
    }
    .step-annotation {
        margin-top: 0.25em;
        font-weight: normal;
        font-size: 97%;
    }
    .workflow-annotation {
        margin-bottom: 1em;
    }
    </style>
</%def>




<%def name="center_panel()">
    <div style="overflow: auto; height: 100%;">
        <div class="page-container" style="padding: 10px;">
            <h2>Launch a Galaxy Cloud Instance</h2>
              <div class="toolForm">
                    <form action="cloud/launch_instance" method="post">
                    <div class="form-row">
                        <label for="id_cluster_name">Cluster Name</label>
                        <input type="text" size="80" name="cluster_name" id="id_cluster_name"/><br/>
                    </div>
                    <div class="form-row">
                        <label for="id_password">Password</label>
                        <input type="password" size="40" name="password" id="id_password"/><br/>
                    </div>
                    <div class="form-row">
                        <label for="id_key_id">Key ID</label>
                        <input type="text" size="40" name="key_id" id="id_key_id"/><br/>
                    </div>
                    <div class="form-row">
                        <label for="id_secret">Secret Key</label>
                        <input type="password" size="120" name="secret" id="id_secret"/><br/>
                    </div>
                    <div class="form-row">
                        <label for="id_instance_type">Instance Type</label>
                        <select name="instance_type" id="id_instance_type">
                            <option value="m1.large">Large</option>
                            <option value="t1.micro">Micro</option>
                            <option value="m1.xlarge">Extra Large</option>
                            <option value="m2.4xlarge">High-Memory Quadruple Extra Large</option>
                        </select>
                    </div>
                    <div class="form-row">
                        <p>Requesting the instance may take a moment, please be patient.  Do not refresh your browser or navigate away from the page</p>
                        <input type="submit" value="Submit" id="id_submit"/>
                    </div>
                    </form>
                </div>
        </div>
    </div>
</%def>

