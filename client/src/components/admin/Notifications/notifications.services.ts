import axios from "axios";

import { type components, fetcher } from "@/schema";

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
type RoleModelResponse = components["schemas"]["RoleModelResponse"];
export async function getRoles(): Promise<RoleModelResponse[]> {
    const { data } = await getRolesReq({});
    return data;
}

type GroupModel = components["schemas"]["GroupModel"];
export async function getGroups(): Promise<GroupModel[]> {
    const { data } = await axios.get("/api/groups");
    return data;
}

type UserModel = components["schemas"]["UserModel"];
export async function getUsers(): Promise<UserModel[]> {
    const { data } = await axios.get("/api/users");
    return data;
}
