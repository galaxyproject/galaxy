# Maintaining the metadata runtime image

For deployment, compatibility, optional datatype dependencies and custom images,
see the [administrator guide](../admin/containerized_metadata.md).

## Publishing official images

`.github/workflows/metadata_image.yaml` defines publication to
`quay.io/galaxyproject/galaxy-job-execution`, using the existing upstream
`QUAY_USERNAME` and `QUAY_PASSWORD` credentials. Registry maintainers must create
the repository, allow those credentials to push, and make images readable by
execution hosts. Pull requests and forks build without publishing or accessing
registry credentials.

- Pushes to `dev`, release branches and release tags build the corresponding
  source checkout. PR checks build both the checkout and the default stable
  PyPI runtime; integration tests always build the checkout.
- Manual dispatch rebuilds a specified published stable package version. Use
  this for the initial 26.1.1 image and for runtime/base-image updates after
  packages are available on PyPI.
- Each publication writes a moving Galaxy-version alias (for example `26.1.1`
  or `26.2.dev0`) and a unique build tag
  `<version>-r<workflow-run-number>.<attempt>`. Do not reuse build tags. Pin the
  digest for deployment; the version alias can advance after rebuilds.
- Images record the Galaxy version, source revision and build date in OCI
  labels. The workflow also produces provenance and an SBOM. The installed
  Python package manifest records the resolved runtime dependencies.

A pinned Galaxy version alone does not make successive builds byte-identical:
base images, OS packages and other Python dependencies can change. Rebuild and
validate for security updates, retain the previous digest for rollback, and
update deployment references deliberately. Update the Dockerfile's stable
Galaxy/Python defaults and the manual-dispatch default when adopting a new
stable release. Do not silently substitute a new Galaxy release in an existing
server deployment.
