import XCTest
@testable import News_Llama

@MainActor
final class InterestViewModelTests: XCTestCase {
    private var mockAPI: MockNewsLlamaAPI!
    private var viewModel: InterestViewModel!

    override func setUp() {
        super.setUp()
        mockAPI = MockNewsLlamaAPI()
        viewModel = InterestViewModel(api: mockAPI)
    }

    // MARK: - loadPredefinedInterests

    func testLoadPredefinedInterestsPopulatesGroups() async {
        mockAPI.predefinedInterestsToReturn = [
            InterestGroup(key: "tech", name: "Tech & Development", emoji: "🔧", interests: ["AI", "Rust"]),
            InterestGroup(key: "gaming", name: "Gaming", emoji: "🎮", interests: ["Minecraft"]),
        ]

        await viewModel.loadPredefinedInterests()

        XCTAssertEqual(viewModel.predefinedGroups.count, 2)
        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNil(viewModel.error)
    }

    func testLoadPredefinedInterestsErrorSetsError() async {
        mockAPI.shouldThrowError = true
        mockAPI.errorToThrow = NewsLlamaAPIError.networkError(NSError(domain: "test", code: -1))

        await viewModel.loadPredefinedInterests()

        XCTAssertTrue(viewModel.predefinedGroups.isEmpty)
        XCTAssertNotNil(viewModel.error)
    }

    // MARK: - addInterest

    func testAddInterestCallsAPI() async {
        await viewModel.addInterest(userId: 1, interestName: "Rust", isPredefined: true)

        XCTAssertTrue(mockAPI.addInterestCalled)
        XCTAssertEqual(mockAPI.addInterestName, "Rust")
        XCTAssertNil(viewModel.error)
    }

    func testAddInterestErrorSetsError() async {
        mockAPI.shouldThrowError = true
        mockAPI.errorToThrow = NewsLlamaAPIError.conflict("Already exists")

        await viewModel.addInterest(userId: 1, interestName: "Rust", isPredefined: true)

        XCTAssertNotNil(viewModel.error)
    }

    // MARK: - removeInterest

    func testRemoveInterestCallsAPI() async {
        await viewModel.removeInterest(userId: 1, interestName: "Rust")

        XCTAssertTrue(mockAPI.removeInterestCalled)
        XCTAssertEqual(mockAPI.removeInterestName, "Rust")
        XCTAssertNil(viewModel.error)
    }

    func testRemoveInterestErrorSetsError() async {
        mockAPI.shouldThrowError = true
        mockAPI.errorToThrow = NewsLlamaAPIError.notFound

        await viewModel.removeInterest(userId: 1, interestName: "Rust")

        XCTAssertNotNil(viewModel.error)
    }
}
