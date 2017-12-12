import WorkflowView from "mvc/workflow/workflow-view";
import Trackster from "viz/trackster";
import Circster from "viz/circster";
import GalaxyLibrary from "galaxy.library";
import AdminToolshed from "admin.toolshed";
import Masthead from "layout/masthead";
import user from "mvc/user/user-model";
import Modal from "mvc/ui/ui-modal";

export function mastheadEntry(options) {
    if (!Galaxy.user) {
        Galaxy.user = new user.User(options.user_json);
    }
    if (!Galaxy.masthead) {
        Galaxy.masthead = new Masthead.View(options);
        Galaxy.modal = new Modal.View();
        $("#masthead").replaceWith(Galaxy.masthead.render().$el);
    }
}

export function adminToolshedEntry(options) {
    new AdminToolshed.GalaxyApp(options);
}

export function tracksterEntry(options) {
    new Trackster.GalaxyApp(options);
}

export function circsterEntry(options) {
    new Circster.GalaxyApp(options);
}

export function workflowEntry(options) {
    new WorkflowView(options);
}

function libraryEntry(options) {
    new GalaxyLibrary.GalaxyApp(options);
}

export const bundleEntries = {
    library: libraryEntry,
    masthead: mastheadEntry,
    workflow: workflowEntry,
    trackster: tracksterEntry,
    circster: circsterEntry,
    adminToolshed: adminToolshedEntry
};

window.bundleEntries = bundleEntries;
