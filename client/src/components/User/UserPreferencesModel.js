import { getGalaxyInstance } from "app";
import _l from "utils/localization";

export const getUserPreferencesModel = (user_id) => {
    const Galaxy = getGalaxyInstance();
    const config = Galaxy.config;
    user_id = user_id || Galaxy.user.id;
    return {
        information: {
            title: _l("Manage Information"),
            id: "edit-preferences-information",
            description: config.enable_account_interface
                ? _l("Edit your email, addresses and custom parameters or change your public name.")
                : _l("Edit your custom parameters."),
            url: `api/users/${user_id}/information/inputs`,
            icon: "fa-user",
            redirect: "user",
            shouldRender: !config.use_remote_user,
        },
        password: {
            title: _l("Change Password"),
            id: "edit-preferences-password",
            description: _l("Allows you to change your login credentials."),
            icon: "fa-unlock-alt",
            url: `api/users/${user_id}/password/inputs`,
            submit_title: "Save Password",
            redirect: "user",
            shouldRender: !config.use_remote_user && config.enable_account_interface,
        },
        external_ids: {
            title: _l("Manage Third-Party Identities"),
            id: "manage-third-party-identities",
            description: _l("Connect or disconnect access to your third-party identities."),
            icon: "fa-id-card-o",
            submitTitle: "Disconnect identity",
            submitIcon: "fa-trash",
            shouldRender: config.enable_oidc,
        },
        permissions: {
            title: _l("Set Dataset Permissions for New Histories"),
            id: "edit-preferences-permissions",
            description: _l(
                "Grant others default access to newly created histories. Changes made here will only affect histories created after these settings have been stored."
            ),
            url: `api/users/${user_id}/permissions/inputs`,
            icon: "fa-users",
            submitTitle: "Save Permissions",
            redirect: "user",
            shouldRender: !config.single_user,
        },
        make_data_private: {
            title: _l("Make All Data Private"),
            id: "edit-preferences-make-data-private",
            description: _l("Click here to make all data private."),
            icon: "fa-lock",
            shouldRender: !config.single_user,
        },
        api_key: {
            title: _l("Manage API Key"),
            id: "edit-preferences-api-key",
            description: _l("Access your current API key or create a new one."),
            url: `api/users/${user_id}/api_key/inputs`,
            icon: "fa-key",
            submitTitle: "Create a new Key",
            submitIcon: "fa-check",
        },
        cloud_auth: {
            id: "edit-preferences-cloud-auth",
            title: _l("Manage Cloud Authorization"),
            description: _l("Add or modify the configuration that grants Galaxy to access your cloud-based resources."),
            icon: "fa-cloud",
            submitTitle: "Create a new Key",
            submitIcon: "fa-check",
            shouldRender: true,
        },
        toolbox_filters: {
            title: _l("Manage Toolbox Filters"),
            id: "edit-preferences-toolbox-filters",
            description: _l("Customize your Toolbox by displaying or omitting sets of Tools."),
            url: `api/users/${user_id}/toolbox_filters/inputs`,
            icon: "fa-filter",
            submitTitle: "Save Filters",
            redirect: "user",
            shouldRender: !!config.has_user_tool_filters,
        },
        custom_builds: {
            title: _l("Manage Custom Builds"),
            description: _l("Add or remove custom builds using history datasets."),
            icon: "fa-cubes",
        },
        logout: {
            title: _l("Sign out"),
            id: "edit-preferences-sign-out",
            description: _l("Click here to sign out of all sessions."),
            icon: "fa-sign-out",
            shouldRender: !!Galaxy.session_csrf_token && !config.single_user,
        },
    };
};
