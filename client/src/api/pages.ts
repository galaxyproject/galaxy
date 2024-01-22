import { fetcher } from "@/api/schema";

/** Page request helper **/
const deletePageById = fetcher.path("/api/pages/{id}").method("delete").create();
export async function deletePage(itemId: string): Promise<void> {
    await deletePageById({
        id: itemId,
    });
}
