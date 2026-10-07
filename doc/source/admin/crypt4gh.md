# Crypt4GH-encrypted datasets

Galaxy can store and compute on datasets encrypted with
[Crypt4GH](https://crypt4gh.readthedocs.io/), the GA4GH file encryption standard
for sensitive genomic data. Encrypted datasets stay encrypted at rest. They are
decrypted on the compute host only for the duration of a job that the dataset's
owner authorized, and the job's outputs are encrypted again for that user before
Galaxy stores them.

The feature is disabled by default. It relies on the external
[crypt4gh-recryptor-service](https://github.com/elixir-europe/crypt4gh-recryptor-service),
which runs in two modes:

- **User service** (`crypt4gh-recryptor-service user`): runs on each user's own
  machine and holds that user's Crypt4GH private key. The user's browser talks
  to it directly. Galaxy never sees the user's private key.
- **Compute service** (`crypt4gh-recryptor-service compute`): one instance per
  Galaxy server, run by the Galaxy administrator. It holds short-lived compute
  keypairs and re-encrypts dataset headers between users, compute keypairs and
  individual jobs. It only ever receives Crypt4GH headers, never file content.

## How it works

1. **Upload.** A user uploads a Crypt4GH file. Galaxy detects the Crypt4GH magic
   bytes and assigns a wrapper datatype named after the inner format, for example
   `fastqsanger.c4gh`, or `c4gh` when the inner format is unknown. The dataset's
   Crypt4GH header, which only the user's private key can open, is stored in the
   dataset's metadata.
2. **Authorization.** The user clicks the key icon of the expanded dataset in their
   history. The browser sends the dataset header to the user service on the
   user's machine. The user service fetches a compute public key from the compute
   service, re-encrypts the header to it with the user's private key, and returns
   the result. The browser submits it to Galaxy
   (`PUT /api/datasets/{id}/protection`), which stores it as a _grant_ for this
   user and this dataset.
3. **Job dispatch.** When a job reads an encrypted dataset as its inner format,
   Galaxy checks that the job's user holds a grant for it that won't expire
   during the job, and that the job's destination can run the job securely (see
   [Job destinations](#job-destinations)). It then writes a protection plan into
   the job's `configs` directory, with permissions restricted to its owner. Jobs that
   fail these checks are failed with an explanation, and nothing is sent to the
   compute service.
4. **Decryption.** Before the tool runs, a command prepended to the job script
   (`galaxy-protected-stage stage-in`) runs on the compute host, outside any tool
   container. It generates a per-job key in memory, asks the compute service to
   re-encrypt each input header to that key, and decrypts the inputs into
   `<job directory>/_protected/inputs/`, with a `umask` of `077`. The tool's
   command line points at these plaintext copies. If this step fails, the tool
   does not run and the job fails with "Job setup failed".
5. **Tool.** The tool reads the plaintext inputs. In a container, they are
   available through the job directory, which Galaxy mounts by default. The
   decrypted inputs are removed as soon as the tool exits.
6. **Output encryption.** While collecting outputs, Galaxy's metadata step
   encrypts every output in place to the compute key, asks the compute service to
   re-encrypt its header to the user's key, and gives it the wrapper datatype of
   its format. This covers declared outputs, `from_work_dir` outputs, discovered
   datasets, collection elements and extra files of composite outputs. Galaxy then
   checks, on the compute host, that every output starts with a Crypt4GH header,
   and records the result in the job's metadata directory.
7. **Verification.** When the job finishes, Galaxy checks that every output it
   knows about was encrypted. On a disk-based object store it re-reads each
   output's header and compares its digest. Outputs that can't be verified are
   purged and the job fails. Outputs that pass get grants for the job's user, so
   they can be used by further jobs and workflow steps without authorizing them
   again.
8. **Cleanup.** The `_protected` directory is removed by the job script once
   outputs are collected. Galaxy also removes the whole job directory of every job
   that decrypted data, whatever the destination's `cleanup_job` setting is, which
   covers jobs that were killed or cancelled.

Users can download outputs and decrypt them with their own Crypt4GH private key.

### Authorization is per user

Sharing an encrypted dataset, publishing its history, or copying it into another
user's history, a data library or an exported archive shares its ciphertext, but
never the ability to compute on it. Grants are stored separately from datasets,
are never serialized by the API, and are not copied with datasets. Another user
can only compute on a shared encrypted dataset after authorizing it through their
own user service, which only works if their own private key can open the dataset
(the file was encrypted for several recipients).

Galaxy can't check that a submitted grant actually opens the dataset: that would
require Galaxy to decrypt the header. An invalid grant only causes its submitter's
own jobs to fail.

## What is and isn't protected

At rest, in Galaxy's object stores, encrypted datasets and the outputs of jobs
using them are always Crypt4GH ciphertext. Plaintext exists only on the compute
host, while a job runs: in `_protected`, and in whatever files the tool writes in
its working directory. Galaxy never holds users' private keys.

The compute host necessarily sees plaintext, and Galaxy's own code running there
decrypts and encrypts the data. The following are **outside** the protection:

- **Tools.** A tool can write the plaintext anywhere it can reach, including the
  network. Only make vetted tools available on destinations running protected
  jobs, and block network egress from jobs.
- **Tool standard output and error.** They are kept in the job's streams in
  Galaxy's database, because Galaxy uses them to detect tool errors. For protected
  jobs they are not copied into the outputs' info field. Tools printing data to
  standard output or error leak it.
- **Tool-provided output names and info.** Names and info set by tools through
  `galaxy.json` are stored in the database in clear. Metadata provided this way is
  ignored for encrypted outputs.
- **Administrators of the compute hosts**, and anyone else with access to the job
  directories while jobs run.
- **A shared filesystem.** When the compute hosts share the job directories with
  the Galaxy server, anyone with access to the Galaxy host can read the plaintext
  of running jobs. Such a deployment is a single trust domain.
- **Direct calls to the compute service.** The compute service does not
  authenticate its callers. A process on a host allowed to reach its re-encryption
  routes, holding a header encrypted to a compute key, can re-encrypt it to a key
  of its choice. Restrict which hosts can reach these routes (see
  [Compute service](#compute-service)) and isolate jobs from each other.

## Deployment requirements

- **Job isolation.** Jobs must not be able to read each other's job directories:
  run jobs as the real user, in containers, or on Pulsar.
- **No network egress** from jobs, and a vetted set of tools on the destinations
  that run protected jobs. Use [TPV](https://total-perspective-vortex.readthedocs.io/)
  or tool destination rules to route jobs reading encrypted datasets to them.
- **The compute service** must be reachable from the compute hosts, and its
  `/get_compute_key_info` route from the users' machines. See
  [Compute service](#compute-service).
- **Job destinations** need extended metadata and outputs written to the job
  directory. See [Job destinations](#job-destinations).
- **Containers.** Custom `docker_volumes` or `singularity_volumes` must still
  include `$job_directory`, where the decrypted inputs are.
- **The `crypt4gh` Python package** must be installed wherever jobs run. See
  [Installation](#installation).
- **A private object store** for encrypted data is recommended. It is not
  required for confidentiality, but it limits who can read even the ciphertext.

### Pulsar

The recommended production topology is [Pulsar](https://pulsar.readthedocs.io/)
without a shared filesystem, so that the Galaxy server never has access to
plaintext. Inputs are staged to the Pulsar host encrypted, decrypted there, and
outputs are encrypted there before they are stored. Pulsar destinations running
protected jobs need, in addition to the requirements below:

- `remote_metadata: true`, so outputs are encrypted on the Pulsar host. With
  `metadata_strategy: extended`, the Pulsar host then writes outputs directly to
  Galaxy's object store, which must be reachable from it.
- `rewrite_parameters: true`, the default of the REST, message queue and
  embedded Pulsar runners.
- Outputs staged to the remote job directory: don't map outputs to the `none`
  file action. Don't set `outputs_to_working_directory` either, Pulsar relocates
  outputs anyway.
- `crypt4gh` installed on the Pulsar host (see [Installation](#installation)), and
  the compute service reachable from it.

Galaxy always asks Pulsar to remove the remote job directory of protected jobs.
Protected jobs have been tested with Pulsar's embedded and message queue runners;
validate them on your own Pulsar hosts before production use.

When the compute hosts share the job directory with the Galaxy server instead,
keep in mind that such a deployment is a single trust domain.

## Installation

The `crypt4gh` Python package is needed by the job script and the metadata step
on the compute hosts.

- When jobs run with Galaxy's own virtualenv, `crypt4gh` is installed as a
  conditional dependency once `crypt4gh_enabled` is set (by `run.sh`, or
  `./scripts/common_startup.sh`).
- When compute hosts install the `galaxy-job-execution` package instead, install
  it with the `crypt4gh` extra: `pip install 'galaxy-job-execution[crypt4gh]'`.
- With [containerized metadata](containerized_metadata.md), the metadata image
  must include `crypt4gh`, and must be able to reach the compute service and any
  certificates configured for it.

Install the recryptor service following its
[documentation](https://github.com/elixir-europe/crypt4gh-recryptor-service). Users
install and run it on their own machines in user mode.

## Configuration

### Galaxy

In `galaxy.yml`:

```yaml
galaxy:
  crypt4gh_enabled: true
  # The compute service, as reached from the compute hosts.
  crypt4gh_recryptor_url: https://recryptor.example.org
  # The user service, as reached from the users' browsers. This is the default.
  crypt4gh_user_service_url: https://localhost:61357
  # Optional, see below.
  #crypt4gh_recryptor_timeout: 30
  #crypt4gh_recryptor_ca_cert: /etc/galaxy/recryptor-ca.pem
  #crypt4gh_recryptor_client_cert: /etc/galaxy/recryptor-client.pem
  #crypt4gh_recryptor_client_key: /etc/galaxy/recryptor-client-key.pem
```

The [configuration options reference](options.rst) describes each option.
Paths of certificates and keys are read on the compute hosts. Requests to the
compute service fail after `crypt4gh_recryptor_timeout` seconds, and are retried
three times on connection and server errors.

Users running their user service on another port can set it in their
preferences when the `crypt4gh_recrypt_service` section is enabled in
`user_preferences_extra_conf.yml`:

```yaml
preferences:
  crypt4gh_recrypt_service:
    description: Crypt4GH recryptor service running on your machine
    inputs:
      - name: port
        label: Port number of your local recryptor service
        type: text
        required: False
        value: "61357"
```

### Job destinations

Every destination running jobs that decrypt datasets must use:

- `metadata_strategy: extended`. Output encryption runs in the metadata step,
  which must run on the compute host. `celery_extended`, `directory` and `legacy`
  are refused.
- Tools writing their outputs into the job directory, so they never write
  unencrypted data to the object store: `outputs_to_working_directory: true`, or
  outputs staged to the remote job directory on Pulsar.
- Metadata collected within the job, so outputs are encrypted on the compute
  host before the decrypted data is removed. Destinations with
  `embed_metadata_in_job: false`, and runners that always collect metadata after
  the job (Kubernetes, AWS Batch, GCP Batch, Chronos, GoDocker), can't run them.
- No task splitting.
- `remote_metadata: true` and `rewrite_parameters: true` on Pulsar destinations.

The `crypt4gh_recryptor_*` options can be overridden per destination, for
instance when the compute hosts reach the compute service through another network
path or need other certificates. All destinations must use the same compute
service: grants are bound to its compute keypairs.

```yaml
execution:
  environments:
    protected:
      runner: slurm
      metadata_strategy: extended
      outputs_to_working_directory: true
      crypt4gh_recryptor_url: https://recryptor.internal.example.org:61358
      crypt4gh_recryptor_ca_cert: /etc/galaxy/recryptor-ca.pem
      crypt4gh_recryptor_client_cert: /etc/galaxy/recryptor-client.pem
      crypt4gh_recryptor_client_key: /etc/galaxy/recryptor-client-key.pem
limits:
  - type: walltime
    value: "24:00:00"
```

Galaxy refuses to start a protected job when one of its grants expires within the
job's maximum run time, so configure a walltime limit matching what your
destinations allow (see [Lifetimes](#lifetimes)).

Jobs are refused when the destination doesn't meet these requirements, with a
message asking the user to contact the administrator. Jobs that don't decrypt
anything are not affected.

### Compute service

The compute service has three routes, with different callers:

| Route                              | Called by                      | Must be reachable from |
| ---------------------------------- | ------------------------------ | ---------------------- |
| `POST /get_compute_key_info`       | the user services              | the users' machines    |
| `POST /recrypt_header_to_job_key`  | jobs, before the tool          | the compute hosts only |
| `POST /recrypt_header_to_user_key` | jobs, while collecting outputs | the compute hosts only |

Run the compute service behind a proxy restricting the two re-encryption routes
to the compute hosts, ideally with mutual TLS. For example, with nginx:

```nginx
server {
    listen 443 ssl;
    server_name recryptor.example.org;
    # ssl_certificate, ssl_certificate_key, ...
    ssl_client_certificate /etc/nginx/compute-hosts-ca.pem;
    ssl_verify_client optional;

    location = /get_compute_key_info {
        proxy_pass https://127.0.0.1:61358;
    }

    location ~ ^/recrypt_header_to_(job|user)_key$ {
        if ($ssl_client_verify != SUCCESS) {
            return 403;
        }
        allow 10.1.0.0/16;  # compute hosts
        deny all;
        proxy_pass https://127.0.0.1:61358;
    }

    location / {
        return 404;
    }
}
```

Users configure their user service's `compute_host` and `compute_port` to point
to the public address of the compute service, and the user service must trust
its TLS certificate. The user service always connects to
`https://<compute_host>:<compute_port>`, so `compute_port` is the port of the
proxy (`443` in the example above), not the compute service's own port.

The user service is called by the user's browser from the Galaxy web page. The
released user service accepts requests from any origin. A setting restricting it
to configured origins is proposed in
[crypt4gh-recryptor-service#3](https://github.com/elixir-europe/crypt4gh-recryptor-service/pull/3);
once available, users must add the Galaxy server's origin to it. The browser must
also trust the user service's certificate, which the service creates with
[mkcert](https://github.com/FiloSottile/mkcert).

## Lifetimes

- The compute service issues compute keypairs valid for 7 days, and refuses to
  use them within 1 day of their expiration.
- A grant is only usable by a job if it is still valid, at dispatch, for the
  longer of 1 day and the configured walltime limit plus 1 hour. Outputs are
  encrypted after the tool ran, so the key must outlive the job.
- Users authorize datasets again once their grant expires. The key icon shows
  until when a dataset is authorized.
- Outputs of a job are granted with the compute keypair expiring last among the
  job's inputs.

## Supported tools and outputs

Encrypted datasets are decrypted for parameters accepting their inner format,
including parameters accepting any format (`data`), and inside conditionals,
repeats and collections. Parameters explicitly accepting a Crypt4GH format
(`c4gh` or a `.c4gh` wrapper) receive the encrypted file, and so do Galaxy's
internal tools, such as metadata setting and collection operations.

Supported outputs:

| Output                                                            | Protected                                             |
| ----------------------------------------------------------------- | ----------------------------------------------------- |
| declared outputs                                                  | yes                                                   |
| `from_work_dir` outputs, including globs                          | yes                                                   |
| discovered datasets (`discover_datasets` patterns, `galaxy.json`) | yes                                                   |
| collection elements, including discovered ones                    | yes                                                   |
| extra files of composite outputs                                  | yes, each as its own Crypt4GH file (see limitations)  |
| outputs written directly to the object store                      | refused: outputs must be written in the job directory |
| unnamed outputs (`__unnamed_outputs` in `galaxy.json`)            | refused                                               |
| linked data (`link_data_only`)                                    | refused                                               |

Limitations:

- Only regular command-line tools can decrypt data. Interactive tools, data
  managers, expression tools and other special tool types are refused.
- Tools see the wrapper datatype in `$input.ext` (for example
  `fastqsanger.c4gh`). The decrypted file name carries the inner extension.
- Metadata files of encrypted inputs, such as BAM indexes, are not available to
  tools.
- Composite datasets uploaded by users can't be decrypted: the user service only
  authorizes the primary file. Composite outputs of protected jobs are supported,
  but their extra files are authorized by the job that wrote them: further jobs
  can use them until that job's compute key expires, about 7 days later.
  Authorizing such an output again (key icon) only renews its primary file.
- The same encrypted dataset can't be passed both decrypted and encrypted to the
  same job.
- With the job cache, jobs decrypting data are only reused from the same user's
  earlier jobs, since outputs are encrypted for the user who ran the job. Reused
  outputs keep the authorization recorded by the original job, so users authorize
  them again once it expires.

## Failures and cleanup

Protected jobs fail closed:

- **Before dispatch:** a missing or expiring grant, or a destination not meeting
  the requirements, fails the job with an explanation. Users are told when they
  submit the job if the dataset is already available.
- **Decryption:** if the compute service can't be reached (after retries), doesn't
  know or no longer accepts the compute key (`404`, `410`), or can't open the
  header (`422`), the partially decrypted inputs are removed, the tool doesn't run,
  and the job fails with "Job setup failed". The message tells the user to
  authorize the dataset again when that would help.
- **Output encryption:** if an output can't be encrypted, metadata collection
  fails and the job fails. Outputs Galaxy can't verify as encrypted are purged.
- **Cleanup:** if the decrypted data can't be removed from the compute host, the
  job fails, but its verified encrypted outputs are kept.

Job errors are shown to users, so they name the setting or error involved but
never include the compute service's address. To see the underlying error while
setting up a destination, for example a TLS problem, set
`crypt4gh_recryptor_verbose_errors: true` on that destination; turn it off again
afterwards, since users of that destination see these details too. Alternatively,
reproduce a job's request from a compute host with the destination's settings.
Any HTTP response, such as `422` for the empty request, means the connection and
certificates work:

```sh
curl --cacert <ca_cert> --cert <client_cert> --key <client_key> \
  -X POST https://<compute service>/recrypt_header_to_job_key -d '{}'
```

Headers, plans, keys and the compute service's requests and responses are never
logged. The `crypt4gh` library's own logging is limited to warnings, since it logs
session keys at debug level.

## Telling users

Users need the recryptor service running on their machine in user mode, with
their Crypt4GH key pair and its `compute_host` and `compute_port` pointing to your
compute service. Let them know that:

- encrypted uploads are detected automatically;
- the key icon of an encrypted dataset authorizes their own jobs to use it, and
  needs to be clicked again when the authorization expires;
- outputs of their jobs are encrypted for them and can be used in further jobs
  directly;
- sharing an encrypted dataset doesn't let others compute on it, unless it was
  also encrypted for them and they authorize it themselves.
