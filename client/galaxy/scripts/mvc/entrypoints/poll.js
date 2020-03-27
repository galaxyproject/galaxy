import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

let interval;

export const clearPolling = () => {
    clearInterval(interval);
};

export const pollUntilActive = (onUpdate, onError, params) => {
    clearPolling();
    const url = getAppRoot() + `api/entry_points`;
    axios
        .get(url, { params: params })
        .then((response) => {
            const entryPoints = [];
            let allReady = true;
            response.data.forEach((entryPoint, i) => {
                entryPoints.push(entryPoint);
                if (!entryPoint.active) {
                    allReady = false;
                }
            });
            onUpdate(entryPoints);
            if (!allReady || entryPoints.length == 0) {
                interval = setInterval(() => {
                    pollUntilActive(onUpdate, onError, params);
                }, 3000);
            }
        })
        .catch(onError);
};
