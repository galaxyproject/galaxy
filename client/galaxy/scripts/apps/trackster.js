import Trackster from "viz/trackster";

export default function tracksterApp(options) {
    new Trackster.GalaxyApp(options);
}

window.tracksterApp = tracksterApp;
