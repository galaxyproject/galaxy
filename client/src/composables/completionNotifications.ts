import { computed } from "vue";

import type { NotificationCategory } from "@/api/notifications";
import { useConfig } from "@/composables/config";

/** Categories the user opts into for each run, so they have no on/off switch in the preferences. */
export const COMPLETION_NOTIFICATION_CATEGORIES: readonly NotificationCategory[] = ["job_completion"];

/**
 * Whether completed jobs are notified through the notification system, following the user's preferences.
 *
 * Mirrors the server: only with Celery does the notification system have an email channel, so without it the
 * server sends a plain email instead.
 */
export function useJobCompletionNotifications() {
    const { config, isConfigLoaded } = useConfig();
    return computed(() =>
        Boolean(isConfigLoaded.value && config.value?.enable_notification_system && config.value?.enable_celery_tasks),
    );
}
