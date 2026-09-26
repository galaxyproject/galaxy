import { faBell, faInfoCircle, faMapSigns, faPuzzlePiece, faUserCog } from "@fortawesome/free-solid-svg-icons";

import { defaultActivities } from "@/stores/activitySetup";
import { useActivityStore } from "@/stores/activityStore";

import type { CommandPaletteProvider, PaletteContext, PaletteItem } from "../types";
import { rankPaletteItems } from "../utilities";

/** Activities owned by the actions provider instead */
const EXCLUDED_ACTIVITY_IDS = ["upload", "beta-upload"];

/**
 * A destination that is not an activity. Gated like the activity rows are:
 * `anonymous` mirrors the flag of {@link defaultActivities}, `available` adds
 * the configuration check the route itself makes.
 */
interface ExtraDestination extends PaletteItem {
    /** Whether anonymous users may reach it; the routes redirect them otherwise */
    anonymous: boolean;
    /** Extra availability check against the Galaxy configuration */
    available?: (ctx: PaletteContext) => boolean;
}

/** Useful destinations that are not activities */
const EXTRA_DESTINATIONS: ExtraDestination[] = [
    {
        anonymous: false,
        id: "navigation:preferences",
        icon: faUserCog,
        keywords: "settings account user",
        subtitle: "Manage your account settings",
        title: "Preferences",
        to: "/user",
    },
    {
        anonymous: false,
        available: (ctx) => Boolean(ctx.config.enable_notification_system),
        id: "navigation:notifications",
        icon: faBell,
        keywords: "messages broadcasts",
        subtitle: "View your notifications",
        title: "Notifications",
        to: "/user/notifications",
    },
    {
        anonymous: true,
        id: "navigation:tours",
        icon: faMapSigns,
        keywords: "help introduction guided",
        subtitle: "Interactive guided tours of the Galaxy interface",
        title: "Tours",
        to: "/tours",
    },
    {
        anonymous: true,
        id: "navigation:datatypes",
        icon: faPuzzlePiece,
        keywords: "formats extensions",
        subtitle: "List of all registered datatypes",
        title: "Datatypes",
        to: "/datatypes",
    },
    {
        anonymous: true,
        id: "navigation:about",
        icon: faInfoCircle,
        keywords: "version instance galaxy",
        subtitle: "About this Galaxy instance",
        title: "About",
        to: "/about",
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

/**
 * The curated destinations the current user can actually reach — an anonymous
 * user is redirected away from `/user`, and notifications only exist where the
 * notification system is enabled.
 */
function extraDestinations(ctx: PaletteContext): PaletteItem[] {
    return EXTRA_DESTINATIONS.filter((destination) => {
        if (!destination.anonymous && ctx.isAnonymous) {
            return false;
        }
        return destination.available ? destination.available(ctx) : true;
    }).map(({ anonymous: _anonymous, available: _available, ...item }) => item);
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
    return [...activityItems, ...extraDestinations(ctx)];
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
};
