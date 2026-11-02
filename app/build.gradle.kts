plugins {
    id("com.android.application")
}

android {
    namespace = "com.kwkaye.flipfellawatch"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.kwkaye.flipfellawatch"
        // Watch Face Format needs Wear OS 4 (API 33) or newer.
        minSdk = 33
        targetSdk = 34
        versionCode = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()
        versionName = "0.2.${System.getenv("GITHUB_RUN_NUMBER") ?: "0"}"
    }

    signingConfigs {
        getByName("debug") {
            // Committed on purpose so every build installs over the last one.
            storeFile = file("debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        getByName("debug") {
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}
