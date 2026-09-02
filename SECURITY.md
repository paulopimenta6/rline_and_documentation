# Security Policy

## Project Scope

This is a local scientific modeling repository, not a deployed service. It has
no supported public endpoint, account system, or production data store. The
main security boundary is the workstation or CI runner executing Fortran
binaries and Python or shell automation against local input files.

The current default branch receives security fixes on a best-effort basis.
Historical third-party binaries, source snapshots, datasets, and documents are
retained for provenance and are not independently supported by this project.

## Reporting A Vulnerability

Do not publish an unpatched vulnerability, exploit, secret, or sensitive input
in a public issue. Use GitHub private vulnerability reporting from the
repository's **Security** tab when it is enabled. If that option is unavailable,
open a public issue containing only a request for a private maintainer contact;
do not include vulnerability details.

Include the affected path and revision, impact, prerequisites, a minimal safe
reproduction, and any proposed mitigation. Remove personal, proprietary, and
regulated data from reports. Maintainers will acknowledge and triage reports on
a best-effort basis; this project does not promise a fixed response or release
service level.

Examples within scope include command or argument injection, unsafe temporary
file handling, traversal outside a requested working directory, memory-safety
issues reachable through model inputs, dependency compromise, and accidental
credential disclosure. Numerical defects without a security impact should be
reported as ordinary bugs, with enough information to reproduce the scientific
result.

## Safe Local Use

Build model executables from reviewed source when possible. Treat bundled
historical executables and all untrusted model inputs as potentially unsafe.
Run them with least privilege in an isolated directory or container, without
secrets or access to unrelated data. Review shell scripts before execution and
do not run the models as root.

CI artifacts and scientific outputs can reveal local paths, configuration, or
input content. Inspect them before sharing. This repository must not be used to
store credentials or sensitive operational datasets.

For a vulnerability in AERMET, AERMOD, RLINE, an EPA document or dataset, or
another dependency, also follow that upstream project's reporting process. A
report here is still useful when repository integration increases the impact,
but maintainers cannot assign terms or issue upstream fixes on a third party's
behalf.
