import type {
    MessageNotification,
    SharedItemNotification,
    ToolInstallationRequestNotification,
    UserNotification,
} from "@/api/notifications";

type NotificationOverrides<T extends UserNotification> = Partial<Omit<T, "category" | "content">> & {
    content?: Partial<T["content"]>;
};

function notificationDefaults() {
    return {
        variant: "info" as const,
        create_time: "2024-01-01T12:00:01.000Z",
        update_time: "2024-01-01T12:00:02.000Z",
        publication_time: "2024-01-01T12:00:03.000Z",
        expiration_time: "2024-01-02T12:00:00.000Z",
        seen_time: null,
        deleted: false,
    };
}

export function generateMessageNotification(
    overrides: NotificationOverrides<MessageNotification> = {},
): MessageNotification {
    return {
        ...notificationDefaults(),
        id: "message-notification",
        source: "admin",
        category: "message",
        ...overrides,
        content: {
            subject: "Message subject",
            message: "Message body",
            category: "message",
            ...overrides.content,
        },
    };
}

export function generateNewSharedItemNotification(
    overrides: NotificationOverrides<SharedItemNotification> = {},
): SharedItemNotification {
    return {
        ...notificationDefaults(),
        id: "shared-item-notification",
        source: "galaxy_sharing_system",
        category: "new_shared_item",
        ...overrides,
        content: {
            category: "new_shared_item",
            item_type: "history",
            item_name: "Shared history",
            owner_name: "History owner",
            slug: "shared-history",
            ...overrides.content,
        },
    };
}

export function generateToolInstallationRequestNotification(
    overrides: NotificationOverrides<ToolInstallationRequestNotification> = {},
): ToolInstallationRequestNotification {
    return {
        ...notificationDefaults(),
        id: "tool-request-notification",
        source: "tool_installation_request_form",
        category: "tool_installation_request",
        ...overrides,
        content: {
            category: "tool_installation_request",
            tools: [
                {
                    name: "Example tool",
                    tool_shed_id: null,
                    tool_url: "https://github.com/example/tool",
                    description: "A useful scientific analysis tool",
                    scientific_domain: "Genomics",
                    requested_version: "1.0.0",
                },
            ],
            workflow_id: null,
            additional_remarks: null,
            requester_email: "requester@example.com",
            ...overrides.content,
        },
    };
}

export function generateNotificationsList(n: number) {
    if (n <= 2) {
        throw new Error("Invalid input. Number must be greater than 2.");
    }

    const notifications = Array.from({ length: n }, (_, index) => {
        const createNotification = index % 2 === 0 ? generateMessageNotification : generateNewSharedItemNotification;
        return createNotification({
            id: `notification-${index + 1}`,
            seen_time: index % 4 < 2 ? null : "2024-01-01T12:00:04.000Z",
        });
    });

    return {
        notifications,
        messageCount: notifications.filter((notification) => notification.category === "message").length,
        sharedItemCount: notifications.filter((notification) => notification.category === "new_shared_item").length,
    };
}
