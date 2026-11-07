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
