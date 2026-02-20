import SwiftUI

@Observable
@MainActor
final class AppViewModel {
    var users: [User] = []
    var selectedUser: User?
    var isLoading = false
    var error: Error?

    private let api: any NewsLlamaAPIProtocol

    init(api: any NewsLlamaAPIProtocol = NewsLlamaAPI()) {
        self.api = api
    }

    func loadUsers() async {
        isLoading = true
        error = nil
        do {
            users = try await api.fetchUsers()
            // Auto-select last used profile
            if selectedUser == nil, let lastId = UserDefaults.standard.object(forKey: "lastSelectedUserId") as? Int {
                selectedUser = users.first { $0.id == lastId }
            }
        } catch {
            self.error = error
        }
        isLoading = false
    }

    func selectUser(_ user: User) {
        selectedUser = user
        UserDefaults.standard.set(user.id, forKey: "lastSelectedUserId")
        if let concreteAPI = api as? NewsLlamaAPI {
            concreteAPI.currentUserId = user.id
        }
    }

    func logout() {
        selectedUser = nil
        UserDefaults.standard.removeObject(forKey: "lastSelectedUserId")
        if let concreteAPI = api as? NewsLlamaAPI {
            concreteAPI.currentUserId = nil
        }
    }

    func createProfile(firstName: String, interests: [String]) async {
        isLoading = true
        error = nil
        do {
            let response = try await api.createProfile(firstName: firstName, interests: interests)
            await loadUsers()
            // Auto-select the newly created user
            selectedUser = users.first { $0.id == response.userId }
            if let user = selectedUser {
                UserDefaults.standard.set(user.id, forKey: "lastSelectedUserId")
            }
        } catch {
            self.error = error
        }
        isLoading = false
    }

    func deleteProfile(userId: Int) async {
        isLoading = true
        error = nil
        do {
            try await api.deleteProfile(userId: userId)
            if selectedUser?.id == userId {
                selectedUser = nil
                UserDefaults.standard.removeObject(forKey: "lastSelectedUserId")
            }
            await loadUsers()
        } catch {
            self.error = error
        }
        isLoading = false
    }
}
