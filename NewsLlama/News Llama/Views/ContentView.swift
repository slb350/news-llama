import SwiftUI

struct ContentView: View {
    @Environment(AppViewModel.self) private var appViewModel
    @Environment(NewsletterViewModel.self) private var newsletterViewModel
    @Environment(InterestViewModel.self) private var interestViewModel

    var body: some View {
        Group {
            if appViewModel.selectedUser != nil {
                MainView()
            } else {
                ProfileSelectionView()
            }
        }
        .task {
            await appViewModel.loadUsers()
        }
    }
}
