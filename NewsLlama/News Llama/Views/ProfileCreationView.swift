import SwiftUI

struct ProfileCreationView: View {
    @Environment(AppViewModel.self) private var appViewModel
    @Environment(InterestViewModel.self) private var interestViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var firstName = ""
    @State private var selectedInterests: Set<String> = []

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Button("Cancel") { dismiss() }
                    .keyboardShortcut(.cancelAction)
                Spacer()
                Text("New Profile")
                    .font(.headline)
                Spacer()
                Button("Create") {
                    Task {
                        await appViewModel.createProfile(
                            firstName: firstName,
                            interests: Array(selectedInterests)
                        )
                        dismiss()
                    }
                }
                .keyboardShortcut(.defaultAction)
                .disabled(firstName.trimmingCharacters(in: .whitespaces).isEmpty)
            }
            .padding()

            Divider()

            Form {
                Section("Name") {
                    TextField("First name", text: $firstName)
                        .textFieldStyle(.roundedBorder)
                }

                Section("Interests") {
                    if interestViewModel.isLoading {
                        ProgressView()
                    } else {
                        ForEach(interestViewModel.predefinedGroups) { group in
                            DisclosureGroup {
                                ForEach(group.interests, id: \.self) { interest in
                                    Toggle(interest, isOn: Binding(
                                        get: { selectedInterests.contains(interest) },
                                        set: { isOn in
                                            if isOn {
                                                selectedInterests.insert(interest)
                                            } else {
                                                selectedInterests.remove(interest)
                                            }
                                        }
                                    ))
                                }
                            } label: {
                                Label(group.name, systemImage: "folder")
                                    .badge(
                                        group.interests.filter { selectedInterests.contains($0) }.count
                                    )
                            }
                        }
                    }
                }
            }
            .formStyle(.grouped)
        }
        .frame(width: 450, height: 550)
        .task {
            await interestViewModel.loadPredefinedInterests()
        }
    }
}
