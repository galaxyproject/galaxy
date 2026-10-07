# Containerized metadata collection

Galaxy can run the metadata step after a tool in a separate container containing
`galaxy-set-metadata`. Enable it per job destination with `metadata_config`.
The tool's container and its dependencies are independent of the metadata image.
This feature must be present in your Galaxy server checkout; installing a newer
runtime image does not add it to an older server.

## When to use it

A metadata image gives execution hosts a consistent Python, Galaxy datatype
implementation, and dependency set without installing Galaxy's virtualenv on
every worker. It also lets Pulsar compute metadata remotely without sharing the
Galaxy installation. Pinning the image digest makes that environment repeatable
and lets you roll it back independently of worker configuration.

The costs are another container startup per job, image distribution and cache
space on workers, and responsibility for maintaining a runtime that matches the
server. Small jobs may spend a noticeable fraction of their time starting the
metadata container. Custom datatypes and optional dependencies need to be
installed in this image as well as on the server where applicable. An image is
not a substitute for configuring output transfer, object-store access, or the
container engine on the execution host.

## Choose a compatible image

Use the same Galaxy release as the server, including the patch release where
possible. Metadata files and serialized model objects are internal interfaces;
compatibility between different Galaxy releases is not guaranteed. For a
modified checkout or development branch, build the runtime from that checkout.
Do not use the latest stable runtime with a newer development server merely
because the image builds successfully.

The default image is
`quay.io/galaxyproject/galaxy-job-execution:<galaxy.version.VERSION>`.
There is no implicit `latest` tag. Set `metadata_config.image` explicitly to use
a locally built image, a private registry, a custom variant, or a digest.
The synthetic metadata tool's profile follows `galaxy.version.VERSION_MAJOR`;
it controls tool compatibility behavior, not which Galaxy packages are installed.

The Dockerfile's release build currently defaults to Galaxy **26.1.1** and Python
**3.14.7** on Debian trixie. The Python image can be overridden with a trixie-compatible `PYTHON_IMAGE`.
Both build and runtime stages use the same base to avoid Python or native-library
ABI mismatches. The supplied publishing workflow initially builds `linux/amd64`;
other architectures require a separately built and validated image.

Before enabling a destination, build the image or verify that its tag has been
published and is accessible from the execution host. Registry publication is a
separate step from merging this feature.

## Configure a destination

For a local or shared-filesystem cluster destination in `job_conf.yml`:

```yaml
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
execution:
  default: metadata_docker
  environments:
    metadata_docker:
      runner: local
      docker_enabled: true
      outputs_to_working_directory: true
      metadata_strategy: extended
      metadata_config:
        containerize: true
        engine: docker
        image: quay.io/galaxyproject/galaxy-job-execution:26.1.1
```

Replace the example release with the version matching your server. Prefer the
registry's `image@sha256:<digest>` reference once you have validated an image.
The engine must be available on the execution host. For Singularity, use
`engine: singularity`, enable `singularity_enabled` on the destination, and
provide an image reference supported by your configured container resolver,
for example a prebuilt SIF available on that host.

Metadata uses the destination's container resolver configuration. Keep the
explicit-container resolver enabled and avoid destination-wide tool-image
overrides such as `container_override` or `docker_container_id_override`:
these take precedence over the explicit metadata image too. Verify the selected
image in the job command when validating a destination.

For an existing Pulsar destination without shared Galaxy storage, add:

```yaml
remote_metadata: true
metadata_strategy: directory
default_file_action: copy
metadata_config:
  containerize: true
  engine: docker
  image: quay.io/galaxyproject/galaxy-job-execution:26.1.1
```

Keep the runner's existing connection and container configuration. `directory`
metadata returns datasets, composite extra files, and metadata through Pulsar's
staging machinery. Container paths refer to the remote job directory, not to
Galaxy's local filesystem. This configuration does not require sharing Galaxy's
object-store directory with Pulsar.

`extended` metadata instead writes outputs to the configured object store from
the execution host and returns the populated model store. Only use it remotely
when that object store is deliberately accessible there, with the required
credentials, networking and, for a disk store, explicitly configured mounts.
Turning on containerized metadata does not supply those resources or make
Galaxy's disk paths available remotely.

## Build a release or checkout image

Run builds from the repository root. A stable release build installs the Galaxy
package dependency closure at the requested version, rather than mixing a
pinned job-execution package with newer unpinned Galaxy packages:

```sh
docker build -f packages/job_execution/Dockerfile \
  --build-arg GALAXY_VERSION=26.1.1 \
  -t registry.example.org/galaxy-metadata:26.1.1 .
```

To build this checkout, including uncommitted development changes:

```sh
version=$(PYTHONPATH=lib python3 -c 'from galaxy.version import VERSION; print(VERSION)')
revision=$(git rev-parse HEAD)
docker build -f packages/job_execution/Dockerfile \
  --build-arg RUNTIME_SOURCE=source \
  --build-arg GALAXY_VERSION="$version" \
  --build-arg GIT_COMMIT="$revision" \
  --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  -t registry.example.org/galaxy-metadata:site-test .
```

`GALAXY_VERSION` labels a source build; it does not change the checked-out code.
Use a clean, recorded commit for production builds. Push the tested image to
your registry, obtain its digest, and set that reference in `metadata_config`.
For offline sites, distribute the image to workers before scheduling jobs.

Builds run `pip check` and import the metadata entry point, pysam and h5py in the
final runtime. They also record installed Python versions in
`/etc/galaxy/requirements.txt`. These checks detect packaging problems; they do
not prove that every configured datatype can collect metadata.

## Optional dependencies and custom datatypes

The standard image includes the declared `galaxy-data` Python dependencies
(including pysam and h5py) and the S3, Azure Blob and iRODS object-store clients. It does not
attempt to include every optional datatype executable, site plugin or file-source
backend. Tool requirements, host Conda environments and the tool container are
not automatically inherited by the metadata container. There is no automatic
per-datatype dependency installation at job runtime.

Build a site image containing the dependencies required by your enabled
datatypes. For example, media datatypes use `ffprobe` when available; without it,
some metadata can remain unset without failing the job. A site image supporting
those formats could include:

```dockerfile
FROM registry.example.org/galaxy-metadata:26.1.1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN ffprobe -version
COPY requirements-metadata.txt /tmp/requirements-metadata.txt
RUN python -m pip install --no-cache-dir \
        -c /etc/galaxy/requirements.txt -r /tmp/requirements-metadata.txt \
    && python -m pip check
```

Use a digest in `FROM` for production. Supply your own pinned
`requirements-metadata.txt` for additional Python dependencies. The constraints
prevent installation from silently replacing the base Galaxy runtime or its
existing dependencies. If dependencies conflict, rebuild and validate a
compatible base rather than removing the constraint without checking the effect.
Native extensions may require extra build tools and runtime libraries; these
must be provided in the custom Dockerfile.

Install custom datatype Python modules in the image under the same import paths
used by the server's datatype registry. The registry configuration is supplied
with the job; it is not an installer for the Python modules or their libraries.
Keep the server and image implementations in sync. Do not copy server secrets
into the image. Use normal job destination and storage configuration for runtime
credentials.

You can maintain different metadata images for different destinations and route
tools accordingly. Record your site variant and image build revision in the tag,
for example `26.1.1-media-r1`, and pin the resulting digest in production.

## Validate and diagnose

Test representative jobs for every enabled datatype, including nonempty data,
composite outputs with nested files, and metadata files such as BAM indexes.
Check the resulting metadata values, not only the final job state: some datatype
implementations tolerate missing optional libraries or executables.

When `metadata_config.containerize` is enabled, failing to resolve a container
is a configuration error; Galaxy does not silently construct a host metadata
command. Check that the requested engine is enabled on the destination and that
its container resolvers can resolve the image.

During validation, set `retry_metadata_internally: false` in `galaxy.yml` so that
server-side metadata fallback cannot conceal a failing remote runtime. Decide
whether to retain that setting in production; fallback can keep jobs usable,
but needs dependencies on the server and moves work back to it.

Inspect job stderr and the job's metadata results for missing imports,
executables, and inaccessible paths. A disk object-store permission error on
Pulsar is a reason to check the metadata strategy and transfer configuration,
not to mount Galaxy's entire storage into every remote container.

## Image versions and updates

Official images use a moving Galaxy-version alias (for example `26.1.1` or
`26.2.dev0`) and a unique build tag `<version>-r<workflow-run-number>.<attempt>`.
Pin a digest for deployment: a version alias can advance after rebuilds.
Images record the Galaxy version, source revision and build date in OCI labels,
and include the installed Python package manifest in `/etc/galaxy/requirements.txt`.

A pinned Galaxy version alone does not make successive builds byte-identical:
base images, OS packages and other Python dependencies can change. Validate
updates with representative jobs, retain the previous digest for rollback, and
update deployment references deliberately. Do not silently substitute a new
Galaxy release in an existing server deployment.

The [developer guide](../dev/metadata_image.md) describes how maintainers publish
official images and update the stable runtime defaults.
