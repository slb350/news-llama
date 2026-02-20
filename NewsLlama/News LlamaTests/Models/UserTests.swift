import XCTest
@testable import News_Llama

final class UserTests: XCTestCase {
    func testUserDecodesFromJSON() throws {
        let json = """
        {
            "id": 1,
            "first_name": "Alice",
            "avatar_path": "/static/avatars/alice.png",
            "created_at": "2025-10-20T10:00:00",
            "interests": [
                {"id": 1, "interest_name": "AI & Machine Learning", "is_predefined": true}
            ],
            "newsletter_count": 5
        }
        """.data(using: .utf8)!

        let user = try JSONDecoder().decode(User.self, from: json)

        XCTAssertEqual(user.id, 1)
        XCTAssertEqual(user.firstName, "Alice")
        XCTAssertEqual(user.avatarPath, "/static/avatars/alice.png")
        XCTAssertEqual(user.createdAt, "2025-10-20T10:00:00")
        XCTAssertEqual(user.interests.count, 1)
        XCTAssertEqual(user.interests[0].interestName, "AI & Machine Learning")
        XCTAssertEqual(user.newsletterCount, 5)
    }

    func testUserDecodesNullAvatarPath() throws {
        let json = """
        {
            "id": 2,
            "first_name": "Bob",
            "avatar_path": null,
            "created_at": "2025-10-20T10:00:00",
            "interests": [],
            "newsletter_count": 0
        }
        """.data(using: .utf8)!

        let user = try JSONDecoder().decode(User.self, from: json)

        XCTAssertEqual(user.id, 2)
        XCTAssertEqual(user.firstName, "Bob")
        XCTAssertNil(user.avatarPath)
        XCTAssertEqual(user.interests.count, 0)
    }

    func testUserListResponseDecodes() throws {
        let json = """
        {
            "users": [
                {
                    "id": 1,
                    "first_name": "Alice",
                    "avatar_path": null,
                    "created_at": "2025-10-20T10:00:00",
                    "interests": [],
                    "newsletter_count": 3
                },
                {
                    "id": 2,
                    "first_name": "Bob",
                    "avatar_path": null,
                    "created_at": "2025-10-21T10:00:00",
                    "interests": [],
                    "newsletter_count": 0
                }
            ],
            "count": 2
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder().decode(UserListResponse.self, from: json)

        XCTAssertEqual(response.count, 2)
        XCTAssertEqual(response.users.count, 2)
        XCTAssertEqual(response.users[0].firstName, "Alice")
        XCTAssertEqual(response.users[1].firstName, "Bob")
    }

    func testUserDetailResponseDecodesWithFullInterests() throws {
        let json = """
        {
            "id": 1,
            "first_name": "Alice",
            "avatar_path": null,
            "created_at": "2025-10-20T10:00:00",
            "interests": [
                {
                    "id": 10,
                    "user_id": 1,
                    "interest_name": "Rust",
                    "is_predefined": true,
                    "added_at": "2025-10-20T10:05:00"
                }
            ],
            "newsletter_count": 5
        }
        """.data(using: .utf8)!

        let detail = try JSONDecoder().decode(UserDetailResponse.self, from: json)

        XCTAssertEqual(detail.id, 1)
        XCTAssertEqual(detail.interests.count, 1)
        XCTAssertEqual(detail.interests[0].userId, 1)
        XCTAssertEqual(detail.interests[0].interestName, "Rust")
        XCTAssertEqual(detail.interests[0].addedAt, "2025-10-20T10:05:00")
    }
}
