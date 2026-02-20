import XCTest
@testable import News_Llama

final class NewsLlamaAPITests: XCTestCase {

    // MARK: - Mock conforms to protocol

    func testMockConformsToProtocol() {
        let mock = MockNewsLlamaAPI()
        let _: any NewsLlamaAPIProtocol = mock
        XCTAssertEqual(mock.baseURL.absoluteString, "http://localhost:8000")
    }

    // MARK: - fetchUsers

    func testFetchUsersSuccess() async throws {
        let mock = MockNewsLlamaAPI()
        mock.usersToReturn = [
            User(
                id: 1, firstName: "Alice", avatarPath: nil,
                createdAt: "2025-10-20", interests: [], newsletterCount: 3
            ),
        ]

        let users = try await mock.fetchUsers()

        XCTAssertTrue(mock.fetchUsersCalled)
        XCTAssertEqual(users.count, 1)
        XCTAssertEqual(users[0].firstName, "Alice")
    }

    func testFetchUsersNetworkError() async {
        let mock = MockNewsLlamaAPI()
        mock.shouldThrowError = true
        mock.errorToThrow = NewsLlamaAPIError.networkError(
            NSError(domain: "test", code: -1)
        )

        do {
            _ = try await mock.fetchUsers()
            XCTFail("Expected error")
        } catch {
            XCTAssertTrue(mock.fetchUsersCalled)
        }
    }

    // MARK: - fetchNewsletters

    func testFetchNewslettersReturnsData() async throws {
        let mock = MockNewsLlamaAPI()
        mock.newslettersToReturn = [
            Newsletter(
                id: 1, userId: 1, date: "2025-10-15", guid: "abc-123",
                filePath: nil, status: .pending, generatedAt: nil, retryCount: 0
            ),
        ]

        let newsletters = try await mock.fetchNewsletters(userId: 1, year: 2025, month: 10)

        XCTAssertTrue(mock.fetchNewslettersCalled)
        XCTAssertEqual(newsletters.count, 1)
        XCTAssertEqual(newsletters[0].guid, "abc-123")
    }

    // MARK: - fetchNewsletterContent

    func testFetchNewsletterContentReturnsHTML() async throws {
        let mock = MockNewsLlamaAPI()
        mock.newsletterContentToReturn = NewsletterContentResponse(
            guid: "abc-123", date: "2025-10-15", status: "completed",
            generatedAt: "2025-10-15T06:00:00", retryCount: 0,
            htmlContent: "<html>Newsletter</html>"
        )

        let content = try await mock.fetchNewsletterContent(guid: "abc-123")

        XCTAssertEqual(mock.fetchNewsletterContentGuid, "abc-123")
        XCTAssertEqual(content.htmlContent, "<html>Newsletter</html>")
    }

    // MARK: - createProfile

    func testCreateProfileReturnsUserId() async throws {
        let mock = MockNewsLlamaAPI()
        mock.profileCreateToReturn = ProfileCreateResponse(
            status: "success", redirectUrl: "/calendar", userId: 42
        )

        let response = try await mock.createProfile(firstName: "Alice", interests: ["Rust"])

        XCTAssertTrue(mock.createProfileCalled)
        XCTAssertEqual(response.userId, 42)
    }

    // MARK: - generateNewsletter

    func testGenerateNewsletterReturnsPending() async throws {
        let mock = MockNewsLlamaAPI()
        mock.generatedNewsletterToReturn = Newsletter(
            id: 10, userId: 1, date: "2025-10-20", guid: "new-guid",
            filePath: nil, status: .pending, generatedAt: nil, retryCount: 0
        )

        let newsletter = try await mock.generateNewsletter(userId: 1, date: "2025-10-20")

        XCTAssertTrue(mock.generateNewsletterCalled)
        XCTAssertEqual(mock.generateNewsletterUserId, 1)
        XCTAssertEqual(newsletter.status, .pending)
    }

    // MARK: - Interest operations

    func testAddInterestSucceeds() async throws {
        let mock = MockNewsLlamaAPI()

        try await mock.addInterest(userId: 1, interestName: "Rust", isPredefined: true)

        XCTAssertTrue(mock.addInterestCalled)
        XCTAssertEqual(mock.addInterestName, "Rust")
    }

    func testRemoveInterestSucceeds() async throws {
        let mock = MockNewsLlamaAPI()

        try await mock.removeInterest(userId: 1, interestName: "Rust")

        XCTAssertTrue(mock.removeInterestCalled)
        XCTAssertEqual(mock.removeInterestName, "Rust")
    }

    // MARK: - deleteProfile

    func testDeleteProfileSucceeds() async throws {
        let mock = MockNewsLlamaAPI()

        try await mock.deleteProfile(userId: 5)

        XCTAssertTrue(mock.deleteProfileCalled)
        XCTAssertEqual(mock.deleteProfileUserId, 5)
    }

    // MARK: - retryNewsletter

    func testRetryNewsletterSucceeds() async throws {
        let mock = MockNewsLlamaAPI()

        try await mock.retryNewsletter(guid: "fail-guid")

        XCTAssertTrue(mock.retryNewsletterCalled)
        XCTAssertEqual(mock.retryNewsletterGuid, "fail-guid")
    }

    // MARK: - Error mapping

    func testNotFoundError() async {
        let mock = MockNewsLlamaAPI()
        mock.shouldThrowError = true
        mock.errorToThrow = NewsLlamaAPIError.notFound

        do {
            _ = try await mock.fetchUser(id: 9999)
            XCTFail("Expected notFound error")
        } catch let error as NewsLlamaAPIError {
            if case .notFound = error {
                // Expected
            } else {
                XCTFail("Expected notFound, got \(error)")
            }
        } catch {
            XCTFail("Unexpected error type")
        }
    }

    func testConflictError() async {
        let mock = MockNewsLlamaAPI()
        mock.shouldThrowError = true
        mock.errorToThrow = NewsLlamaAPIError.conflict("Already exists")

        do {
            _ = try await mock.createProfile(firstName: "Alice", interests: [])
            XCTFail("Expected conflict error")
        } catch let error as NewsLlamaAPIError {
            if case .conflict(let message) = error {
                XCTAssertEqual(message, "Already exists")
            } else {
                XCTFail("Expected conflict, got \(error)")
            }
        } catch {
            XCTFail("Unexpected error type")
        }
    }

    func testUnauthorizedError() async {
        let mock = MockNewsLlamaAPI()
        mock.shouldThrowError = true
        mock.errorToThrow = NewsLlamaAPIError.unauthorized

        do {
            try await mock.deleteProfile(userId: 1)
            XCTFail("Expected unauthorized error")
        } catch let error as NewsLlamaAPIError {
            if case .unauthorized = error {
                // Expected
            } else {
                XCTFail("Expected unauthorized, got \(error)")
            }
        } catch {
            XCTFail("Unexpected error type")
        }
    }
}
