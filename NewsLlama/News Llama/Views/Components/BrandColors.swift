import SwiftUI

extension Color {
    static let newsLlamaCoral = Color(red: 232 / 255, green: 93 / 255, blue: 74 / 255)
    static let newsLlamaCream = Color(red: 245 / 255, green: 241 / 255, blue: 234 / 255)
}

extension ShapeStyle where Self == Color {
    static var newsLlamaCoral: Color { .newsLlamaCoral }
    static var newsLlamaCream: Color { .newsLlamaCream }
}
