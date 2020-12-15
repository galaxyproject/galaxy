// called by Vuex store whenever current history changes
// Inefficient because it will result in redundant ajax calls, but
// requires less legwork to hunt down all the horrible little
// hooks into the existing spaghetti-code model.
// TODO: remove when when not beta

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
