import { standardInit, addInitialization } from "onload";
import { getAnalysisRouter } from "./AnalysisRouter";
import ToolPanel from "entry/panels/tool-panel";
import HistoryPanel from "entry/panels/history-panel";
import Page from "layout/page";

addInitialization((Galaxy, { options = {} }) => {
    console.log("Analysis custom page setup");

    let pageOptions = Object.assign({}, options, {
        config: Object.assign({}, options.config, {
            hide_panels: Galaxy.params.hide_panels,
            hide_masthead: Galaxy.params.hide_masthead
        }),
        Left: ToolPanel,
        Right: HistoryPanel,
        Router: getAnalysisRouter(Galaxy)
    });

    Galaxy.page = new Page.View(pageOptions);
});

window.addEventListener("load", () => standardInit("analysis"));
