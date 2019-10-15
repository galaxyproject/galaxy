/** User Preferences view */
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";

/** TODO delete this model */
const Model = Backbone.Model.extend({
    initialize: function(options) {
        const Galaxy = getGalaxyInstance();
        options = options || {};
        options.user_id = options.user_id || Galaxy.user.id;
        this.set({
            user_id: options.user_id,
            information: {
                title: _l("Manage information"),
                description: "Edit your email, addresses and custom parameters or change your public name.",
                url: `api/users/${options.user_id}/information/inputs`,
                icon: "fa-user",
                redirect: "user"
            },
            password: {
                title: _l("Change password"),
                description: _l("Allows you to change your login credentials."),
                icon: "fa-unlock-alt",
                url: `api/users/${options.user_id}/password/inputs`,
                submit_title: "Save password",
                redirect: "user"
            },
            communication: {
                title: _l("Change communication settings"),
                description: _l("Enable or disable the communication feature to chat with other users."),
                url: `api/users/${options.user_id}/communication/inputs`,
                icon: "fa-comments-o",
                redirect: "user"
            },
            permissions: {
                title: _l("Set dataset permissions for new histories"),
                description:
                    "Grant others default access to newly created histories. Changes made here will only affect histories created after these settings have been stored.",
                url: `api/users/${options.user_id}/permissions/inputs`,
                icon: "fa-users",
                submit_title: "Save permissions",
                redirect: "user"
            },
            make_data_private: {
                title: _l("Make all data private"),
                description: _l("Click here to make all data private."),
                icon: "fa-lock",
                onclick: function() {
                    if (
                        confirm(
                            _l(
                                "WARNING: This will make all datasets (excluding library datasets) for which you have " +
                                    "'management' permissions, in all of your histories " +
                                    "private, and will set permissions such that all " +
                                    "of your new data in these histories is created as private.  Any " +
                                    "datasets within that are currently shared will need " +
                                    "to be re-shared or published.  Are you sure you " +
                                    "want to do this?"
                            )
                        )
                    ) {
                        $.post(`${Galaxy.root}history/make_private`, { all_histories: true }, () => {
                            Galaxy.modal.show({
                                title: _l("Datasets are now private"),
                                body: `All of your histories and datsets have been made private.  If you'd like to make all *future* histories private please use the <a href="${
                                    Galaxy.root
                                }user/permissions">User Permissions</a> interface.`,
                                buttons: {
                                    Close: function() {
                                        Galaxy.modal.hide();
                                    }
                                }
                            });
                        });
                    }
                }
            },
            api_key: {
                title: _l("Manage API key"),
                description: _l("Access your current API key or create a new one."),
                url: `api/users/${options.user_id}/api_key/inputs`,
                icon: "fa-key",
                submit_title: "Create a new key",
                submit_icon: "fa-check"
            },
            cloud_auth: {
                title: _l("Manage Cloud Authorization"),
                description: _l(
                    "Add or modify the configuration that grants Galaxy to access your cloud-based resources."
                ),
                icon: "fa-cloud",
                submit_title: "Create a new key",
                submit_icon: "fa-check"
            },
            toolbox_filters: {
                title: _l("Manage Toolbox filters"),
                description: _l("Customize your Toolbox by displaying or omitting sets of Tools."),
                url: `api/users/${options.user_id}/toolbox_filters/inputs`,
                icon: "fa-filter",
                submit_title: "Save filters",
                redirect: "user"
            },
            custom_builds: {
                title: _l("Manage custom builds"),
                description: _l("Add or remove custom builds using history datasets."),
                icon: "fa-cubes",
                onclick: function() {
                    Galaxy.page.router.push(`${getAppRoot()}custom_builds`);
                }
            },
            genomespace: {
                title: _l("Request GenomeSpace token"),
                description: _l("Requests token through OpenID."),
                icon: "fa-openid",
                onclick: function() {
                    window.location.href = `${getAppRoot()}openid/openid_auth?openid_provider=genomespace`;
                }
            },
            logout: {
                title: _l("Sign out"),
                description: _l("Click here to sign out of all sessions."),
                icon: "fa-sign-out",
                onclick: function() {
                    Galaxy.modal.show({
                        title: _l("Sign out"),
                        body: "Do you want to continue and sign out of all active sessions?",
                        buttons: {
                            Cancel: function() {
                                Galaxy.modal.hide();
                            },
                            "Sign out": function() {
                                window.location.href = `${getAppRoot()}user/logout?session_csrf_token=${
                                    Galaxy.session_csrf_token
                                }`;
                            }
                        }
                    });
                }
            }
        });
    }
});

export default {
    Model: Model
};
