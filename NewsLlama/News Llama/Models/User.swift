import Foundation

struct User: Codable, Identifiable, Hashable {
    let id: Int
    let firstName: String
    let avatarPath: String?
    let createdAt: String
    let interests: [InterestBrief]
    let newsletterCount: Int

    enum CodingKeys: String, CodingKey {
        case id
        case firstName = "first_name"
        case avatarPath = "avatar_path"
        case createdAt = "created_at"
        case interests
        case newsletterCount = "newsletter_count"
    }
}

struct UserListResponse: Codable {
    let users: [User]
    let count: Int
}

struct UserDetailResponse: Codable, Identifiable, Hashable {
    let id: Int
    let firstName: String
    let avatarPath: String?
    let createdAt: String
    let interests: [InterestFull]
    let newsletterCount: Int

    enum CodingKeys: String, CodingKey {
        case id
        case firstName = "first_name"
        case avatarPath = "avatar_path"
        case createdAt = "created_at"
        case interests
        case newsletterCount = "newsletter_count"
    }
}
