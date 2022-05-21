/**
 * Share Replay with a refcount as per the older rxjs shareReplay operator. It is often important to
 * have the global availability of a shareReplay, but the ability to complete a subscription.
 */
import { shareReplay } from "rxjs/operators";

export const shareButDie = (n) => shareReplay({ bufferSize: n, refCount: true });
