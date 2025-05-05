import { getGalaxyInstance } from "app";

import { useResourceWatcher } from "@/composables/resourceWatcher";

import {
    ACTIVE_POLLING_INTERVAL,
    INACTIVE_POLLING_INTERVAL,
    watchHistory as watchHistorySuppliedApp,
} from "./watchHistory";

function watchHistory() {
    const app = getGalaxyInstance();
    return watchHistorySuppliedApp(app);
}

const { startWatchingResource: startWatchingHistory } = useResourceWatcher(watchHistory, {
    shortPollingInterval: ACTIVE_POLLING_INTERVAL,
    longPollingInterval: INACTIVE_POLLING_INTERVAL,
});

export { startWatchingHistory };
