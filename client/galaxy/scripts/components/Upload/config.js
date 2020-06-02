import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";

export function initializeUploadDefaults(propsData = {}) {
    const Galaxy = getGalaxyInstance();
    const appRoot = getAppRoot();
    return Object.assign(propsData, {
        uploadPath: Galaxy.config.nginx_upload_path || `${appRoot}api/tools`,
        chunkUploadSize: Galaxy.config.chunk_upload_size,
        ftpUploadSite: Galaxy.config.ftp_upload_site,
        defaultGenome: Galaxy.config.default_genome,
        defaultExtension: Galaxy.config.default_extension,
    });
}
