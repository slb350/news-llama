import XCTest
@testable import News_Llama

final class InterestTests: XCTestCase {
    func testInterestBriefDecodes() throws {
        let json = """
        {
            "id": 1,
            "interest_name": "AI & Machine Learning",
            "is_predefined": true
        }
        """.data(using: .utf8)!

        let interest = try JSONDecoder().decode(InterestBrief.self, from: json)

        XCTAssertEqual(interest.id, 1)
        XCTAssertEqual(interest.interestName, "AI & Machine Learning")
        XCTAssertTrue(interest.isPredefined)
    }

    func testInterestFullDecodes() throws {
        let json = """
        {
            "id": 10,
            "user_id": 1,
            "interest_name": "Rust",
            "is_predefined": true,
            "added_at": "2025-10-20T10:05:00"
        }
        """.data(using: .utf8)!

        let interest = try JSONDecoder().decode(InterestFull.self, from: json)

        XCTAssertEqual(interest.id, 10)
        XCTAssertEqual(interest.userId, 1)
        XCTAssertEqual(interest.interestName, "Rust")
        XCTAssertTrue(interest.isPredefined)
        XCTAssertEqual(interest.addedAt, "2025-10-20T10:05:00")
    }

    func testInterestGroupDecodes() throws {
        let json = """
        {
            "key": "tech",
            "name": "Tech & Development",
            "emoji": "🔧",
            "interests": ["AI & Machine Learning", "Rust", "Python"]
        }
        """.data(using: .utf8)!

        let group = try JSONDecoder().decode(InterestGroup.self, from: json)

        XCTAssertEqual(group.key, "tech")
        XCTAssertEqual(group.name, "Tech & Development")
        XCTAssertEqual(group.emoji, "🔧")
        XCTAssertEqual(group.interests.count, 3)
        XCTAssertEqual(group.id, "tech")
    }

    func testPredefinedInterestsResponseDecodes() throws {
        let json = """
        {
            "groups": [
                {
                    "key": "tech",
                    "name": "Tech & Development",
                    "emoji": "🔧",
                    "interests": ["AI & Machine Learning", "Rust"]
                },
                {
                    "key": "gaming",
                    "name": "Gaming",
                    "emoji": "🎮",
                    "interests": ["Minecraft", "Roblox"]
                }
            ]
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder().decode(PredefinedInterestsResponse.self, from: json)

        XCTAssertEqual(response.groups.count, 2)
        XCTAssertEqual(response.groups[0].key, "tech")
        XCTAssertEqual(response.groups[1].key, "gaming")
    }

    func testInterestSearchResponseDecodes() throws {
        let json = """
        {
            "results": ["Python", "Raspberry Pi"],
            "count": 2
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder().decode(InterestSearchResponse.self, from: json)

        XCTAssertEqual(response.count, 2)
        XCTAssertEqual(response.results, ["Python", "Raspberry Pi"])
    }

    func testPredefinedInterestsFlatResponseDecodes() throws {
        let json = """
        {
            "interests": ["AI & Machine Learning", "Coffee & Tea Culture", "Python"]
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder().decode(PredefinedInterestsFlatResponse.self, from: json)

        XCTAssertEqual(response.interests.count, 3)
    }
}
