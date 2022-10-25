/**
 * Returns the active tab given a current route.
 */

export function getActiveTab(currentRoute, baseTabs) {
    let matchedId = null;
    for (const tab of baseTabs) {
        const tabId = tab.id;
        if (currentRoute == tab.url) {
            matchedId = tabId;
            break;
        } else if (tab.menu) {
            for (const item of tab.menu) {
                if (currentRoute == item.url) {
                    matchedId = tabId;
                    break;
                }
            }
        }
    }
    return matchedId;
}
