import SwiftUI

struct SidebarView: View {
    @Environment(AppViewModel.self) private var appViewModel
    @Environment(NewsletterViewModel.self) private var newsletterViewModel

    private let weekdays = ["S", "M", "T", "W", "T", "F", "S"]
    private let calendarColumns = Array(repeating: GridItem(.flexible(), spacing: 4), count: 7)

    var body: some View {
        VStack(spacing: 16) {
            // Month navigation
            HStack {
                Button {
                    newsletterViewModel.previousMonth()
                    reloadNewsletters()
                } label: {
                    Image(systemName: "chevron.left")
                }
                .buttonStyle(.plain)

                Spacer()

                Text("\(newsletterViewModel.currentMonthName) \(String(newsletterViewModel.currentYear))")
                    .font(.headline)

                Spacer()

                Button {
                    newsletterViewModel.nextMonth()
                    reloadNewsletters()
                } label: {
                    Image(systemName: "chevron.right")
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal)

            // Weekday header
            LazyVGrid(columns: calendarColumns, spacing: 4) {
                ForEach(weekdays, id: \.self) { day in
                    Text(day)
                        .font(.caption)
                        .fontWeight(.medium)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity)
                }
            }
            .padding(.horizontal)

            // Calendar grid
            LazyVGrid(columns: calendarColumns, spacing: 4) {
                // Leading empty cells
                let offset = newsletterViewModel.firstDayOfMonthWeekday - 1
                ForEach(0..<offset, id: \.self) { _ in
                    Color.clear
                        .frame(height: 36)
                }

                // Day cells
                ForEach(1...newsletterViewModel.daysInMonth, id: \.self) { day in
                    CalendarDayView(
                        day: day,
                        newsletter: newsletterViewModel.newsletterForDay(day),
                        isToday: newsletterViewModel.isToday(day),
                        isSelected: isSelected(day: day)
                    )
                    .onTapGesture {
                        if let newsletter = newsletterViewModel.newsletterForDay(day) {
                            newsletterViewModel.selectedNewsletter = newsletter
                            Task {
                                await newsletterViewModel.loadNewsletterContent(guid: newsletter.guid)
                            }
                        }
                    }
                }
            }
            .padding(.horizontal)

            Divider()

            // Generate button
            if let userId = appViewModel.selectedUser?.id {
                Button {
                    let today = todayDateString()
                    Task {
                        await newsletterViewModel.generateNewsletter(userId: userId, date: today)
                    }
                } label: {
                    HStack {
                        if newsletterViewModel.isGenerating {
                            ProgressView()
                                .controlSize(.small)
                            Text("Generating...")
                        } else {
                            Image(systemName: "newspaper")
                            Text("Generate Today's Newsletter")
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                }
                .buttonStyle(.borderedProminent)
                .tint(.newsLlamaCoral)
                .disabled(newsletterViewModel.isGenerating)
                .padding(.horizontal)
                .keyboardShortcut("g")
            }

            Spacer()
        }
        .padding(.top, 12)
    }

    private func isSelected(day: Int) -> Bool {
        guard let selected = newsletterViewModel.selectedNewsletter else { return false }
        let dateString = String(format: "%04d-%02d-%02d", newsletterViewModel.currentYear, newsletterViewModel.currentMonth, day)
        return selected.date == dateString
    }

    private func reloadNewsletters() {
        guard let userId = appViewModel.selectedUser?.id else { return }
        Task {
            await newsletterViewModel.loadNewsletters(userId: userId)
        }
    }

    private func todayDateString() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: Date())
    }
}
