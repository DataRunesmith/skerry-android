# Skerry for Android

An SSH and host-management app for Android, written in Kotlin.

## Build and test

Requires JDK 17 or newer and the Android SDK (platform 35).

```sh
cd Android
./gradlew testDebugUnitTest
./gradlew assembleDebug
```

Point `ANDROID_HOME` at your SDK, or create `Android/local.properties` with `sdk.dir=...`. Set your own application ID and signing configuration in `Android/app/build.gradle.kts` before distributing a build.

<!-- coderabbit-ai-generated:v1 -->

## Documentation site

Requires Python 3.11 or newer. From the repository root:

```sh
python -m venv .venv-docs
. .venv-docs/bin/activate
pip install --no-deps -r requirements-docs.txt
python scripts/docs.py build --clean --strict
python scripts/docs.py serve
```

Use these commands for local builds and previews to resolve repository links and
the home page template. The wrapper restores unchanged source files on exit.
Repository identity comes from `REPOSITORY`, then `GITHUB_REPOSITORY`, then the
GitHub `origin` remote. For a source archive or a different remote host, set
`REPOSITORY=owner/repo`. Actions supplies `REPOSITORY` from `github.repository`.
