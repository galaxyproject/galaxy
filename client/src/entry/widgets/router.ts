import { createRouter, createWebHistory, type RouterHistory } from "vue-router";

import { getAppRoot } from "@/onload/loadConfig";

import { widgetRoutes } from "./routes";

export function getRouter(history: RouterHistory = createWebHistory(getAppRoot())) {
    return createRouter({ history, routes: widgetRoutes });
}
