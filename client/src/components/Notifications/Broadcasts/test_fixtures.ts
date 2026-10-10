import { type BroadcastNotification } from "@/stores/broadcastsStore";

export const HOUR = 60 * 60 * 1000;

export const DAY = 24 * HOUR;

export interface BroadcastScenario extends Pick<BroadcastNotification, "id" | "variant"> {
    subject: string;
    message: string;
    /** Offsets from now, in ms. */
    publishedIn: number;
    expiresIn: number;
}

/** A broadcast timed from `now`, created a day before it's published, or a day before now if that's earlier. */
export function broadcast(
    now: number,
    { subject, message, publishedIn, expiresIn, ...rest }: BroadcastScenario,
    naiveUtc = false,
) {
    const format = (time: number) => {
        const iso = new Date(time).toISOString();
        return naiveUtc ? iso.replace("Z", "") : iso;
    };
    const created = format(now + Math.min(publishedIn, 0) - DAY);
    return {
        ...rest,
        source: "admin",
        category: "broadcast",
        create_time: created,
        update_time: created,
        publication_time: format(now + publishedIn),
        expiration_time: format(now + expiresIn),
        content: { category: "broadcast", subject, message },
    } satisfies BroadcastNotification;
}
