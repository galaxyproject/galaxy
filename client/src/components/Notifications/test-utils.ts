import {
    type MessageNotification,
    type NewSharedItemNotificationContentItemType,
    type NotificationVariants,
    type SharedItemNotification,
    type UserNotification,
} from "@/api/notifications";

export function generateRandomItemType() {
    const itemTypes = ["history", "workflow", "visualization", "page"];
    const randomIndex = Math.floor(Math.random() * itemTypes.length);
    return itemTypes[randomIndex] as NewSharedItemNotificationContentItemType;
}

export function generateRandomString() {
    return Math.random().toString(36).substring(7) as string;
}

export function generateRandomVariant() {
    const variants: NotificationVariants[] = ["info", "warning", "urgent"];
    const randomIndex = Math.floor(Math.random() * variants.length);
    return variants[randomIndex] as NotificationVariants;
}

export function generateMessageNotification(): MessageNotification {
    return {
        id: "notification-" + Math.floor(Math.random() * 1000000),
        source: "admin",
        category: "message",
        variant: generateRandomVariant(),
        create_time: new Date(Date.now() + 1).toISOString(),
        update_time: new Date(Date.now() + 2).toISOString(),
        publication_time: new Date(Date.now() + 3).toISOString(),
        expiration_time: new Date(Date.now() + 86400000).toISOString(),
        content: {
            subject: generateRandomString(),
            message: generateRandomString(),
            category: "message",
        },
        seen_time: Math.random() > 0.5 ? new Date().toISOString() + 3 : undefined,
        deleted: false,
    };
}

export function generateNewSharedItemNotification(): SharedItemNotification {
    return {
        id: "notification-" + Math.floor(Math.random() * 1000000),
        source: "galaxy_sharing_system",
        category: "new_shared_item",
        variant: generateRandomVariant(),
        create_time: new Date(Date.now() + 1).toISOString(),
        update_time: new Date(Date.now() + 2).toISOString(),
        publication_time: new Date(Date.now() + 3).toISOString(),
        expiration_time: new Date(Date.now() + 86400000).toISOString(),
        content: {
            category: "new_shared_item",
            item_type: generateRandomItemType(),
            item_name: generateRandomString(),
            owner_name: generateRandomString(),
            slug: generateRandomString(),
        },
        seen_time: Math.random() > 0.5 ? new Date().toISOString() + 3 : undefined,
        deleted: false,
    };
}

export function generateNotificationsList(n: number) {
    if (n <= 2) {
        throw new Error("Invalid input. Number must be greater than 2.");
    }

    let messageCount = 1;
    let sharedItemCount = 1;
    const remainingCount = n - 2;

    const notifications: UserNotification[] = [generateMessageNotification(), generateNewSharedItemNotification()];

    if (remainingCount > 0) {
        for (let i = 0; i < remainingCount; i++) {
            if (i % 2 === 0) {
                notifications.push(generateMessageNotification());
                messageCount = messageCount + 1;
            } else {
                notifications.push(generateNewSharedItemNotification());
                sharedItemCount = sharedItemCount + 1;
            }
        }
    }

    return {
        notifications,
        messageCount,
        sharedItemCount,
    };
}
