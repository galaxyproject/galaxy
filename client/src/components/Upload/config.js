import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";

export function initializeUploadDefaults(propsData = {}) {
    const Galaxy = getGalaxyInstance();
    const appRoot = getAppRoot();
    const defaults = {
        multiple: true,
        uploadPath: Galaxy.config.nginx_upload_path || `${appRoot}api/tools`,
        chunkUploadSize: Galaxy.config.chunk_upload_size,
        fileSourcesConfigured: Galaxy.config.file_sources_configured,
        ftpUploadSite: Galaxy.config.ftp_upload_site,
        defaultGenome: Galaxy.config.default_genome,
        defaultExtension: Galaxy.config.default_extension,
        selectable: false,
    };
    return Object.assign({}, defaults, propsData);
}
