import SwiftUI

@Observable
@MainActor
final class NewsletterViewModel {
    var newsletters: [Newsletter] = []
    var selectedNewsletter: Newsletter?
    var selectedNewsletterContent: NewsletterContentResponse?
    var isLoading = false
    var isGenerating = false
    var error: Error?

    var currentYear: Int
    var currentMonth: Int

    private let api: any NewsLlamaAPIProtocol
    private var pollingTask: Task<Void, Never>?

    init(api: any NewsLlamaAPIProtocol = NewsLlamaAPI()) {
        self.api = api
        let today = Date()
        let calendar = Calendar.current
        self.currentYear = calendar.component(.year, from: today)
        self.currentMonth = calendar.component(.month, from: today)
    }

    // MARK: - Computed properties

    var currentMonthName: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMMM"
        var components = DateComponents()
        components.year = currentYear
        components.month = currentMonth
        components.day = 1
        guard let date = Calendar.current.date(from: components) else { return "" }
        return formatter.string(from: date)
    }

    var daysInMonth: Int {
        var components = DateComponents()
        components.year = currentYear
        components.month = currentMonth
        let calendar = Calendar.current
        guard let date = calendar.date(from: components),
              let range = calendar.range(of: .day, in: .month, for: date)
        else { return 30 }
        return range.count
    }

    var firstDayOfMonthWeekday: Int {
        var components = DateComponents()
        components.year = currentYear
        components.month = currentMonth
        components.day = 1
        let calendar = Calendar.current
        guard let date = calendar.date(from: components) else { return 1 }
        // Sunday = 1, Monday = 2, etc.
        return calendar.component(.weekday, from: date)
    }

    // MARK: - Navigation

    func nextMonth() {
        if currentMonth == 12 {
            currentMonth = 1
            currentYear += 1
        } else {
            currentMonth += 1
        }
    }

    func previousMonth() {
        if currentMonth == 1 {
            currentMonth = 12
            currentYear -= 1
        } else {
            currentMonth -= 1
        }
    }

    // MARK: - Data loading

    func loadNewsletters(userId: Int) async {
        isLoading = true
        error = nil
        do {
            newsletters = try await api.fetchNewsletters(
                userId: userId, year: currentYear, month: currentMonth
            )
        } catch {
            self.error = error
        }
        isLoading = false
    }

    func loadNewsletterContent(guid: String) async {
        isLoading = true
        error = nil
        do {
            selectedNewsletterContent = try await api.fetchNewsletterContent(guid: guid)
        } catch {
            self.error = error
        }
        isLoading = false
    }

    // MARK: - Actions

    func generateNewsletter(userId: Int, date: String) async {
        isGenerating = true
        error = nil
        do {
            let newsletter = try await api.generateNewsletter(userId: userId, date: date)
            await loadNewsletters(userId: userId)
            startPolling(guid: newsletter.guid, userId: userId)
        } catch {
            self.error = error
            isGenerating = false
        }
    }

    func retryNewsletter(guid: String, userId: Int) async {
        error = nil
        do {
            try await api.retryNewsletter(guid: guid)
            await loadNewsletters(userId: userId)
        } catch {
            self.error = error
        }
    }

    // MARK: - Calendar helpers

    func newsletterForDay(_ day: Int) -> Newsletter? {
        let dateString = String(format: "%04d-%02d-%02d", currentYear, currentMonth, day)
        return newsletters.first { $0.date == dateString }
    }

    func isToday(_ day: Int) -> Bool {
        let calendar = Calendar.current
        let today = Date()
        return calendar.component(.year, from: today) == currentYear
            && calendar.component(.month, from: today) == currentMonth
            && calendar.component(.day, from: today) == day
    }

    // MARK: - Polling

    func startPolling(guid: String, userId: Int) {
        pollingTask?.cancel()
        pollingTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(5))
                if Task.isCancelled { break }

                do {
                    let content = try await api.fetchNewsletterContent(guid: guid)
                    if content.status == "completed" || content.status == "failed" {
                        await loadNewsletters(userId: userId)
                        isGenerating = false
                        break
                    }
                } catch {
                    break
                }
            }
        }
    }

    func stopPolling() {
        pollingTask?.cancel()
        pollingTask = nil
    }
}
