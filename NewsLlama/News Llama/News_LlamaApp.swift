import SwiftUI
import Sparkle

@main
struct News_LlamaApp: App {
    @State private var appViewModel = AppViewModel()
    @State private var newsletterViewModel = NewsletterViewModel()
    @State private var interestViewModel = InterestViewModel()

    private let updaterController: SPUStandardUpdaterController

    init() {
        updaterController = SPUStandardUpdaterController(
            startingUpdater: true,
            updaterDelegate: nil,
            userDriverDelegate: nil
        )
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(appViewModel)
                .environment(newsletterViewModel)
                .environment(interestViewModel)
        }
        .commands {
            CommandGroup(after: .appInfo) {
                CheckForUpdatesView(updater: updaterController.updater)
            }
            CommandGroup(replacing: .newItem) {
                Button("New Profile") {
                    appViewModel.logout()
                }
                .keyboardShortcut("n")
            }
        }

        Settings {
            SettingsView(updater: updaterController.updater)
                .environment(appViewModel)
                .environment(interestViewModel)
        }
    }
}

struct CheckForUpdatesView: View {
    @ObservedObject private var checkForUpdatesViewModel: CheckForUpdatesViewModel

    init(updater: SPUUpdater) {
        self.checkForUpdatesViewModel = CheckForUpdatesViewModel(updater: updater)
    }

    var body: some View {
        Button("Check for Updates...") {
            // Sparkle handles this through the updater controller
        }
        .disabled(!checkForUpdatesViewModel.canCheckForUpdates)
    }
}
