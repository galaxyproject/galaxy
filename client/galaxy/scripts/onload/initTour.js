import Tours from "mvc/tours";

export function initTour(Galaxy, config) {
    console.log("append tour data to instance");
    Galaxy.giveTourWithData = Tours.giveTourWithData;
}
