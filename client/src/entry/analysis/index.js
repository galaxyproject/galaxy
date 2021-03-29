import { standardInit, addInitialization } from "onload";
import { getAnalysisRouter } from "./AnalysisRouter";
import ToolPanel from "entry/panels/tool-panel";
import MvcHistoryPanel from "entry/panels/history-panel";
import Page from "layout/page";

// Vue adapter emulates current features of backbone history panel
import { HistoryPanelProxy } from "components/History/adapters/HistoryPanelProxy";
import { shouldUseBetaHistory } from "components/History/adapters/betaToggle";

addInitialization((Galaxy, { options = {} }) => {
    console.log("Analysis custom page setup");

    // Handle beta history panel
    // Need to mock Galaxy.currHistoryPanel
    // pass config through for defaults
    const HistoryPanel = shouldUseBetaHistory(Galaxy.config.beta_history_default_on)
        ? HistoryPanelProxy
        : MvcHistoryPanel;

    const pageOptions = Object.assign({}, options, {
        config: Object.assign({}, options.config, {
            hide_panels: Galaxy.params.hide_panels,
            hide_masthead: Galaxy.params.hide_masthead,
        }),
        Left: ToolPanel,
        Right: HistoryPanel,
        Router: getAnalysisRouter(Galaxy),
    });
    Galaxy.page = new Page.View(pageOptions);
});

window.addEventListener("load", () => standardInit("analysis"));
