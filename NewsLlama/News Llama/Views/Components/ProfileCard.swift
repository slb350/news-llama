import SwiftUI

struct ProfileCard: View {
    let user: User

    var body: some View {
        VStack(spacing: 8) {
            // Avatar circle
            ZStack {
                Circle()
                    .fill(.newsLlamaCoral.opacity(0.15))
                    .frame(width: 64, height: 64)

                if let avatarPath = user.avatarPath {
                    AsyncImage(url: URL(string: avatarPath)) { image in
                        image
                            .resizable()
                            .scaledToFill()
                    } placeholder: {
                        initialView
                    }
                    .frame(width: 64, height: 64)
                    .clipShape(Circle())
                } else {
                    initialView
                }
            }

            Text(user.firstName)
                .font(.subheadline)
                .fontWeight(.medium)
                .lineLimit(1)

            Text("\(user.newsletterCount) newsletters")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 16)
        .background(.background.opacity(0.5))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(.secondary.opacity(0.15))
        )
        .contentShape(Rectangle())
    }

    private var initialView: some View {
        Text(String(user.firstName.prefix(1)).uppercased())
            .font(.title2)
            .fontWeight(.semibold)
            .foregroundStyle(.newsLlamaCoral)
    }
}
