import Trackster from "viz/trackster";
import Circster from "viz/circster";

export function tracksterApp(options) {
    new Trackster.GalaxyApp(options);
}

export function circsterApp(options) {
    new Circster.GalaxyApp(options);
}

window.tracksterApp = tracksterApp;
window.circsterApp = circsterApp;
