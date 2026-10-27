import { describe, expect, it, vi } from "vitest";
import type { RouteLocationNormalized } from "vue-router";

import { getRouter } from "./router";

vi.mock("@/onload/loadConfig", () => ({ getAppRoot: () => "/galaxy/" }));
vi.mock("@/app", () => ({ getGalaxyInstance: () => ({ user: {}, config: {} }) }));

function props(path: string) {
    const router = getRouter({ config: {}, user: {} });
    const route = router.resolve(path) as RouteLocationNormalized;
    const propsOf = route.matched[route.matched.length - 1]!.props.default as (r: RouteLocationNormalized) => object;
    return propsOf(route);
}

describe("published embed routes", () => {
    it("maps the page embed parameters", () => {
        expect(props("/published/page?id=a1&embed=true&heading=false&displayOnly=true")).toEqual({
            pageId: "a1",
            embed: true,
            showHeading: false,
            displayOnly: true,
        });
    });

    it("leaves absent page parameters to the component defaults", () => {
        expect(props("/published/page?id=a1")).toEqual({
            pageId: "a1",
            embed: undefined,
            showHeading: undefined,
            displayOnly: false,
        });
    });

    it("maps the workflow embed parameters of the sharing snippet", () => {
        const query =
            "id=b2&embed=true&buttons=true&about=false&heading=false&minimap=true&zoom_controls=true&initialX=-20&initialY=-30&zoom=1.5&version=2";
        expect(props(`/published/workflow?${query}`)).toEqual({
            id: "b2",
            version: "2",
            zoom: 1.5,
            embed: true,
            showButtons: true,
            showAbout: false,
            showHeading: false,
            showMinimap: true,
            showZoomControls: true,
            initialX: -20,
            initialY: -30,
        });
    });

    it("leaves absent workflow parameters to the component defaults", () => {
        expect(props("/published/workflow?id=b2")).toEqual({
            id: "b2",
            version: undefined,
            zoom: undefined,
            embed: undefined,
            showButtons: undefined,
            showAbout: undefined,
            showHeading: undefined,
            showMinimap: undefined,
            showZoomControls: undefined,
            initialX: undefined,
            initialY: undefined,
        });
    });
});
