import Foundation

protocol NewsLlamaAPIProtocol: Sendable {
    var baseURL: URL { get }

    func fetchUsers() async throws -> [User]
    func fetchUser(id: Int) async throws -> UserDetailResponse
    func createProfile(firstName: String, interests: [String]) async throws -> ProfileCreateResponse
    func deleteProfile(userId: Int) async throws
    func fetchNewsletters(userId: Int, year: Int, month: Int) async throws -> [Newsletter]
    func fetchNewsletterContent(guid: String) async throws -> NewsletterContentResponse
    func generateNewsletter(userId: Int, date: String) async throws -> Newsletter
    func retryNewsletter(guid: String) async throws
    func fetchPredefinedInterests() async throws -> [InterestGroup]
    func addInterest(userId: Int, interestName: String, isPredefined: Bool) async throws
    func removeInterest(userId: Int, interestName: String) async throws
}

enum NewsLlamaAPIError: Error, LocalizedError {
    case invalidURL
    case networkError(Error)
    case decodingError(Error)
    case serverError(Int, String)
    case notFound
    case conflict(String)
    case rateLimited
    case unauthorized
    case unknown

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid server URL"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .serverError(let code, let message):
            return "Server error (\(code)): \(message)"
        case .notFound:
            return "Resource not found"
        case .conflict(let message):
            return "Conflict: \(message)"
        case .rateLimited:
            return "Too many requests. Please wait."
        case .unauthorized:
            return "Not authorized. Please select a profile."
        case .unknown:
            return "An unknown error occurred"
        }
    }
}
