import { faBell, faInfoCircle, faMapSigns, faPuzzlePiece, faUserCog } from "@fortawesome/free-solid-svg-icons";

import { defaultActivities } from "@/stores/activitySetup";
import { useActivityStore } from "@/stores/activityStore";

import type { CommandPaletteProvider, PaletteContext, PaletteItem } from "../types";
import { rankPaletteItems } from "../utilities";

/** Activities owned by the actions provider instead */
const EXCLUDED_ACTIVITY_IDS = ["upload", "beta-upload"];

/** Useful destinations that are not activities */
const EXTRA_DESTINATIONS: PaletteItem[] = [
    {
        id: "navigation:preferences",
        icon: faUserCog,
        keywords: "settings account user",
        subtitle: "Manage your account settings",
        title: "Preferences",
        to: "/user",
    },
    {
        id: "navigation:notifications",
        icon: faBell,
        keywords: "messages broadcasts",
        subtitle: "View your notifications",
        title: "Notifications",
        to: "/user/notifications",
    },
    {
        id: "navigation:tours",
        icon: faMapSigns,
        keywords: "help introduction guided",
        subtitle: "Interactive guided tours of the Galaxy interface",
        title: "Tours",
        to: "/tours",
    },
    {
        id: "navigation:datatypes",
        icon: faPuzzlePiece,
        keywords: "formats extensions",
        subtitle: "List of all registered datatypes",
        title: "Datatypes",
        to: "/datatypes",
    },
    {
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
    return [...activityItems, ...EXTRA_DESTINATIONS];
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
