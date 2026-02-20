import SwiftUI

struct NewsletterDetailView: View {
    @Environment(NewsletterViewModel.self) private var newsletterViewModel
    @Environment(AppViewModel.self) private var appViewModel

    var body: some View {
        Group {
            if let content = newsletterViewModel.selectedNewsletterContent {
                switch content.status {
                case "completed":
                    if let html = content.htmlContent {
                        NewsletterWebView(
                            htmlContent: html,
                            baseURL: (appViewModel.selectedUser != nil)
                                ? URL(string: UserDefaults.standard.string(forKey: "serverURL") ?? "http://localhost:8000")
                                : nil
                        )
                    } else {
                        ContentUnavailableView(
                            "Newsletter File Missing",
                            systemImage: "doc.questionmark",
                            description: Text("The newsletter was generated but the file could not be found.")
                        )
                    }

                case "pending", "generating":
                    VStack(spacing: 16) {
                        ProgressView()
                            .controlSize(.large)
                        Text("Generating newsletter...")
                            .font(.title3)
                            .foregroundStyle(.secondary)
                        Text("This may take 10-15 minutes")
                            .font(.caption)
                            .foregroundStyle(.tertiary)
                    }

                case "failed":
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.system(size: 48))
                            .foregroundStyle(.orange)
                        Text("Newsletter generation failed")
                            .font(.title3)

                        if content.retryCount < 3 {
                            Button("Retry") {
                                guard let userId = appViewModel.selectedUser?.id else { return }
                                Task {
                                    await newsletterViewModel.retryNewsletter(
                                        guid: content.guid, userId: userId
                                    )
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(.newsLlamaCoral)
                        } else {
                            Text("Maximum retries reached")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }

                default:
                    ContentUnavailableView(
                        "Unknown Status",
                        systemImage: "questionmark.circle",
                        description: Text("Newsletter status: \(content.status)")
                    )
                }
            } else if newsletterViewModel.isLoading {
                ProgressView()
            } else {
                ContentUnavailableView(
                    "Select a Newsletter",
                    systemImage: "newspaper",
                    description: Text("Choose a day from the calendar to view its newsletter")
                )
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
