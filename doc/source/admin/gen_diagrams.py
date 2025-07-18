import os
import sys

import erdantic as erd

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, "lib")))

from galaxy.files.templates.models import (
    AzureFileSourceConfiguration,
    AzureFileSourceTemplateConfiguration,
    DropboxFileSourceConfiguration,
    DropboxFileSourceTemplateConfiguration,
    eLabFTWFileSourceConfiguration,
    eLabFTWFileSourceTemplateConfiguration,
    FileSourceTemplate,
    FtpFileSourceConfiguration,
    FtpFileSourceTemplateConfiguration,
    InvenioFileSourceConfiguration,
    InvenioFileSourceTemplateConfiguration,
    PosixFileSourceConfiguration,
    PosixFileSourceTemplateConfiguration,
    RSpaceFileSourceConfiguration,
    RSpaceFileSourceTemplateConfiguration,
    S3FSFileSourceConfiguration,
    S3FSFileSourceTemplateConfiguration,
    WebdavFileSourceConfiguration,
    WebdavFileSourceTemplateConfiguration,
    ZenodoFileSourceConfiguration,
    ZenodoFileSourceTemplateConfiguration,
)
from galaxy.objectstore.templates.models import (
    AwsS3ObjectStoreConfiguration,
    AwsS3ObjectStoreTemplateConfiguration,
    AzureObjectStoreConfiguration,
    AzureObjectStoreTemplateConfiguration,
    Boto3ObjectStoreConfiguration,
    Boto3ObjectStoreTemplateConfiguration,
    DiskObjectStoreConfiguration,
    DiskObjectStoreTemplateConfiguration,
    GenericS3ObjectStoreConfiguration,
    GenericS3ObjectStoreTemplateConfiguration,
    ObjectStoreTemplate,
)

DOC_SOURCE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))

class_to_diagram = {
    ObjectStoreTemplate: "object_store_templates",
    AzureObjectStoreConfiguration: "object_store_azure_configuration",
    AzureObjectStoreTemplateConfiguration: "object_store_azure_configuration_template",
    Boto3ObjectStoreConfiguration: "object_store_boto3_configuration",
    Boto3ObjectStoreTemplateConfiguration: "object_store_boto3_configuration_template",
    DiskObjectStoreConfiguration: "object_store_disk_configuration",
    DiskObjectStoreTemplateConfiguration: "object_store_disk_configuration_template",
    AwsS3ObjectStoreTemplateConfiguration: "object_store_aws_s3_configuration_template",
    AwsS3ObjectStoreConfiguration: "object_store_aws_s3_configuration",
    GenericS3ObjectStoreTemplateConfiguration: "object_store_generic_s3_configuration_template",
    GenericS3ObjectStoreConfiguration: "object_store_generic_s3_configuration",
    FileSourceTemplate: "file_source_templates",
    AzureFileSourceTemplateConfiguration: "file_source_azure_configuration_template",
    AzureFileSourceConfiguration: "file_source_azure_configuration",
    DropboxFileSourceTemplateConfiguration: "file_source_dropbox_configuration_template",
    DropboxFileSourceConfiguration: "file_source_dropbox_configuration",
    PosixFileSourceTemplateConfiguration: "file_source_posix_configuration_template",
    PosixFileSourceConfiguration: "file_source_posix_configuration",
    S3FSFileSourceTemplateConfiguration: "file_source_s3fs_configuration_template",
    S3FSFileSourceConfiguration: "file_source_s3fs_configuration",
    FtpFileSourceTemplateConfiguration: "file_source_ftp_configuration_template",
    FtpFileSourceConfiguration: "file_source_ftp_configuration",
    WebdavFileSourceTemplateConfiguration: "file_source_webdav_configuration_template",
    WebdavFileSourceConfiguration: "file_source_webdav_configuration",
    eLabFTWFileSourceTemplateConfiguration: "file_source_elabftw_configuration_template",
    eLabFTWFileSourceConfiguration: "file_source_elabftw_configuration",
    InvenioFileSourceTemplateConfiguration: "file_source_invenio_configuration_template",
    InvenioFileSourceConfiguration: "file_source_invenio_configuration",
    ZenodoFileSourceTemplateConfiguration: "file_source_zenodo_configuration_template",
    ZenodoFileSourceConfiguration: "file_source_zenodo_configuration",
    RSpaceFileSourceTemplateConfiguration: "file_source_rspace_configuration_template",
    RSpaceFileSourceConfiguration: "file_source_rspace_configuration",
}

for clazz, diagram_name in class_to_diagram.items():
    erd.draw(clazz, out=f"{DOC_SOURCE_DIR}/{diagram_name}.png")
