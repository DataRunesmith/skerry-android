buildscript {
    repositories {
        google()
        mavenCentral()
    }
    configurations.classpath {
        resolutionStrategy.force(
            "org.bouncycastle:bcprov-jdk18on:1.87",
            "org.bouncycastle:bcpkix-jdk18on:1.87",
            "org.bouncycastle:bcutil-jdk18on:1.87",
            "org.bitbucket.b_c:jose4j:0.9.7",
            "org.jdom:jdom2:2.0.6.1",
            "com.google.guava:guava:33.8.0-jre",
        )
    }
    dependencies {
        classpath("com.android.tools.build:gradle:9.5.1")

        // AGP exposes these as transitive build-tool dependencies, but GitHub
        // dependency submission can alert on transitive Gradle dependencies
        // without Dependabot being able to update them in the repository.
        // Keep them explicit so security fixes remain both enforced and
        // machine-updatable without removing dependency-graph coverage.
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.4.21")
        classpath("org.apache.commons:commons-lang3:3.21.0")
    }
}

// Android Gradle Plugin currently requests build-tool transitive
// dependencies with known vulnerabilities. Keep AGP stable while selecting
// patched buildscript-classpath versions. Explicit classpath entries above
// make Kotlin Gradle Plugin and Commons Lang directly updateable by Dependabot;
// the forced entries cover the remaining build-only transitives. None of these
// dependencies are added to the application runtime.

// Android Lint runs from its own tool classpath, the androidLintTool
// configuration that AGP adds to each Android project. The classpath forcing in
// buildscript above does not reach it, so lint would otherwise resolve
// vulnerable versions of these libraries. The constraints only raise a version,
// never lower it, and androidLintTool is never part of the application runtime.
subprojects {
    val patchedLintToolDependencies = listOf(
        "org.bouncycastle:bcprov-jdk18on:1.87",
        "org.bouncycastle:bcpkix-jdk18on:1.87",
        "org.bouncycastle:bcutil-jdk18on:1.87",
        "com.google.guava:guava:33.8.0-jre",
        "org.apache.commons:commons-lang3:3.21.0",
        "org.apache.httpcomponents:httpclient:4.5.14",
    )
    configurations.matching { it.name == "androidLintTool" }.configureEach {
        patchedLintToolDependencies.forEach { notation ->
            dependencyConstraints.add(project.dependencies.constraints.create(notation))
        }
    }
}

// CodeQL Default Setup uses Gradle autobuild for Kotlin and invokes the generic
// testClasses task. Android Gradle Plugin does not create that lifecycle task,
// so map it to an Android debug build that compiles the Java/Kotlin sources.
tasks.register("testClasses") {
    group = "verification"
    description = "Build Android JVM/Kotlin classes for CodeQL autobuild"
    dependsOn(":app:assembleDebug")
}
