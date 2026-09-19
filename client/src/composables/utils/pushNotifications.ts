import { Toast } from "@/composables/toast";

export function browserSupportsPushNotifications() {
    return "Notification" in window;
}

export function handlePermission(permission: string) {
    if (permission === "granted") {
        new Notification("Notifications enabled", {
            icon: "static/favicon.ico",
        });
        return true;
    } else {
        Toast.info("Push notifications disabled, please re-enable through browser settings.");
        return false;
    }
}

export async function togglePushNotifications() {
    if (browserSupportsPushNotifications()) {
        const permission = await Notification.requestPermission();
        return handlePermission(permission);
    }
    return false;
}

export function pushNotificationsEnabled() {
    if (browserSupportsPushNotifications()) {
        return Notification.permission === "granted";
    }
    return false;
}
