import Foundation

enum NewsletterStatus: String, Codable {
    case pending
    case generating
    case completed
    case failed
}

struct Newsletter: Codable, Identifiable, Hashable {
    let id: Int
    let userId: Int
    let date: String
    let guid: String
    let filePath: String?
    let status: NewsletterStatus
    let generatedAt: String?
    let retryCount: Int

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case date
        case guid
        case filePath = "file_path"
        case status
        case generatedAt = "generated_at"
        case retryCount = "retry_count"
    }
}

struct NewslettersResponse: Codable {
    let newsletters: [Newsletter]
    let year: Int
    let month: Int
    let count: Int
}

struct NewsletterContentResponse: Codable {
    let guid: String
    let date: String
    let status: String
    let generatedAt: String?
    let retryCount: Int
    let htmlContent: String?

    enum CodingKeys: String, CodingKey {
        case guid
        case date
        case status
        case generatedAt = "generated_at"
        case retryCount = "retry_count"
        case htmlContent = "html_content"
    }
}
