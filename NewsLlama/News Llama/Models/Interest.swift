import Foundation

struct InterestBrief: Codable, Identifiable, Hashable {
    let id: Int
    let interestName: String
    let isPredefined: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case interestName = "interest_name"
        case isPredefined = "is_predefined"
    }
}

struct InterestFull: Codable, Identifiable, Hashable {
    let id: Int
    let userId: Int
    let interestName: String
    let isPredefined: Bool
    let addedAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case interestName = "interest_name"
        case isPredefined = "is_predefined"
        case addedAt = "added_at"
    }
}

struct InterestGroup: Codable, Identifiable {
    let key: String
    let name: String
    let emoji: String
    let interests: [String]

    var id: String { key }
}

struct PredefinedInterestsResponse: Codable {
    let groups: [InterestGroup]
}

struct PredefinedInterestsFlatResponse: Codable {
    let interests: [String]
}

struct InterestSearchResponse: Codable {
    let results: [String]
    let count: Int
}
