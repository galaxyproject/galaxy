import { faFilter, faSliders, faUnlockAlt, type IconDefinition } from "font-awesome-6";
import { storeToRefs } from "pinia";

import { isRegisteredUser } from "@/api";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

export type UserPreferencesKey = "password" | "toolbox_filters" | "extra_preferences";

interface UserPreference {
    title: string;
    id: string;
    description: string;
    url: string;
    icon: IconDefinition;
    redirect: string;
    submitTitle?: string;
    disabled?: boolean;
}

export type UserPreferencesModel = Record<UserPreferencesKey, UserPreference>;

export const getUserPreferencesModel: (user_id?: string) => UserPreferencesModel = (user_id) => {
    const { config, isConfigLoaded } = useConfig();
    const userStore = useUserStore();
    const { currentUser } = storeToRefs(userStore);
    if (!user_id && isRegisteredUser(currentUser.value)) {
        user_id = currentUser.value?.id;
    }

    return {
        password: {
            title: localize("Change Password"),
            id: "edit-preferences-password",
            description: localize("Allows you to change your login credentials."),
            icon: faUnlockAlt,
            url: `/api/users/${user_id}/password/inputs`,
            submitTitle: "Save Password",
            redirect: "/user",
            disabled:
                isConfigLoaded.value &&
                (config.value.use_remote_user ||
                    config.value.disable_local_accounts ||
                    !config.value.enable_account_interface),
        },
        toolbox_filters: {
            title: localize("Manage Toolbox Filters"),
            id: "edit-preferences-toolbox-filters",
            description: localize("Customize your Toolbox by displaying or omitting sets of Tools."),
            url: `/api/users/${user_id}/toolbox_filters/inputs`,
            icon: faFilter,
            submitTitle: "Save Filters",
            redirect: "/user",
            disabled: isConfigLoaded.value && !config.value.has_user_tool_filters,
        },
        extra_preferences: {
            title: localize("Extra Configurations"),
            id: "edit-preferences-extra",
            description: localize("Settings this Galaxy instance defines, such as external service credentials."),
            url: `/api/users/${user_id}/extra_preferences/inputs`,
            icon: faSliders,
            submitTitle: "Save Settings",
            redirect: "/user",
            disabled: isConfigLoaded.value && !config.value.has_user_preferences_extra,
        },
    };
};
