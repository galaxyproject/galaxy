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
    #hidden_options{
        display:none;
    }
    #loading_indicator{
            position:fixed;
            top:40px;
    }
    </style>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        var ACCOUNT_URL = "${h.url_for( controller='/cloudlaunch', action='get_account_info')}";
        var PKEY_DL_URL = "${h.url_for( controller='/cloudlaunch', action='get_pkey')}";
        var cloudlaunch_clusters = [];

        $(document).ready(function(){
            $('#id_existing_instance').change(function(){
                var ei_name = $(this).val();
                if (ei_name === "New Cluster"){
                    //For new instances, need to see the cluster name field.
                    $('#id_cluster_name').val("New Cluster")
                    $('#cluster_name_wrapper').show('fast');
                }else{
                    //Hide the Cluster Name field, but set the value
                    $('#id_cluster_name').val($(this).val());
                    $('#cluster_name_wrapper').hide('fast');
                }
            });
             //When id_secret and id_key are complete, submit to get_account_info
            $("#id_secret, #id_key_id").bind("paste input propertychange", function(){
                secret_el = $("#id_secret");
                key_el = $("#id_key_id");
                if (secret_el.val().length === 40 && key_el.val().length === 20){
                    //Clear errors
                    $('.errormessage').remove()
                    //Submit these to get_account_info, unhide fields, and update as appropriate
                    $.ajax({type: "POST",
                            url: ACCOUNT_URL,
                            dataType: 'json',
                            data: {key_id: key_el.val(),secret:secret_el.val()},
                            success: function(result){
                                    cloudlaunch_clusters = result.clusters;
                                    var kplist = $("#id_keypair");
                                    var clusterlist = $("#id_existing_instance");
                                    kplist.find('option').remove();
                                    clusterlist.find('option').remove();
                                    //Update fields with appropriate elements
                                    clusterlist.append($('<option/>').val('New Cluster').text('New Cluster'));
                                    if (_.size(result.clusters) > 0){
                                        _.each(result.clusters, function(cluster, index){
                                            clusterlist.append($('<option/>').val(cluster.cluster_name).text(cluster.cluster_name));
                                        });
                                        $('#existing_instance_wrapper').show();
                                    }
                                    if (!_.include(result.keypairs, '${default_keypair}')){
                                        kplist.append($('<option/>').val('${default_keypair}').text('Create New - ${default_keypair}'));
                                    }
                                    _.each(result.keypairs, function(keypair, index){
                                        kplist.append($('<option/>').val(keypair).text(keypair));
                                    });
                                    $('#hidden_options').show('fast');
                                },
                            error: function(jqXHR, textStatus, errorThrown){
                                 //Show error message
                                 $('#launchFormContainer').prepend('<div class="errormessage">' + errorThrown + " : " + jqXHR.responseText + '</div>');
                                 //Hide the options form
                                 $('#hidden_options').hide('fast');
                                }
                            });
                }
            });
            $(document).ajaxStart(function(){
                $('#loading_indicator').show('fast');
            }).ajaxStop(function(){
                $('#loading_indicator').hide('fast');
            });
            $('form').ajaxForm({
                    type: 'POST',
                    dataType: 'json',
                    beforeSubmit: function(data, form){
                        // Dig up placement info for selected cluster, set hidden input.
                        // This is not necessary to present to the user though the interface may prove useful.
                        var ei_val = _.find(data, function(f_obj){return f_obj.name === 'existing_instance'});
                        if( ei_val && (ei_val.value !== "New Cluster")){
                            var cluster = _.find(cloudlaunch_clusters, function(cluster){return cluster.cluster_name === ei_val.value});
                            var placement_field = _.find(data, function(f_obj){return f_obj.name === 'placement'});
                            placement_field.value = cluster.placement;
                        }else if($('#id_cluster_name').val() === ''){
                            // If we're not using an existing cluster, this must be set.
                            form.prepend('<div class="errormessage">You must specify a cluster name</div>');
                            return false;
                        }
                        if ($('#id_password').val() != $('#id_password_confirm').val()){
                            //Passwords don't match.
                            form.prepend('<div class="errormessage">Passwords do not match</div>');
                            return false;
                        }
                        // Lastly, clear errors and flip to the response panel.
                        $('.errormessage').remove()
                        $('#launchFormContainer').hide('fast');
                        $('#responsePanel').show('fast');
                    },
                    success: function(data){
                        // Success Message, link to key download if required, link to server itself.
                        $('#launchPending').hide('fast');
                        //Set appropriate fields (dns, key, ami) and then display.
                        if(data.kp_material_tag){
                            var kp_download_link = $('<a/>').attr('href', PKEY_DL_URL + '?kp_material_tag=' + data.kp_material_tag)
                                                            .attr('target','_blank')
                                                            .text("Download your key now");
                            $('#keypairInfo').append(kp_download_link);
                            $('#keypairInfo').show();
                        }
                        $('.kp_name').text(data.kp_name);
                        $('#instance_id').text(data.instance_id);
                        $('#image_id').text(data.image_id);
                        $('#instance_link').html($('<a/>')
                            .attr('href', 'http://' + data.public_dns_name + '/cloud')
                            .attr('target','_blank')
                            .text(data.public_dns_name + '/cloud'));
                        $('#instance_dns').text(data.public_dns_name);
                        $('#launchSuccess').show('fast');
                    },
                    error: function(jqXHR, textStatus, errorThrown){
                       $('#launchFormContainer').prepend('<div class="errormessage">' + errorThrown + " : " + jqXHR.responseText + '</div>');
                       $('#responsePanel').hide('fast');
                       $('#launchFormContainer').show('fast');
                    }
            });
        });
    </script>
</%def>

<%def name="center_panel()">
    <div style="overflow: auto; height: 100%;">
        <div class="page-container" style="padding: 10px;">
        <div id="loading_indicator"></div>
            <h2>Launch a Galaxy Cloud Instance</h2>
              <div id="launchFormContainer">
                    <form id="cloudlaunch_form" action="${h.url_for( controller='/cloudlaunch', action='launch_instance')}" method="post">

                    <p>To launch a Galaxy Cloud Cluster, enter your AWS Secret
                    Key ID, and Secret Key.  Galaxy will use these to present
                    appropriate options for launching your cluster.  Note that
                    using this form to launch computational resources in the
                    Amazon Cloud will result in costs to the account indicated
                    above.
                    See <a href="http://aws.amazon.com/ec2/pricing/">Amazon's
                    pricing</a> for more information.</p>

                    <div class="form-row">
                        <label for="id_key_id">Key ID</label>
                        <input type="text" size="30" maxlength="20" name="key_id" id="id_key_id" value="" tabindex="1"/><br/>
                        <div class="toolParamHelp">
                            This is the text string that uniquely identifies your account, found in the
                            <a href="https://portal.aws.amazon.com/gp/aws/securityCredentials">Security Credentials section of the AWS Console</a>.
                        </div>
                    </div>

                    <div class="form-row">
                        <label for="id_secret">Secret Key</label>
                        <input type="text" size="50" maxlength="40" name="secret" id="id_secret" value="" tabindex="2"/><br/>
                        <div class="toolParamHelp">
                            This is your AWS Secret Key, also found in the <a href="https://portal.aws.amazon.com/gp/aws/securityCredentials">Security
Credentials section of the AWS Console</a>.  </div>
                    </div>

                    <div id="hidden_options">
                        %if not share_string:
                        <div id='existing_instance_wrapper' style="display:none;" class="form-row">
                                <label for="id_existing_instance">Instances in your account</label>
                                <select name="existing_instance" id="id_existing_instance" style="min-width: 228px">
                                </select>
                                <input id='id_placement' type='hidden' name='placement' value=''/>
                        </div>
                        %endif
                        <div id='cluster_name_wrapper' class="form-row">
                            <label for="id_cluster_name">Cluster Name</label>
                            <input type="text" size="40" class="text-and-autocomplete-select" name="cluster_name" id="id_cluster_name"/><br/>
                            <div class="toolParamHelp">
                                This is the name for your cluster.  You'll use this when you want to restart.
                            </div>
                        </div>

                        <div class="form-row">
                            <label for="id_password">Cluster Password</label>
                            <input type="password" size="40" name="password" id="id_password"/><br/>
                        </div>

                        <div class="form-row">
                            <label for="id_password_confirm">Cluster Password - Confirmation</label>
                            <input type="password" size="40" name="password_confirm" id="id_password_confirm"/><br/>
                        </div>


                        <div class="form-row">
                            <label for="id_keypair">Key Pair</label>
                            <select name="keypair" id="id_keypair" style="min-width: 228px">
                                <option name="Create" value="cloudman_keypair">cloudman_keypair</option>
                            </select>
                        </div>

                        %if share_string:
                            <input type='hidden' name='share_string' value='${share_string}'/>
                        %else:
                        <!-- DBEDIT temporary hide share string due to it being broken on the cloudman end -->
                        <div class="form-row" style="display:none;">
                            <label for="id_share_string">Instance Share String (optional)</label>
                            <input type="text" size="120" name="share_string" id="id_share_string"/><br/>
                        </div>
                        %endif

                        %if ami:
                            <input type='hidden' name='ami' value='${ami}'/>
                        %endif

                        %if bucket_default:
                            <input type='hidden' name='bucket_default' value='${bucket_default}'/>
                        %endif

                        <div class="form-row">
                            <label for="id_instance_type">Instance Type</label>
                            <select name="instance_type" id="id_instance_type">
                            %for (itype, description) in instance_types:
                                <option value="${itype}">${description}</option>
                            %endfor
                            </select>
                        </div>
                        <div class="form-row">
                            <p>Requesting the instance may take a moment, please be patient.  Do not refresh your browser or navigate away from the page</p>
                            <input type="submit" value="Submit" id="id_submit"/>
                        </div>
                    </div>
                        <div class="form-row">
                        <div id="loading_indicator" style="position:relative;left:10px;right:0px"></div>
                        </div>
                    </form>
                </div>
                <div id="responsePanel" style="display:none;">
                        <div id="launchPending">Launch Pending, please be patient.</div>
                        <div id="launchSuccess" style="display:none;">
                            <div id="keypairInfo" style="display:none;margin-bottom:20px;">
                                <h3>Very Important Key Pair Information</h3>
                                <p>A new key pair named <strong><span class="kp_name">kp_name</span></strong> has been created in your AWS
                                account and will be used to access this instance via ssh. It is
                                <strong>very important</strong> that you save the following private key
                                as it is not saved on this Galaxy instance and will be permanently lost if not saved.  Additionally, this link will
                                only allow a single download, after which the key is removed from the Galaxy server permanently.<br/>
                            </div>
                            <div>
                                <h3>Access Information</h3>
                                <ul>
                                    <li>Your instance '<span id="instance_id">undefined</span>' has been successfully launched using the
                                '<span id="image_id">undefined</span>' AMI.</li>
                                <li>While it may take a few moments to boot, you will be able to access the cloud control
                                panel at <span id="instance_link">undefined.</span>.</li>
                            <li>SSH access is also available using your private key.  From the terminal, you would execute something like:</br>&nbsp;&nbsp;&nbsp;&nbsp;`ssh -i <span class="kp_name">undefined</span>.pem ubuntu@<span
id="instance_dns">undefined</span>`</li>
                                </ul>
                        </div>
                </div>
        </div>
    </div>
</%def>

