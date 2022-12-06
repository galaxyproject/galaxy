import { paths } from "./schema";
import { Fetcher } from "openapi-typescript-fetch";
import { getAppRoot } from "onload/loadConfig";

export const fetcher = Fetcher.for<paths>();
fetcher.configure({ baseUrl: getAppRoot() });
