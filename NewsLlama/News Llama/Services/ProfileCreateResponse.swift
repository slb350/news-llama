import Foundation

struct ProfileCreateResponse: Codable {
    let status: String
    let redirectUrl: String
    let userId: Int

    enum CodingKeys: String, CodingKey {
        case status
        case redirectUrl = "redirect_url"
        case userId = "user_id"
    }
}

struct ErrorResponse: Codable {
    let detail: String
}
