import XCTest
@testable import News_Llama

@MainActor
final class NewsletterViewModelTests: XCTestCase {
    private var mockAPI: MockNewsLlamaAPI!
    private var viewModel: NewsletterViewModel!

    override func setUp() {
        super.setUp()
        mockAPI = MockNewsLlamaAPI()
        viewModel = NewsletterViewModel(api: mockAPI)
    }

    // MARK: - loadNewsletters

    func testLoadNewslettersPopulatesData() async {
        mockAPI.newslettersToReturn = [
            Newsletter(id: 1, userId: 1, date: "2025-10-15", guid: "abc", filePath: nil, status: .pending, generatedAt: nil, retryCount: 0),
            Newsletter(id: 2, userId: 1, date: "2025-10-20", guid: "def", filePath: nil, status: .completed, generatedAt: "2025-10-20T06:00:00", retryCount: 0),
        ]

        await viewModel.loadNewsletters(userId: 1)

        XCTAssertEqual(viewModel.newsletters.count, 2)
        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNil(viewModel.error)
    }

    func testLoadNewslettersUsesCurrentYearMonth() async {
        let calendar = Calendar.current
        let today = Date()
        XCTAssertEqual(viewModel.currentYear, calendar.component(.year, from: today))
        XCTAssertEqual(viewModel.currentMonth, calendar.component(.month, from: today))
    }

    // MARK: - Month navigation

    func testNextMonthIncrementsMonth() {
        viewModel.currentYear = 2025
        viewModel.currentMonth = 10

        viewModel.nextMonth()

        XCTAssertEqual(viewModel.currentYear, 2025)
        XCTAssertEqual(viewModel.currentMonth, 11)
    }

    func testNextMonthRollsOverYear() {
        viewModel.currentYear = 2025
        viewModel.currentMonth = 12

        viewModel.nextMonth()

        XCTAssertEqual(viewModel.currentYear, 2026)
        XCTAssertEqual(viewModel.currentMonth, 1)
    }

    func testPreviousMonthDecrementsMonth() {
        viewModel.currentYear = 2025
        viewModel.currentMonth = 10

        viewModel.previousMonth()

        XCTAssertEqual(viewModel.currentYear, 2025)
        XCTAssertEqual(viewModel.currentMonth, 9)
    }

    func testPreviousMonthRollsBackYear() {
        viewModel.currentYear = 2025
        viewModel.currentMonth = 1

        viewModel.previousMonth()

        XCTAssertEqual(viewModel.currentYear, 2024)
        XCTAssertEqual(viewModel.currentMonth, 12)
    }

    // MARK: - loadNewsletterContent

    func testLoadNewsletterContentPopulates() async {
        mockAPI.newsletterContentToReturn = NewsletterContentResponse(
            guid: "abc", date: "2025-10-15", status: "completed",
            generatedAt: "2025-10-15T06:00:00", retryCount: 0,
            htmlContent: "<html>Content</html>"
        )

        await viewModel.loadNewsletterContent(guid: "abc")

        XCTAssertEqual(viewModel.selectedNewsletterContent?.htmlContent, "<html>Content</html>")
        XCTAssertFalse(viewModel.isLoading)
    }

    // MARK: - generateNewsletter

    func testGenerateNewsletterCallsAPIAndRefreshes() async {
        mockAPI.generatedNewsletterToReturn = Newsletter(
            id: 10, userId: 1, date: "2025-10-20", guid: "new-guid",
            filePath: nil, status: .pending, generatedAt: nil, retryCount: 0
        )
        // Stop polling immediately for test
        mockAPI.newsletterContentToReturn = NewsletterContentResponse(
            guid: "new-guid", date: "2025-10-20", status: "completed",
            generatedAt: nil, retryCount: 0, htmlContent: nil
        )

        await viewModel.generateNewsletter(userId: 1, date: "2025-10-20")

        XCTAssertTrue(mockAPI.generateNewsletterCalled)
        XCTAssertTrue(mockAPI.fetchNewslettersCalled)
    }

    // MARK: - newsletterForDay

    func testNewsletterForDayReturnsCorrectNewsletter() {
        viewModel.currentYear = 2025
        viewModel.currentMonth = 10
        viewModel.newsletters = [
            Newsletter(id: 1, userId: 1, date: "2025-10-15", guid: "abc", filePath: nil, status: .completed, generatedAt: nil, retryCount: 0),
        ]

        let found = viewModel.newsletterForDay(15)
        let notFound = viewModel.newsletterForDay(16)

        XCTAssertEqual(found?.guid, "abc")
        XCTAssertNil(notFound)
    }

    // MARK: - isToday

    func testIsTodayIdentifiesCurrentDay() {
        let calendar = Calendar.current
        let today = Date()
        viewModel.currentYear = calendar.component(.year, from: today)
        viewModel.currentMonth = calendar.component(.month, from: today)
        let day = calendar.component(.day, from: today)

        XCTAssertTrue(viewModel.isToday(day))
        XCTAssertFalse(viewModel.isToday(day == 1 ? 2 : 1))
    }

    // MARK: - Calendar computed properties

    func testDaysInMonthOctober() {
        viewModel.currentYear = 2025
        viewModel.currentMonth = 10

        XCTAssertEqual(viewModel.daysInMonth, 31)
    }

    func testDaysInMonthFebruaryLeapYear() {
        viewModel.currentYear = 2024
        viewModel.currentMonth = 2

        XCTAssertEqual(viewModel.daysInMonth, 29)
    }

    func testDaysInMonthFebruaryNonLeapYear() {
        viewModel.currentYear = 2025
        viewModel.currentMonth = 2

        XCTAssertEqual(viewModel.daysInMonth, 28)
    }

    func testCurrentMonthNameOctober() {
        viewModel.currentYear = 2025
        viewModel.currentMonth = 10

        XCTAssertEqual(viewModel.currentMonthName, "October")
    }

    func testFirstDayOfMonthWeekday() {
        // October 1, 2025 is a Wednesday (weekday = 4)
        viewModel.currentYear = 2025
        viewModel.currentMonth = 10

        XCTAssertEqual(viewModel.firstDayOfMonthWeekday, 4)
    }
}
