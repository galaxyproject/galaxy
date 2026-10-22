import { computed } from "vue";

import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";

/** Whether the current user can ask the admins to install tools: the request form rides on notifications. */
export function useCanRequestToolInstallation() {
    const { config, isConfigLoaded } = useConfig();
    const userStore = useUserStore();

    return computed(
        () =>
            isConfigLoaded.value &&
            Boolean(config.value?.enable_notification_system) &&
            Boolean(config.value?.enable_tool_installation_request_form) &&
            !userStore.isAnonymous,
    );
}
