import SwiftUI

struct MainView: View {
    @Environment(AppViewModel.self) private var appViewModel
    @Environment(NewsletterViewModel.self) private var newsletterViewModel

    var body: some View {
        NavigationSplitView {
            SidebarView()
                .navigationSplitViewColumnWidth(min: 280, ideal: 300, max: 350)
        } detail: {
            NewsletterDetailView()
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Menu {
                    if let user = appViewModel.selectedUser {
                        Text(user.firstName)
                            .font(.headline)
                        Divider()
                    }
                    Button("Switch Profile") {
                        appViewModel.logout()
                    }
                    Divider()
                    SettingsLink {
                        Text("Settings...")
                    }
                } label: {
                    Label(
                        appViewModel.selectedUser?.firstName ?? "Profile",
                        systemImage: "person.circle"
                    )
                }
            }
            ToolbarItem(placement: .automatic) {
                Button {
                    guard let userId = appViewModel.selectedUser?.id else { return }
                    Task {
                        await newsletterViewModel.loadNewsletters(userId: userId)
                    }
                } label: {
                    Label("Refresh", systemImage: "arrow.clockwise")
                }
                .keyboardShortcut("r")
            }
        }
        .frame(minWidth: 900, minHeight: 600)
        .task {
            guard let userId = appViewModel.selectedUser?.id else { return }
            await newsletterViewModel.loadNewsletters(userId: userId)
        }
    }
}
