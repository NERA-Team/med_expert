# MedExpert

Offline medication reference app built with Kotlin Multiplatform and Compose. The SQLite database is bundled with the app; no database server is required.

## Requirements

- JDK 17 (configure `JAVA_HOME` if needed).
- Internet access on the first Gradle build to download dependencies.
- **Android:** Android Studio with Android SDK 37 and an emulator or device (Android 8.0/API 26+).
- **iOS:** macOS, Xcode, and an iOS Simulator. The iOS app is in `iosApp/`.
- **Desktop:** macOS, Windows, or Linux with a graphical desktop environment.
- **Rebuild the database only:** Python 3.10+ and `python-docx` from `parser/requirements.txt`.

## Run the desktop app

macOS / Linux:

```sh
./gradlew :composeApp:run
```

Windows (PowerShell):

```powershell
.\gradlew.bat :composeApp:run
```

## Run on Android

Open the project in Android Studio, let Gradle sync, select an emulator or connected device, and run the `androidApp` configuration. Or use the command line:

```sh
./gradlew :androidApp:installDebug
```

On Windows, use `gradlew.bat` instead of `./gradlew`.

## Run on iOS (macOS only)

Open `iosApp/iosApp.xcodeproj` in Xcode, select an iOS Simulator, then Build and Run. Xcode invokes Gradle to build the shared Kotlin framework.

## Build

```sh
./gradlew :composeApp:build
./gradlew :androidApp:assembleDebug
```

For Windows, replace `./gradlew` with `gradlew.bat`. Desktop installers can be created with:

```sh
./gradlew :composeApp:createDistributable
```

## Database and parser

The bundled database is `composeApp/src/commonMain/composeResources/files/med_expert.db`. It is installed locally on first launch and the app works offline.

To regenerate it from the DOCX source:

```sh
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install -r parser/requirements.txt
python parser/parse_docx.py
python parser/parse_docx.py --verify
```

The parser replaces the bundled database with a fresh SQLite database. Review changes before committing.
