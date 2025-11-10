// globalInits.ts
import { monitorInit } from "@/utils/installMonitor";

import { initSentry } from "./initSentry";
import { onloadWebhooks } from "./onloadWebhooks";

export async function globalInits(galaxy, config) {
    monitorInit(galaxy, config);
    await initSentry(galaxy, config);
    await onloadWebhooks(galaxy);
}
