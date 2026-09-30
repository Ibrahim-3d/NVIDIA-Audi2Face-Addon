# Licensing — 2026-09-30

## Current license

Audio2Face for Blender is **GPL-3.0-or-later**. The root LICENSE now matches
the grant already present in `nvidia_audio2face/LICENSE.txt`, the
`SPDX:GPL-3.0-or-later` Blender manifest entry, and the README.

The existing package copyright notice, including its original author and
year, is retained. The complete unmodified GPL v3 text is also included in
`nvidia_audio2face/COPYING` so that it travels with an add-on-only archive.

## Historical mismatch

Commit `9d231b5b7bf4b5c82d7e5994cd98ec2fdcde3fe2` introduced an AGPL-3.0 root
license despite the package's existing GPL grant. That root text is preserved
verbatim in `LICENSES/AGPL-3.0-historical.txt`. This correction does not revoke
any independently granted historical rights or rewrite older tags/archives.

## Third-party scope

The existing NVIDIA, grpcio, protobuf and USC ICT-FaceKit license texts remain
unchanged under `nvidia_audio2face/LICENSES/`. The add-on license does not
relicense model assets, vendor code, API services or third-party trademarks.
Service availability, provider terms and charges are separate from GPL rights.

## Distribution

Include the whole add-on source package, `LICENSE.txt`, `COPYING`, all required
`LICENSES/` texts, and notices required by the exact dependency wheels shipped.
Any source-delivery obligations for a particular bundled dependency remain
applicable; this notice is not a wheel-by-wheel compliance certification.
Official paid distribution or support does not remove recipients' GPL rights.

No Python behavior, manifest settings, dependency versions or previously
published release assets were changed in this license-hygiene pass.
