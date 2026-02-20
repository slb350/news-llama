import XCTest
@testable import News_Llama

final class NewsletterTests: XCTestCase {
    func testNewsletterDecodesAllStatusValues() throws {
        let statuses = ["pending", "generating", "completed", "failed"]
        for status in statuses {
            let json = """
            {
                "id": 1,
                "user_id": 1,
                "date": "2025-10-15",
                "guid": "abc-123",
                "file_path": null,
                "status": "\(status)",
                "generated_at": null,
                "retry_count": 0
            }
            """.data(using: .utf8)!

            let newsletter = try JSONDecoder().decode(Newsletter.self, from: json)
            XCTAssertEqual(newsletter.status.rawValue, status)
        }
    }

    func testNewsletterStatusEnumRawValues() {
        XCTAssertEqual(NewsletterStatus.pending.rawValue, "pending")
        XCTAssertEqual(NewsletterStatus.generating.rawValue, "generating")
        XCTAssertEqual(NewsletterStatus.completed.rawValue, "completed")
        XCTAssertEqual(NewsletterStatus.failed.rawValue, "failed")
    }

    func testNewsletterDecodesCompletedWithFilePath() throws {
        let json = """
        {
            "id": 5,
            "user_id": 1,
            "date": "2025-10-20",
            "guid": "def-456",
            "file_path": "output/news-2025-10-20.html",
            "status": "completed",
            "generated_at": "2025-10-20T06:15:00",
            "retry_count": 0
        }
        """.data(using: .utf8)!

        let newsletter = try JSONDecoder().decode(Newsletter.self, from: json)

        XCTAssertEqual(newsletter.id, 5)
        XCTAssertEqual(newsletter.userId, 1)
        XCTAssertEqual(newsletter.date, "2025-10-20")
        XCTAssertEqual(newsletter.guid, "def-456")
        XCTAssertEqual(newsletter.filePath, "output/news-2025-10-20.html")
        XCTAssertEqual(newsletter.status, .completed)
        XCTAssertEqual(newsletter.generatedAt, "2025-10-20T06:15:00")
        XCTAssertEqual(newsletter.retryCount, 0)
    }

    func testNewsletterContentResponseWithHTML() throws {
        let json = """
        {
            "guid": "abc-123",
            "date": "2025-10-15",
            "status": "completed",
            "generated_at": "2025-10-15T06:00:00",
            "retry_count": 0,
            "html_content": "<html><body>Newsletter</body></html>"
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder().decode(NewsletterContentResponse.self, from: json)

        XCTAssertEqual(response.guid, "abc-123")
        XCTAssertEqual(response.status, "completed")
        XCTAssertEqual(response.htmlContent, "<html><body>Newsletter</body></html>")
    }

    func testNewsletterContentResponseWithoutHTML() throws {
        let json = """
        {
            "guid": "abc-123",
            "date": "2025-10-15",
            "status": "pending",
            "generated_at": null,
            "retry_count": 0,
            "html_content": null
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder().decode(NewsletterContentResponse.self, from: json)

        XCTAssertEqual(response.status, "pending")
        XCTAssertNil(response.generatedAt)
        XCTAssertNil(response.htmlContent)
    }

    func testNewslettersResponseDecodes() throws {
        let json = """
        {
            "newsletters": [
                {
                    "id": 1,
                    "user_id": 1,
                    "date": "2025-10-15",
                    "guid": "abc-123",
                    "file_path": null,
                    "status": "pending",
                    "generated_at": null,
                    "retry_count": 0
                }
            ],
            "year": 2025,
            "month": 10,
            "count": 1
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder().decode(NewslettersResponse.self, from: json)

        XCTAssertEqual(response.year, 2025)
        XCTAssertEqual(response.month, 10)
        XCTAssertEqual(response.count, 1)
        XCTAssertEqual(response.newsletters.count, 1)
        XCTAssertEqual(response.newsletters[0].guid, "abc-123")
    }
}
