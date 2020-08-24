/**
 * Panel management code transplanted from base.mako
 * TODO: figure out when these functions fire
 *
 * @param {} panelConfig
 */
export function panelManagement(panelConfig) {
    console.log("panelManagement");
    console.log("(looks like it's assinging some global handlers to window to manage the left and right panel views?)");

    const { left_panel, right_panel, rightPanelSelector, leftPanelSelector } = panelConfig;

    if (left_panel) {
        var lp = new window.bundleEntries.panels.LeftPanel({
            el: leftPanelSelector,
        });
        window.force_left_panel = function (x) {
            console.log("window.force_left_panel fired");
            lp.force_panel(x);
        };
    }

    if (right_panel) {
        var rp = new window.bundleEntries.panels.RightPanel({
            el: rightPanelSelector,
        });
        window.handle_minwidth_hint = function (x) {
            console.log("window.handle_minwidth_hint", x);
            rp.handle_minwidth_hint(x);
        };
        window.force_right_panel = function (x) {
            console.log("window.force_right_panel", x);
            rp.force_panel(x);
        };
    }
}
