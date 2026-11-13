# Get started

## Requirements

JDK 17 or newer and the Android SDK (platform 35). Point `ANDROID_HOME` at your SDK, or create `Android/local.properties` with `sdk.dir=...`.

## Build and test

```sh
cd Android
./gradlew testDebugUnitTest
./gradlew assembleDebug
```

Set your own application ID and signing configuration in `Android/app/build.gradle.kts` before distributing a build.
