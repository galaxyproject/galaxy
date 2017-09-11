define( [ 'libs/vue', "libs/toastr" ], function( Vue, mod_toastr ) {

    var UserAPIKeysView = Backbone.View.extend({
        initialize: function() {
            mod_toastr.options.timeOut = 1000;
            this.setElement( '<div/>' );
            this.render();
        },

        render: function() {
            var self = this,
                url = Galaxy.root + 'userskeys/all_users';
            self.$el.empty().append( self._template() );
            self.fetchUsers( url );
        },

        /** Load users and their keys */
        fetchUsers: function( url ) {
            var self = this;
            $.getJSON( url, function( users ) {
                // apply vue model on the dom
                // timeout is used to ensure dom is created first and then
                // vue model is applied with the required data
                setTimeout(function() { 
                    self.applyVue( users );
                });
            });
        },

        /** Create model for the view using vue */
        applyVue: function( users ) {
            var form_vue = new Vue({
                el: '#form-userkeys',
                data: {
                    users: users // data model
                },
                methods: {
                    // bind event from view
                    generateKey: function( id ) {
                        var self = this;
                        // fetch fresh model
                        $.ajax({
                            url: Galaxy.root + 'userskeys/admin_api_keys',
                            data: { 'uid': id },
                            success: function( users ) {
                                mod_toastr.success("Successfully generated a user key");
                                // refresh the model
                                self._data.users = users;
                            },
                            error: function( ) {
                                mod_toastr.success("Error occured while loading data");
                            }
                        });
                    }
                }
            });
        },

        _template: function() {
            return '<div id="form-userkeys" class="toolForm" v-cloak>' +
                       '<div class="toolFormTitle">User Information</div>' +
                       '<div v-if="users && users.length > 0">' +
                           '<table class="grid">' +
                               '<thead><th>Encoded UID</th><th>Email</th><th>API Key</th><th>Actions</th></thead>' +
                               '<tbody>' +
                                   '<tr v-for="user in users">' +
                                       '<td>' + '{{ user.uid }}' + '</td>' +
                                       '<td>' + '{{ user.email }}' + '</td>' +
                                       '<td>' + '{{ user.key }}' + '</td>' +
                                       '<td>' +
                                           '<input type="button" value="Generate a new key now" v-on:click="generateKey( user.uid )" />' +
                                       '</td>' +
                               '</tbody>' +
                           '</table>' +
                       '</div>' +
                       '<div v-else>' +
                           '<div>No informations available</div>' +
                       '</div>' +
                       '<div style="clear: both"></div>' +
                   '</div>';
        }
    });

    return {
        View: UserAPIKeysView
    };
});
