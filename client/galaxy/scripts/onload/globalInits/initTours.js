import Tours from "mvc/tours";

export function initTours(Galaxy) {
    console.log("initTours");
    Tours.activeGalaxyTourRunner();
    Galaxy.giveTourWithData = Tours.giveTourWithData;
}
