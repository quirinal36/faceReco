# FaceReco security and privacy operations

FaceReco processes biometric identifiers and face images. Treat every face image,
face thumbnail, embedding, face-database record, attendance record, export,
backup, and diagnostic artifact derived from them as restricted biometric data.
Names, device identifiers, and attendance data are restricted personal data.

This document defines the P0 deployment baseline. It is an operating requirement,
not a claim that bearer authentication or filesystem permissions alone make a
public deployment safe.

## Supported trust boundary

The API listens on `127.0.0.1` by default. Keep that default whenever the browser,
camera, and API run on one machine.

The supported production entrypoint is `backend/server.py`. Legacy camera,
command-line, test-image, and demo entrypoints may display or print recognized
identities and are not approved for production use. Run them only with synthetic
fixtures on an isolated development host; do not use them to enroll or process
real people.

- Never expose the edge API directly to the public internet. Do not use
  `0.0.0.0`, a public address, router port forwarding, or a public load balancer.
- A development or test host may listen on one explicit private LAN or VPN
  address only after setting both `FACERECO_BIND_HOST=<that-address>` and
  `FACERECO_ALLOW_NON_LOOPBACK=true`. Restrict the host firewall to named source
  devices, use TLS at a trusted VPN/zero-trust boundary, and remove the opt-in
  after the test. `FACERECO_ALLOW_NON_LOOPBACK` is not permission to publish the
  service.
- A production edge must set `FACERECO_ENV=production` and bind inbound API
  traffic to loopback only. Production rejects non-loopback binds even if the
  development opt-in is present. Only `development`, `prod`, and `production`
  are accepted environment values; unknown values and spelling mistakes fail
  startup instead of falling back to development behavior.
- The application also compares each accepted TCP socket with
  `FACERECO_BIND_HOST`, so an accidental wildcard Uvicorn CLI argument does not
  silently widen API access. This defense does not make a wildcard listener
  acceptable and does not replace the service/socket and host-firewall policy.
- The production edge initiates outbound HTTPS connections to the approved Edu
  Manager endpoint. Edu Manager must not initiate an inbound connection to this
  API. Egress should be limited to TCP 443 for the exact Manager host and any
  separately approved operational dependency; deny general internet egress.

CORS is only a browser control; it is not authentication or a network firewall.
Set `FACERECO_CORS_ORIGINS` to a comma-separated list of exact origins, including
scheme and port, for example:

```text
FACERECO_CORS_ORIGINS=https://127.0.0.1:5173
```

Origins must not contain a path, query, or fragment. Wildcards are rejected.
`localhost` and `127.0.0.1` are different origins, so list only the one actually
used. If unset, the development defaults are the exact HTTP and HTTPS origins for
`localhost:5173` and `127.0.0.1:5173`; production operators should narrow the
list to the deployed UI origin.

## Bearer roles

The P0 edge has two independent, local bearer principals:

| Role | Intended holder | Access |
| --- | --- | --- |
| `operator` | The local management UI or an authorized human-operated client | Enrollment, face list and authenticated thumbnails, deletion/merge, camera management and stream, and attendance administration |
| `device` | One provisioned local kiosk/device process | Device-only liveness operations; no enrollment, face browsing, deletion, or attendance administration |

`GET /api/health` is intentionally minimal and unauthenticated. Every other
documented API call requires the appropriate bearer; `GET /api/auth/whoami` can
be used to verify a credential's role. A device token is not a second operator
token. The P0 design supports one local device principal; fleet identity and
per-device revocation belong in the Edu Manager integration.

Send credentials only in the request header:

```http
Authorization: Bearer <credential>
```

Never put a token in a URL, query parameter, form field, cookie, filename, or
log message. URL credentials leak through browser history, referrers, proxy/access
logs, screenshots, and copied links. A plain `<img src>` cannot safely attach the
required header; use an authenticated client that fetches the resource and
renders a local object URL. Do not work around this with `?token=...`.

## Provisioning and rotating credentials

Generate two different cryptographically random values of at least 32 characters.
Do not reuse an Edu Manager credential. Prefer secret files supplied by the OS
service manager:

- `FACERECO_OPERATOR_TOKEN_FILE=/absolute/path/to/operator.token`
- `FACERECO_DEVICE_TOKEN_FILE=/absolute/path/to/device.token`

For local development only, the corresponding `FACERECO_OPERATOR_TOKEN` and
`FACERECO_DEVICE_TOKEN` environment variables are accepted. Configure either the
value or the `_FILE` form for each role, never both. The repository's
`.env.example` is an inventory of settings with deliberately invalid
`CHANGEME` placeholders; it is not loaded automatically and must never be used as
a credential source.

Example Linux provisioning (replace the sample account name with the real
dedicated service account):

```bash
sudo install -d -o facereco -g facereco -m 0700 /var/lib/facereco/secrets
sudo -u facereco sh -c 'umask 077; openssl rand -base64 48 > /var/lib/facereco/secrets/operator.token'
sudo -u facereco sh -c 'umask 077; openssl rand -base64 48 > /var/lib/facereco/secrets/device.token'
sudo -u facereco chmod 0600 /var/lib/facereco/secrets/operator.token /var/lib/facereco/secrets/device.token
```

Do not print, paste, email, commit, or place generated values on a command line.
On Windows, store secrets under a non-shared service directory, disable inherited
ACLs, and grant read access only to the dedicated FaceReco service account (and
`SYSTEM` if the service manager requires it). Do not grant `Users`,
`Authenticated Users`, or an interactive shared account access.

Rotate credentials on a schedule, whenever an operator/device is reprovisioned,
and immediately after suspected disclosure:

1. Generate new, distinct operator and device secrets using the same protected
   path and permissions.
2. Distribute them through the service secret mechanism, never through Git,
   tickets, chat, or screenshots.
3. Restart the edge and verify each role with `/api/auth/whoami` over loopback.
4. Remove the old values from clients and secret stores. The P0 API accepts one
   value per role, so plan a short maintenance window rather than leaving old and
   new credentials valid together.
5. Review access and application logs for misuse without copying biometric data
   into the incident record.

## Model artifacts and egress

Pre-provision approved InsightFace model artifacts before an edge starts. Download
them only in a controlled staging/build environment, verify them against an
approved version and checksum manifest, scan them, then transfer the frozen model
root to the encrypted edge. For the default bundle, the required layout is
`$FACERECO_MODEL_ROOT/models/buffalo_l/*.onnx`. An approved alternative sets
`FACERECO_MODEL_NAME` and uses the matching
`$FACERECO_MODEL_ROOT/models/$FACERECO_MODEL_NAME/` directory. Make artifacts
read-only to the service where practical.

Do not grant a production runtime general internet access and do not rely on
InsightFace's automatic download behavior. Production startup fails unless the
configured root and bundle directory are real, non-symlink directories and the
bundle contains at least one regular, non-symlink `.onnx` file directly inside
it. Production uses only the selected bundle and does not fall back to another
model. A missing model is a provisioning failure; remediate it through the
controlled artifact workflow, not by temporarily opening edge egress.

## Storage and permissions

Use a dedicated OS service account. On POSIX systems, biometric-data and secret
directories must be mode `0700`; files, SQLite databases and journals,
embeddings, thumbnails, tokens, exports, and backups must be mode `0600`. Ensure
the service account owns them, set `umask 077`, and do not place the data tree in
a synced or shared home directory. Reject symlinks and junctions in managed data
paths.

On Windows, run under a dedicated service account on an NTFS volume. Disable ACL
inheritance on the data, model, secret, export, and backup directories; remove
broad principals; and grant only that service account the minimum required
rights. Administrators and backup agents must be explicitly approved and audited.
Do not use FAT/exFAT, a user Downloads folder, OneDrive, or another consumer-sync
location for biometric data.

The three multipart image endpoints authenticate before reading the body,
require `Content-Length`, cap the complete request at the 5 MiB image allowance
plus 64 KiB of multipart framing, and keep accepted parts in memory. Oversized
requests return `413`; unbounded chunked uploads return `411`. This prevents raw
frames from being spooled to the host's general-purpose temporary directory.
Any reverse proxy or security agent in front of the loopback API must also have
request buffering disabled or place its buffers on the same verified encrypted
volume; application controls cannot protect a proxy's separate temp path.

### P0 encryption baseline and startup gate

The P0 at-rest baseline is a host-managed encrypted volume: LUKS2 on Linux or
BitLocker on Windows. The volume must cover `backend/data`, SQLite temporary/WAL
files, exports, backups kept on the edge, and any swap/hibernation area that can
contain process memory. Store recovery material separately from the device and
restrict unlock privileges to the approved boot/service workflow.

Production additionally requires:

```text
FACERECO_ENCRYPTED_STORAGE_VERIFIED=true
```

This variable is an operator attestation and startup gate, not encryption. Set it
only after verifying that the actual data paths resolve onto the encrypted volume,
the volume is unlocked through the approved mechanism, permissions/ACLs are
correct, and backup destinations have equivalent protection. Production refuses
to start without the attestation.

### Planned application-level encryption

Filesystem encryption is the P0 baseline. A future defense-in-depth design should
use reviewed components rather than custom cryptography:

- AES-256-GCM envelope encryption for each image/embedding/export with a unique
  nonce, authenticated metadata, and format/key versioning.
- Random data-encryption keys wrapped by a key-encryption key held in a KMS, HSM,
  TPM/OS keystore, or equivalent managed secret service. Data and wrapping keys
  must not be stored beside ciphertext. Rotation must support key IDs, rewrap or
  controlled re-encryption, audit, revocation, and recovery testing.
- SQLCipher (or a comparably reviewed encrypted database) for attendance and
  metadata, including encrypted journals, WAL, and temporary files. Supply its
  key through the service secret mechanism and fail closed on key/configuration
  errors.

Until that design is implemented and tested, do not claim that individual
FaceReco records or SQLite fields are application-encrypted.

## Backup, restore, retention, and deletion

- Minimize collection and define a documented retention period for enrollment
  samples, embeddings, attendance records, exports, and backups. Do not retain
  raw registration uploads; only the bounded thumbnail required by the product
  may be retained.
- Create backups only to an approved encrypted target using an approved backup
  tool. A plain `tar`/ZIP file is not an acceptable backup. Backups inherit the
  highest biometric classification, must be access-controlled, inventoried,
  integrity-checked, and expired on schedule.
- Take a consistent backup (stop application writes or use a database-aware
  snapshot), record a non-sensitive manifest and integrity hashes, then restart.
  Do not include bearer tokens in a data backup.
- Test restore procedures on an isolated encrypted host with the same service
  ownership and permissions. Verify integrity, database consistency, model
  version, and record counts without publishing sample images. Rotate runtime
  credentials after disaster recovery rather than restoring old token files.
- A person's deletion must cover metadata, every embedding/sample, thumbnail,
  derived export, and associated attendance data where policy and law permit.
  Propagate a tombstone or deletion job to backups and Edu Manager under the
  retention policy, and record only a non-biometric audit reference.
- Overwriting one file is not reliable secure erasure on SSD/flash media. Use
  encrypted-volume crypto-erasure or approved device destruction at
  decommissioning, and account for snapshots and replicas.

## Incident response

If a token, face image, embedding, database, attendance record, backup, or device
may have been exposed:

1. Isolate the edge from all networks while preserving volatile evidence under
   the incident procedure. Do not upload biometric evidence to a public issue.
2. Revoke and rotate both local role tokens as appropriate, plus affected Edu
   Manager/device credentials. Block affected endpoints or the device until the
   scope is known.
3. Preserve access-controlled logs and hashes; avoid copying face images,
   embeddings, bearer values, request bodies, or personal names into ordinary
   logs, chat, tickets, or crash reports.
4. Determine the affected people, artifact types, time window, backups/replicas,
   recipients, and whether notification or regulatory reporting is required.
5. Eradicate the cause, rebuild from trusted artifacts, restore onto verified
   encrypted storage, test the boundary, and document follow-up controls.

Screenshots are data, not harmless documentation. Use synthetic faces and names
for documentation and tests. Before publishing or attaching a screenshot, inspect
the entire frame for faces, names, attendance information, paths, tokens, terminal
history, and browser developer tools.

Deleting a biometric file or screenshot from the current Git checkout does not
remove it from Git history, forks, pull-request caches, package artifacts, CI
artifacts, browser caches, or downstream clones. If real biometric data ever
entered Git or a public screenshot, treat it as a disclosure: remove public
access, preserve the incident record privately, identify every copy, obtain the
required privacy/legal guidance, replace it with synthetic material, and use a
coordinated history-rewrite and cache/artifact purge when required. Assume a
previously public biometric object cannot be made secret again merely by rewriting
history.

## Release checklist

- API binds to `127.0.0.1`; there is no public/LAN listener or port forward.
- Only outbound HTTPS to the approved Edu Manager host is allowed in production.
- Operator and device secrets are different, random, protected, and not in URLs.
- CORS contains only the exact deployed UI origin; there is no wildcard.
- `/data` and biometric files return no unauthenticated response; thumbnails are
  available only through the operator-authorized endpoint.
- Model artifacts are frozen, verified, locally present, and runtime downloads are
  blocked.
- The data/backup paths are on verified LUKS2 or BitLocker storage; production's
  encrypted-storage gate is set only after verification.
- POSIX modes or Windows service-account ACLs, retention, backup/restore,
  deletion, and incident-response procedures have been tested.
- Screenshots, Git history, logs, and build/CI artifacts contain no real biometric
  or bearer material.
