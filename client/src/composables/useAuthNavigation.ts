import { cancelPendingRequests } from "@/api/pendingRequests";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useNotificationsStore } from "@/stores/notificationsStore";

/**
 * Tear down every long-lived connection and cancel every in-flight request
 * (both axios and ``openapi-fetch``/GalaxyApi) so that nothing issued under
 * the old anonymous ``galaxysession`` cookie can land on the server after
 * ``handle_user_login`` has invalidated it. See
 * ``client/src/api/pendingRequests.ts`` for the race this guards against.
 *
 * Call this synchronously as the first step of a login or registration
 * submit, before the authenticating POST goes out. The shared abort
 * controller is rotated, so the login/register POST (issued right after)
 * will use a fresh signal and is not affected.
 */
export function discardActiveConnectionsBeforeAuthNavigation() {
    // Order: close SSE streams first (synchronous TCP close), then stop the
    // polling watchers so they can't kick off new fetches, then abort any
    // requests still in flight via the shared AbortController.
    useHistoryStore().stopWatchingHistory();
    useEntryPointStore().stopWatchingEntryPoints();
    useNotificationsStore().stopWatchingNotifications();
    cancelPendingRequests();
}
