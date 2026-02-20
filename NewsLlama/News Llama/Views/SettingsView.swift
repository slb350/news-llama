import SwiftUI
import Sparkle

struct SettingsView: View {
    private let updater: SPUUpdater

    init(updater: SPUUpdater) {
        self.updater = updater
    }

    var body: some View {
        TabView {
            GeneralSettingsView(updater: updater)
                .tabItem {
                    Label("General", systemImage: "gear")
                }

            ProfileSettingsView()
                .tabItem {
                    Label("Profile", systemImage: "person")
                }
        }
        .frame(width: 450, height: 300)
    }
}

struct GeneralSettingsView: View {
    @AppStorage("serverURL") private var serverURL = "http://localhost:8000"
    private let updater: SPUUpdater

    init(updater: SPUUpdater) {
        self.updater = updater
    }

    var body: some View {
        Form {
            Section("Server") {
                TextField("Server URL", text: $serverURL)
                    .textFieldStyle(.roundedBorder)
                Text("The URL of your News Llama server")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Section("Updates") {
                Button("Check for Updates...") {
                    updater.checkForUpdates()
                }
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}

struct ProfileSettingsView: View {
    @Environment(AppViewModel.self) private var appViewModel
    @Environment(InterestViewModel.self) private var interestViewModel
    @State private var showDeleteConfirmation = false

    var body: some View {
        Form {
            if let user = appViewModel.selectedUser {
                Section("Current Profile") {
                    LabeledContent("Name", value: user.firstName)
                    LabeledContent("Interests", value: "\(user.interests.count)")
                    LabeledContent("Newsletters", value: "\(user.newsletterCount)")
                }

                Section {
                    Button("Delete Profile", role: .destructive) {
                        showDeleteConfirmation = true
                    }
                }
            } else {
                Text("No profile selected")
                    .foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .padding()
        .confirmationDialog(
            "Delete Profile?",
            isPresented: $showDeleteConfirmation,
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) {
                guard let userId = appViewModel.selectedUser?.id else { return }
                Task {
                    await appViewModel.deleteProfile(userId: userId)
                }
            }
        } message: {
            Text("This will permanently delete the profile, all interests, and all newsletters. This cannot be undone.")
        }
    }
}
