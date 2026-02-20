import Foundation
@testable import News_Llama

final class MockNewsLlamaAPI: NewsLlamaAPIProtocol, @unchecked Sendable {
    let baseURL: URL = URL(string: "http://localhost:8000")!

    // Configurable return values
    var usersToReturn: [User] = []
    var userDetailToReturn: UserDetailResponse?
    var profileCreateToReturn: ProfileCreateResponse?
    var newslettersToReturn: [Newsletter] = []
    var newsletterContentToReturn: NewsletterContentResponse?
    var generatedNewsletterToReturn: Newsletter?
    var predefinedInterestsToReturn: [InterestGroup] = []

    // Error control
    var shouldThrowError = false
    var errorToThrow: Error = NewsLlamaAPIError.unknown

    // Call tracking
    var fetchUsersCalled = false
    var fetchUserIdCalled: Int?
    var createProfileCalled = false
    var deleteProfileCalled = false
    var deleteProfileUserId: Int?
    var fetchNewslettersCalled = false
    var fetchNewsletterContentGuid: String?
    var generateNewsletterCalled = false
    var generateNewsletterUserId: Int?
    var retryNewsletterCalled = false
    var retryNewsletterGuid: String?
    var fetchPredefinedInterestsCalled = false
    var addInterestCalled = false
    var addInterestName: String?
    var removeInterestCalled = false
    var removeInterestName: String?

    func fetchUsers() async throws -> [User] {
        fetchUsersCalled = true
        if shouldThrowError { throw errorToThrow }
        return usersToReturn
    }

    func fetchUser(id: Int) async throws -> UserDetailResponse {
        fetchUserIdCalled = id
        if shouldThrowError { throw errorToThrow }
        guard let detail = userDetailToReturn else {
            throw NewsLlamaAPIError.notFound
        }
        return detail
    }

    func createProfile(firstName: String, interests: [String]) async throws -> ProfileCreateResponse {
        createProfileCalled = true
        if shouldThrowError { throw errorToThrow }
        guard let response = profileCreateToReturn else {
            throw NewsLlamaAPIError.unknown
        }
        return response
    }

    func deleteProfile(userId: Int) async throws {
        deleteProfileCalled = true
        deleteProfileUserId = userId
        if shouldThrowError { throw errorToThrow }
    }

    func fetchNewsletters(userId: Int, year: Int, month: Int) async throws -> [Newsletter] {
        fetchNewslettersCalled = true
        if shouldThrowError { throw errorToThrow }
        return newslettersToReturn
    }

    func fetchNewsletterContent(guid: String) async throws -> NewsletterContentResponse {
        fetchNewsletterContentGuid = guid
        if shouldThrowError { throw errorToThrow }
        guard let content = newsletterContentToReturn else {
            throw NewsLlamaAPIError.notFound
        }
        return content
    }

    func generateNewsletter(userId: Int, date: String) async throws -> Newsletter {
        generateNewsletterCalled = true
        generateNewsletterUserId = userId
        if shouldThrowError { throw errorToThrow }
        guard let newsletter = generatedNewsletterToReturn else {
            throw NewsLlamaAPIError.unknown
        }
        return newsletter
    }

    func retryNewsletter(guid: String) async throws {
        retryNewsletterCalled = true
        retryNewsletterGuid = guid
        if shouldThrowError { throw errorToThrow }
    }

    func fetchPredefinedInterests() async throws -> [InterestGroup] {
        fetchPredefinedInterestsCalled = true
        if shouldThrowError { throw errorToThrow }
        return predefinedInterestsToReturn
    }

    func addInterest(userId: Int, interestName: String, isPredefined: Bool) async throws {
        addInterestCalled = true
        addInterestName = interestName
        if shouldThrowError { throw errorToThrow }
    }

    func removeInterest(userId: Int, interestName: String) async throws {
        removeInterestCalled = true
        removeInterestName = interestName
        if shouldThrowError { throw errorToThrow }
    }
}
