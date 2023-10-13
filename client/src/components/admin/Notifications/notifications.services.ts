import axios from "axios";

import { type components, fetcher } from "@/api/schema";

const getNotification = fetcher.path("/api/notifications/{notification_id}").method("get").create();
type NotificationResponse = components["schemas"]["NotificationResponse"];
export async function loadNotification(id: string): Promise<NotificationResponse> {
    const { data } = await getNotification({ notification_id: id });
    return data;
}

const postNotification = fetcher.path("/api/notifications").method("post").create();
type NotificationCreateRequest = components["schemas"]["NotificationCreateRequest"];
export async function sendNotification(notification: NotificationCreateRequest) {
    const { data } = await postNotification(notification);
    return data;
}

const putNotification = fetcher.path("/api/notifications/{notification_id}").method("put").create();
type UserNotificationUpdateRequest = components["schemas"]["UserNotificationUpdateRequest"];
export async function updateNotification(id: string, notification: UserNotificationUpdateRequest) {
    const { data } = await putNotification({ notification_id: id, ...notification });
    return data;
}

const getRolesReq = fetcher.path("/api/roles").method("get").create();
export async function getRoles() {
    const { data } = await getRolesReq({});
    return data;
}

const getUsersReq = fetcher.path("/api/users").method("get").create();
export async function getUsers() {
    const { data } = await getUsersReq({});
    return data;
}

type GroupModel = components["schemas"]["GroupModel"];
export async function getGroups(): Promise<GroupModel[]> {
    const { data } = await axios.get("/api/groups");
    return data;
}
