import { useRouter } from "vue-router/composables";

import { type Activity } from "@/stores/activityStore";
import { useUserStore } from "@/stores/userStore";

export function useActivityAction() {
    const router = useRouter();
    const userStore = useUserStore();
    const executeActivity = (activity: Activity) => {
        if (activity.panel) {
            userStore.toggleSideBar(activity.id);
        }
        if (activity.to) {
            router.push(activity.to);
        }
    };

    return {
        executeActivity,
    };
}
