import SwiftUI

@Observable
@MainActor
final class InterestViewModel {
    var predefinedGroups: [InterestGroup] = []
    var isLoading = false
    var error: Error?

    private let api: any NewsLlamaAPIProtocol

    init(api: any NewsLlamaAPIProtocol = NewsLlamaAPI()) {
        self.api = api
    }

    func loadPredefinedInterests() async {
        isLoading = true
        error = nil
        do {
            predefinedGroups = try await api.fetchPredefinedInterests()
        } catch {
            self.error = error
        }
        isLoading = false
    }

    func addInterest(userId: Int, interestName: String, isPredefined: Bool) async {
        error = nil
        do {
            try await api.addInterest(userId: userId, interestName: interestName, isPredefined: isPredefined)
        } catch {
            self.error = error
        }
    }

    func removeInterest(userId: Int, interestName: String) async {
        error = nil
        do {
            try await api.removeInterest(userId: userId, interestName: interestName)
        } catch {
            self.error = error
        }
    }
}
