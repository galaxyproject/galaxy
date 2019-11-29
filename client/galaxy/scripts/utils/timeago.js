/**
 * Determines the time passed given a iso-timestamp
 */
export function timeAgo(stamp) {
    if (stamp) {
        const now = Math.floor(Date.now() / 1000);
        const past = Math.floor(new Date(stamp) / 1000);
        const titles = ["second", "minute", "hour", "day", "month"];
        const dividers = [60, 60, 24, 30, 12];
        let delta = now - past;
        for (const i in dividers) {
            const title = titles[i];
            const divider = dividers[i];
            if (delta < divider) {
                const suffix = delta > 1 ? "s" : "";
                return `${delta} ${title}${suffix} ago`;
            }
            delta = Math.floor(delta / divider);
        }
        const suffix = delta > 1 ? "s" : "";
        return `${delta} year${suffix} ago`;
    } else {
        return "Unavailable";
    }
}
