import { useConfigStore } from "@/stores/configurationStore";

import { submitToolJob as submitAsync } from "./submitAsync";
import { submitToolJob as submitLegacy } from "./submitLegacy";

const ENABLE_ASYNC = false;

export async function submitToolJob(params) {
    const configStore = useConfigStore();
    if (ENABLE_ASYNC && configStore.config?.enable_celery_tasks) {
        return submitAsync(params);
    }
    return submitLegacy(params);
}
