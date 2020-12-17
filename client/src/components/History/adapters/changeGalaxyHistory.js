// called by Vuex store whenever current history changes

export function changeGalaxyHistory(id) {
    console.log("changeGalaxyHistory", id);
    if (window.Galaxy) {
        try {
            window.Galaxy.currHistoryPanel.switchToHistory(id);
        } catch (err) {
            console.warn("unable to switch histories", id, err);
        }
    }
}
