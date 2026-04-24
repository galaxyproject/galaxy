import { useConfigStore } from "@/stores/configurationStore";

import { submitToolJob as submitAsync } from "./submitAsync";
import { submitToolJob as submitLegacy } from "./submitLegacy";

export async function submitToolJob(params) {
    const configStore = useConfigStore();
    if (configStore.config?.enable_celery_tasks) {
        return submitAsync(params);
    }
    return submitLegacy(params);
}
