// globalInits.ts
import { initSentry } from "./initSentry";
import { onloadWebhooks } from "./onloadWebhooks";

export async function globalInits(galaxy, config) {
    await initSentry(galaxy, config);
    await onloadWebhooks(galaxy);
}
