import { useRouter } from "vue-router/composables";

import { type Activity, useActivityStore } from "@/stores/activityStore";

export function useActivityAction(activityStoreId: string) {
    const router = useRouter();
    const activityStore = useActivityStore(activityStoreId);
    const executeActivity = (activity: Activity) => {
        if (activity.panel) {
            activityStore.toggleSideBar(activity.id);
        }
        if (activity.to) {
            router.push(activity.to);
        }
    };

    return {
        executeActivity,
    };
}
