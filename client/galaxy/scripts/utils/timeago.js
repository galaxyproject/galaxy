/**
 * Determines the time passed given a iso-timestamp
 */
export function timeAgo(stamp) {
    if (stamp) {
        const seconds = Math.floor(new Date(stamp) / 1000);
        const now = Math.floor(Date.now() / 1000);
        let delta = now - seconds;
        const titles = ['second', 'minute', 'hour', 'day', 'month'];
        const dividers = [60, 60, 24, 30, 12];
        for (const i in dividers) {
            const title = titles[i];
            const divider = dividers[i];
            if (delta < divider) {
                const suffix = delta > 1 ? "s" : "";
                return `${delta} ${title}${suffix} ago`;
            }
            delta = Math.floor(delta / divider);
        }
        return `${delta} years ago`;
    } else {
        return "Unavailable";
    }
}