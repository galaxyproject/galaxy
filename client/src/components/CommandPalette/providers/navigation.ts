import { faBell, faInfoCircle, faMapSigns, faPuzzlePiece, faUserCog } from "@fortawesome/free-solid-svg-icons";

import { defaultActivities } from "@/stores/activitySetup";
import { useActivityStore } from "@/stores/activityStore";

import type { CommandPaletteProvider, PaletteContext, PaletteItem, ScopedSection } from "../types";
import { type Gated, rankPaletteItems, visibleFor } from "../utilities";

/** Activities owned by the actions provider instead */
const EXCLUDED_ACTIVITY_IDS = ["upload", "beta-upload"];

/**
 * Non-activity destinations gated like the activity rows: `anonymous` mirrors
 * {@link defaultActivities}, `configGate` repeats the route's own check.
 */
const EXTRA_DESTINATIONS: Gated<PaletteItem>[] = [
    {
        anonymous: false,
        item: {
            id: "navigation:preferences",
            icon: faUserCog,
            keywords: "settings account user",
            subtitle: "Manage your account settings",
            title: "Preferences",
            to: "/user",
        },
    },
    {
        anonymous: false,
        configGate: (ctx) => Boolean(ctx.config.enable_notification_system),
        item: {
            id: "navigation:notifications",
            icon: faBell,
            keywords: "messages broadcasts",
            subtitle: "View your notifications",
            title: "Notifications",
            to: "/user/notifications",
        },
    },
    {
        anonymous: true,
        item: {
            id: "navigation:tours",
            icon: faMapSigns,
            keywords: "help introduction guided",
            subtitle: "Interactive guided tours of the Galaxy interface",
            title: "Tours",
            to: "/tours",
        },
    },
    {
        anonymous: true,
        item: {
            id: "navigation:datatypes",
            icon: faPuzzlePiece,
            keywords: "formats extensions",
            subtitle: "List of all registered datatypes",
            title: "Datatypes",
            to: "/datatypes",
        },
    },
    {
        anonymous: true,
        item: {
            id: "navigation:about",
            icon: faInfoCircle,
            keywords: "version instance galaxy",
            subtitle: "About this Galaxy instance",
            title: "About",
            to: "/about",
        },
    },
];

function activityAvailable(activityId: string, anonymous: boolean, ctx: PaletteContext): boolean {
    if (EXCLUDED_ACTIVITY_IDS.includes(activityId)) {
        return false;
    }
    if (!anonymous && ctx.isAnonymous) {
        return false;
    }
    if (activityId === "user-defined-tools" && !ctx.canUseUnprivilegedTools) {
        return false;
    }
    if (activityId === "interactivetools" && !ctx.config.interactivetools_enable) {
        return false;
    }
    if (activityId === "galaxyai" && !ctx.config.llm_api_configured) {
        return false;
    }
    return true;
}

/** Focuses a panel-type activity in the activity bar side panel */
function openActivityPanel(activityId: string) {
    const activityStore = useActivityStore("default");
    activityStore.ensureVisible(activityId);
    activityStore.ensureSideBarOpen(activityId);
}

function navigationItems(ctx: PaletteContext): PaletteItem[] {
    const activityItems = defaultActivities
        .filter((activity) => activityAvailable(activity.id, activity.anonymous, ctx))
        .map((activity) => {
            const base = {
                id: `navigation:${activity.id}`,
                icon: activity.icon,
                keywords: activity.tooltip,
                subtitle: activity.description,
                title: activity.title,
            };
            if (activity.to) {
                return { ...base, to: activity.to };
            }
            return { ...base, handler: () => openActivityPanel(activity.id) };
        });
    return [...activityItems, ...visibleFor(EXTRA_DESTINATIONS, ctx)];
}

export const navigationProvider: CommandPaletteProvider = {
    id: "navigation",
    title: "Navigation",
    emptyQueryItems(ctx: PaletteContext) {
        return navigationItems(ctx);
    },
    search(query: string, ctx: PaletteContext) {
        return rankPaletteItems(navigationItems(ctx), query);
    },
    /**
     * `n:` scope — one section over the same destinations the root mode ranks,
     * headed like the other providers' scoped results: the matches for a query,
     * the full list of destinations without one.
     */
    searchScoped(_scope, query: string, ctx: PaletteContext): ScopedSection[] {
        const items = query ? rankPaletteItems(navigationItems(ctx), query) : navigationItems(ctx);
        return [{ id: "results", items, title: query ? "Navigation" : "Destinations" }];
    },
};
