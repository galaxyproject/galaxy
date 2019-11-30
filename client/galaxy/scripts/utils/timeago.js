/**
 * Determines the time passed given a iso-timestamp
 */
export function timeAgo(stamp) {
    const now = Date.now();
    const past = new Date(stamp);
    if (stamp && past <= now) {
        const titles = ["second", "minute", "hour", "day", "month"];
        const dividers = [60, 60, 24, 30, 12];
        let delta = Math.floor((now - past) / 1000);
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
