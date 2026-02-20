import SwiftUI

struct CalendarDayView: View {
    let day: Int
    let newsletter: Newsletter?
    let isToday: Bool
    let isSelected: Bool

    var body: some View {
        VStack(spacing: 2) {
            Text("\(day)")
                .font(.system(size: 13, weight: isToday ? .bold : .regular))
                .foregroundStyle(isSelected ? .white : .primary)

            // Status indicator dot
            Circle()
                .fill(statusColor)
                .frame(width: 6, height: 6)
                .opacity(newsletter != nil ? 1 : 0)
        }
        .frame(maxWidth: .infinity)
        .frame(height: 36)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(isSelected ? Color.newsLlamaCoral : Color.clear)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .strokeBorder(isToday && !isSelected ? Color.newsLlamaCoral : Color.clear, lineWidth: 1.5)
        )
        .contentShape(Rectangle())
    }

    private var statusColor: Color {
        guard let newsletter else { return .clear }
        switch newsletter.status {
        case .completed:
            return isSelected ? .white : .green
        case .generating, .pending:
            return isSelected ? .white.opacity(0.8) : .orange
        case .failed:
            return isSelected ? .white.opacity(0.8) : .red
        }
    }
}
