<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

%if emails:
    <div class="toolForm">
        <div class="toolFormTitle">Impersonate another user</div>
        <div class="toolFormBody">
        <form name="impersonate" id="impersonate" action="${h.url_for( controller='admin', action='impersonate' )}" method="post" >
            <div class="form-row">
                <label>
                    User to impersonate:
                </label>
                <input type="hidden" id="email_select" name="email">
                </input>
            </div>
            <div class="form-row">
                <input type="submit" name="impersonate_button" value="Impersonate"/>
            </div>
        </form>
        </div>
    </div>
    <script type="text/javascript">
    /*  This should be ripped out and made generic at some point for the
     *  various API bindings available, and once the API can filter list
     *  queries (term, below) */
    $("#email_select").select2({
        placeholder: "Select a user",
        ajax: {
            url: "${h.url_for(controller="/api/users", action="index")}",
            dataType: 'json',
            quietMillis: 250,
            matcher: function(term, text) { return text.toUpperCase().indexOf(term.toUpperCase())>=0; },
            data: function (term) {
                return {
                    f_email: term
                };
            },
            results: function (data) {
              var results = [];
              $.each(data, function(index, item){
                    results.push({
                      id: item.email,
                      text: item.email
                    });
              });
              return {
                  results: results
              };
            }
        }
    });
    </script>
%endif
