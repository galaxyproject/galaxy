##
## Base template for sharing an item with an individual user. Template expects the following parameters:
## (a) item - item to be shared.
##
<%!
    def inherit(context):
        if context.get('use_panels'):
            if context.get('webapp'):
                app_name = context.get('webapp')
            elif context.get('app'):
                app_name = context.get('app').name
            else:
                app_name = 'galaxy'
            return '/webapps/%s/base_panels.mako' % app_name
        else:
            return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%namespace file="./display_common.mako" import="*" />

##
## Page methods.
##

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
    self.overlay_visible=False
    self.message_box_class=""
    self.active_view=""
    self.body_class=""
%>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>
        ## If page is displayed in panels, pad from edges for readabilit.
        %if context.get('use_panels'):
        div#center
        {
            padding: 10px;
        }
        %endif
    </style>
</%def>


<%def name="center_panel()">
    ${self.body()}
</%def>

<%def name="body()">
    %if message:
    <%
    if messagetype is UNDEFINED:
        mt = "done"
    else:
        mt = messagetype
    %>
    <p />
    <div class="${mt}message">
        ${message}
    </div>
    <p />
    %endif

    <%
        #
        # Setup and variables needed for page.
        #

        # Get class name strings.
        item_class_name = get_class_display_name( item.__class__ )
        item_class_name_lc = item_class_name.lower()
        item_class_plural_name = get_class_plural_display_name( item.__class__ )
        item_class_plural_name_lc = item_class_plural_name.lower()
        item_controller = get_controller_name(item)

        # Get item name.
        item_name = get_item_name(item)
    %>

    <div class="card">
        <div class="card-header">Share ${item_class_name} '${item_name | h}' with Another User</div>
            <div class="card-body">
                <form action="${h.url_for(controller=item_controller, action='share', id=trans.security.encode_id( item.id ) )}" method="POST">
                    <div class="form-row">
                        <label>
                            Email address of user to share with
                        </label>
                        <div style="float: left; width: 100%;  margin-right: 10px;">
                            %if trans.app.config.expose_user_email or trans.app.config.expose_user_name or trans.user_is_admin:
                            <input type="hidden" id="email_select" name="email" >
                            </input>
                            %else:
                            <input type="text" name="email" value="${email | h}" size="40">
                            </input>
                            %endif
                        </div>

                        <div style="clear: both"></div>
                    </div>
                    <div class="form-row">
                        <input type="submit" value="Share"></input>
                    </div>
                    <div class="form-row">
                        %if item_class_name == "Workflow":
                        <a href="${h.url_for(controller="", action="workflow/sharing", id=trans.security.encode_id( item.id ) )}">Back to ${item_class_name}'s Sharing Home</a>
                        %else:
                        <a href="${h.url_for(controller="", action="%s/sharing" % item_class_plural_name_lc, id=trans.security.encode_id( item.id ) )}">Back to ${item_class_name}'s Sharing Home</a>
                        %endif
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script type="text/javascript">
    /*  This should be ripped out and made generic at some point for the
     *  various API bindings available, and once the API can filter list
     *  queries (term, below) */

    var user_id = "${trans.security.encode_id(trans.user.id)}";

    function item_to_label(item){
        var text = "";
        if(typeof(item.username) === "string" && typeof(item.email) === "string"){
            text = item.username + " <" + item.email + ">";
        }else if(typeof(item.username) === "string"){
            text = item.username;
        }else{
            text = item.email;
        }
        return text;
        //return "id:" + item.id + "|e:" + item.email + "|u:" + item.username;
    }

    $("#email_select").select2({
        placeholder: "Select a user",
	width: "33%",
        multiple: false,
        initSelection: function(element, callback) {
            var data = [];
            callback(data);
        },
        // Required for initSelection
        id: function(object) {
            return object.id;
        },
        ajax: {
            url: "${h.url_for(controller="/api/users", action="index")}",
            data: function (term) {
                return {
                    f_any: term,
                };
            },
            dataType: 'json',
            quietMillis: 250,
            results: function (data) {
                var results = [];
                // For every user returned by the API call,
                $.each(data, function(index, item){
                    // If they aren't the requesting user, add to the
                    // list that will populate the select
                    if(item.id != "${trans.security.encode_id(trans.user.id)}"){
                        // Because we "share-by-email", we can ONLY add a
                        // result if we can see the email. Hopefully someday
                        // someone will allow sharing by Galaxy user ID (or
                        // something else "opaque" and people will be able to
                        // share-by-username.)
                        if(item.email !== undefined){
                            results.push({
                              id: item.email,
                              name: item.username,
                              text: item_to_label(item),
                            });
                        }
                    }
                });
                return {
                    results: results
                };
            }
        },
        createSearchChoice: function(term, data) {
            // Check for a user with a matching email.
            var matches = _.filter(data, function(user){
                return user.text.indexOf(term) > -1;
            });
            // If there aren't any users with matching object labels, then
            // display a "default" entry with whatever text they're entering.
            // id is set to term as that will be used in
            if(matches.length == 0){
                return {id: term, text:term};
            }else{
                // No extra needed
            }
        }
    });
    </script>
</%def>
