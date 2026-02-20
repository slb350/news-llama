import XCTest
@testable import News_Llama

@MainActor
final class AppViewModelTests: XCTestCase {
    private var mockAPI: MockNewsLlamaAPI!
    private var viewModel: AppViewModel!

    override func setUp() {
        super.setUp()
        mockAPI = MockNewsLlamaAPI()
        viewModel = AppViewModel(api: mockAPI)
    }

    // MARK: - loadUsers

    func testLoadUsersPopulatesUsers() async {
        mockAPI.usersToReturn = [
            User(id: 1, firstName: "Alice", avatarPath: nil, createdAt: "2025-10-20", interests: [], newsletterCount: 3),
            User(id: 2, firstName: "Bob", avatarPath: nil, createdAt: "2025-10-21", interests: [], newsletterCount: 0),
        ]

        await viewModel.loadUsers()

        XCTAssertEqual(viewModel.users.count, 2)
        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNil(viewModel.error)
    }

    func testLoadUsersErrorSetsError() async {
        mockAPI.shouldThrowError = true
        mockAPI.errorToThrow = NewsLlamaAPIError.networkError(NSError(domain: "test", code: -1))

        await viewModel.loadUsers()

        XCTAssertTrue(viewModel.users.isEmpty)
        XCTAssertNotNil(viewModel.error)
        XCTAssertFalse(viewModel.isLoading)
    }

    // MARK: - selectUser

    func testSelectUserSetsSelectedUser() {
        let user = User(id: 1, firstName: "Alice", avatarPath: nil, createdAt: "2025-10-20", interests: [], newsletterCount: 0)

        viewModel.selectUser(user)

        XCTAssertEqual(viewModel.selectedUser?.id, 1)
    }

    // MARK: - logout

    func testLogoutClearsSelectedUser() {
        let user = User(id: 1, firstName: "Alice", avatarPath: nil, createdAt: "2025-10-20", interests: [], newsletterCount: 0)
        viewModel.selectUser(user)

        viewModel.logout()

        XCTAssertNil(viewModel.selectedUser)
    }

    // MARK: - createProfile

    func testCreateProfileCallsAPIAndReloadsUsers() async {
        mockAPI.profileCreateToReturn = ProfileCreateResponse(
            status: "success", redirectUrl: "/calendar", userId: 42
        )
        mockAPI.usersToReturn = [
            User(id: 42, firstName: "NewUser", avatarPath: nil, createdAt: "2025-10-20", interests: [], newsletterCount: 0),
        ]

        await viewModel.createProfile(firstName: "NewUser", interests: ["Rust"])

        XCTAssertTrue(mockAPI.createProfileCalled)
        XCTAssertTrue(mockAPI.fetchUsersCalled)
        XCTAssertEqual(viewModel.selectedUser?.id, 42)
    }

    // MARK: - deleteProfile

    func testDeleteProfileClearsIfSelected() async {
        let user = User(id: 5, firstName: "Alice", avatarPath: nil, createdAt: "2025-10-20", interests: [], newsletterCount: 0)
        viewModel.selectUser(user)
        mockAPI.usersToReturn = []

        await viewModel.deleteProfile(userId: 5)

        XCTAssertTrue(mockAPI.deleteProfileCalled)
        XCTAssertNil(viewModel.selectedUser)
    }

    func testDeleteProfileKeepsOtherUserSelected() async {
        let alice = User(id: 1, firstName: "Alice", avatarPath: nil, createdAt: "2025-10-20", interests: [], newsletterCount: 0)
        viewModel.selectUser(alice)
        mockAPI.usersToReturn = [alice]

        await viewModel.deleteProfile(userId: 5)

        XCTAssertTrue(mockAPI.deleteProfileCalled)
        XCTAssertEqual(viewModel.selectedUser?.id, 1)
    }
}
