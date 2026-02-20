import SwiftUI

struct ProfileSelectionView: View {
    @Environment(AppViewModel.self) private var appViewModel
    @State private var showingCreateSheet = false

    private let columns = [
        GridItem(.adaptive(minimum: 140, maximum: 180), spacing: 16),
    ]

    var body: some View {
        VStack(spacing: 24) {
            // Header
            VStack(spacing: 8) {
                Image(systemName: "newspaper")
                    .font(.system(size: 48))
                    .foregroundStyle(.newsLlamaCoral)
                Text("News Llama")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                Text("Select a profile to get started")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            .padding(.top, 40)

            if appViewModel.isLoading {
                ProgressView()
                    .padding()
            } else {
                // Profile grid
                LazyVGrid(columns: columns, spacing: 16) {
                    ForEach(appViewModel.users) { user in
                        ProfileCard(user: user)
                            .onTapGesture {
                                appViewModel.selectUser(user)
                            }
                    }

                    // Add new profile card
                    Button {
                        showingCreateSheet = true
                    } label: {
                        VStack(spacing: 8) {
                            ZStack {
                                Circle()
                                    .fill(.gray.opacity(0.15))
                                    .frame(width: 64, height: 64)
                                Image(systemName: "plus")
                                    .font(.title2)
                                    .foregroundStyle(.secondary)
                            }
                            Text("New Profile")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(.background.opacity(0.5))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .strokeBorder(style: StrokeStyle(lineWidth: 1, dash: [6]))
                                .foregroundStyle(.secondary.opacity(0.3))
                        )
                    }
                    .buttonStyle(.plain)
                }
                .padding(.horizontal, 40)
            }

            Spacer()
        }
        .frame(minWidth: 500, minHeight: 400)
        .sheet(isPresented: $showingCreateSheet) {
            ProfileCreationView()
        }
    }
}
