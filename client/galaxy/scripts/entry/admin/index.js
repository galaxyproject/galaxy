import { standardInit, addInitialization } from "onload";
import { getAdminRouter } from "./AdminRouter";
import AdminPanel from "../panels/admin-panel";
import Utils from "utils/utils";
import Page from "layout/page";

addInitialization((Galaxy, { options }) => {
    console.log("Admin custom page setup");

    Object.assign(options.config, {
        active_view: "admin"
    });

    let pageOptions = Object.assign({}, options, {
        Left: AdminPanel,
        Router: getAdminRouter(Galaxy, options)
    });

    Utils.setWindowTitle("Administration");
    Galaxy.page = new Page.View(pageOptions);
});

window.addEventListener("load", () => standardInit("admin"));
