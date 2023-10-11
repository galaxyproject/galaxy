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
            url: `/api/users/${user_id}/information/inputs`,
            icon: "fa-user",
            redirect: "/user",
            disabled: config.use_remote_user,
        },
        password: {
            title: _l("Change Password"),
            id: "edit-preferences-password",
            description: _l("Allows you to change your login credentials."),
            icon: "fa-unlock-alt",
            url: `/api/users/${user_id}/password/inputs`,
            submit_title: "Save Password",
            redirect: "/user",
            disabled: config.use_remote_user || !config.enable_account_interface,
        },
        permissions: {
            title: _l("Set Dataset Permissions for New Histories"),
            id: "edit-preferences-permissions",
            description: _l(
                "Grant others default access to newly created histories. Changes made here will only affect histories created after these settings have been stored."
            ),
            url: `/api/users/${user_id}/permissions/inputs`,
            icon: "fa-users",
            submitTitle: "Save Permissions",
            redirect: "/user",
            disabled: config.single_user,
        },
        toolbox_filters: {
            title: _l("Manage Toolbox Filters"),
            id: "edit-preferences-toolbox-filters",
            description: _l("Customize your Toolbox by displaying or omitting sets of Tools."),
            url: `/api/users/${user_id}/toolbox_filters/inputs`,
            icon: "fa-filter",
            submitTitle: "Save Filters",
            redirect: "/user",
            disabled: !config.has_user_tool_filters,
        },
    };
};
