import { setGalaxyInstance } from "app";

/**
 * Most of the time, all we do is launch a GalaxyApp with the passed configs
 *
 * @param {string} label
 * @returns {function} Returns a function that accepts the application
 * configuration and returns a galaxy instance.
 */
export const defaultAppFactory = (config, label = "Galaxy") => {
    return setGalaxyInstance((GalaxyApp) => {
        const { options, bootstrapped } = config;
        const app = new GalaxyApp(options, bootstrapped);
        app.debug(`${label} app`);
        return app;
    });
};
