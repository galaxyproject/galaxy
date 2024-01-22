import { type components } from "@/api/schema";

type NotificationVariants = components["schemas"]["NotificationVariant"];
type BroadcastNotificationResponse = components["schemas"]["BroadcastNotificationResponse"];

export function generateRandomString() {
    return Math.random().toString(36).substring(7) as string;
}

export function generateRandomVariant() {
    const variants: NotificationVariants[] = ["info", "warning", "urgent"];
    const randomIndex = Math.floor(Math.random() * variants.length);
    return variants[randomIndex] as NotificationVariants;
}

export function generateNewBroadcast({ actionLink = false, published = false }): BroadcastNotificationResponse {
    let baseDate;

    if (published) {
        baseDate = Date.now() - 100000;
    } else {
        baseDate = Date.now() + 100000;
    }

    const tmp: BroadcastNotificationResponse = {
        id: "broadcast-" + Math.floor(Math.random() * 1000000),
        source: generateRandomString(),
        category: "broadcast",
        variant: generateRandomVariant(),
        create_time: new Date(baseDate + 1).toISOString(),
        update_time: new Date(baseDate + 2000).toISOString(),
        publication_time: new Date(baseDate + 3000).toISOString(),
        expiration_time: new Date(baseDate + 86400000).toISOString(),
        content: {
            subject: generateRandomString(),
            message: generateRandomString(),
            category: "broadcast",
        },
    };

    if (actionLink) {
        tmp.content.action_links = [
            {
                link: "https://test.link",
                action_name: generateRandomString(),
            },
        ];
    }

    return tmp;
}
