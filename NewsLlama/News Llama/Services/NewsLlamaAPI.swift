import Foundation

final class NewsLlamaAPI: NewsLlamaAPIProtocol, @unchecked Sendable {
    let baseURL: URL
    private let session: URLSession
    var currentUserId: Int?

    init(baseURL: URL? = nil, session: URLSession = .shared) {
        let savedURL = UserDefaults.standard.string(forKey: "serverURL") ?? "http://localhost:8000"
        self.baseURL = baseURL ?? URL(string: savedURL)!
        self.session = session
    }

    // MARK: - Users

    func fetchUsers() async throws -> [User] {
        let response: UserListResponse = try await performRequest(
            path: "/api/v1/users/"
        )
        return response.users
    }

    func fetchUser(id: Int) async throws -> UserDetailResponse {
        return try await performRequest(path: "/api/v1/users/\(id)")
    }

    func createProfile(firstName: String, interests: [String]) async throws -> ProfileCreateResponse {
        let body: [String: Any] = [
            "first_name": firstName,
            "interests": interests,
        ]
        return try await performRequest(
            path: "/profile/create",
            method: "POST",
            jsonBody: body
        )
    }

    func deleteProfile(userId: Int) async throws {
        let _: EmptyResponse = try await performRequest(
            path: "/profile/\(userId)",
            method: "DELETE",
            requiresAuth: true
        )
    }

    // MARK: - Newsletters

    func fetchNewsletters(userId: Int, year: Int, month: Int) async throws -> [Newsletter] {
        let response: NewslettersResponse = try await performRequest(
            path: "/api/v1/users/\(userId)/newsletters?year=\(year)&month=\(month)"
        )
        return response.newsletters
    }

    func fetchNewsletterContent(guid: String) async throws -> NewsletterContentResponse {
        return try await performRequest(
            path: "/api/v1/newsletters/\(guid)/content"
        )
    }

    func generateNewsletter(userId: Int, date: String) async throws -> Newsletter {
        let body: [String: Any] = ["date": date]
        return try await performRequest(
            path: "/newsletters/generate",
            method: "POST",
            jsonBody: body,
            requiresAuth: true
        )
    }

    func retryNewsletter(guid: String) async throws {
        let _: EmptyResponse = try await performRequest(
            path: "/newsletters/\(guid)/retry",
            method: "POST",
            requiresAuth: true
        )
    }

    // MARK: - Interests

    func fetchPredefinedInterests() async throws -> [InterestGroup] {
        let response: PredefinedInterestsResponse = try await performRequest(
            path: "/api/v1/interests/predefined"
        )
        return response.groups
    }

    func addInterest(userId: Int, interestName: String, isPredefined: Bool) async throws {
        let body: [String: Any] = [
            "interest_name": interestName,
            "is_predefined": isPredefined,
        ]
        let _: EmptyResponse = try await performRequest(
            path: "/profile/settings/interests/add",
            method: "POST",
            jsonBody: body,
            requiresAuth: true
        )
    }

    func removeInterest(userId: Int, interestName: String) async throws {
        let body: [String: Any] = [
            "interest_name": interestName,
        ]
        let _: EmptyResponse = try await performRequest(
            path: "/profile/settings/interests/remove",
            method: "POST",
            jsonBody: body,
            requiresAuth: true
        )
    }

    // MARK: - Private helpers

    private func performRequest<T: Decodable>(
        path: String,
        method: String = "GET",
        jsonBody: [String: Any]? = nil,
        requiresAuth: Bool = false
    ) async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL) else {
            throw NewsLlamaAPIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method

        if let jsonBody {
            request.httpBody = try JSONSerialization.data(withJSONObject: jsonBody)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        if requiresAuth, let userId = currentUserId {
            request.setValue("user_id=\(userId)", forHTTPHeaderField: "Cookie")
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw NewsLlamaAPIError.networkError(error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NewsLlamaAPIError.unknown
        }

        switch httpResponse.statusCode {
        case 200..<300:
            break
        case 401:
            throw NewsLlamaAPIError.unauthorized
        case 404:
            throw NewsLlamaAPIError.notFound
        case 409:
            let detail = (try? JSONDecoder().decode(ErrorResponse.self, from: data))?.detail ?? "Conflict"
            throw NewsLlamaAPIError.conflict(detail)
        case 429:
            throw NewsLlamaAPIError.rateLimited
        default:
            let detail = (try? JSONDecoder().decode(ErrorResponse.self, from: data))?.detail ?? "Unknown error"
            throw NewsLlamaAPIError.serverError(httpResponse.statusCode, detail)
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw NewsLlamaAPIError.decodingError(error)
        }
    }
}

/// Used for endpoints that return non-JSON or where we discard the response body.
private struct EmptyResponse: Decodable {
    init(from decoder: Decoder) throws {
        // Accept any response body
    }
}
