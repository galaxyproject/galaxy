// legacy code
export function extractRoles(role_list) {
    const selected_roles = [];
    role_list.forEach((item) => {
        selected_roles.push({ name: item[0], id: item[1] });
    });

    return selected_roles;
}
