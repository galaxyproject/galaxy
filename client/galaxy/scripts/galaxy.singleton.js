/**
 * TODO: Make this part of galaxy.js later, once the global refs are gone
 *
 * DO NOT import GalaxyApp into this file or you will create a catch-22 circular
 * dependency situation with the galaxy.monitor as window.Galaxy refers to the
 * instance and the instance refers to hard-coded Galaxy config variables which
 * refer back to window.Galaxy
 */

window._galaxyInstance = window._galaxyInstance || null;

export function setGalaxyInstance(factory) {
    window._galaxyInstance = factory();
    return window._galaxyInstance;
}

export function getGalaxyInstance() {
    return window._galaxyInstance;
}

export function galaxyIsInitialized() {
    return window._galaxyInstance !== null;
}
