import GalaxyLibrary from "galaxy.library";

export function tracksterApp(options) {
    new GalaxyLibrary.GalaxyApp(options);
}

window.libraryApp = tracksterApp;
