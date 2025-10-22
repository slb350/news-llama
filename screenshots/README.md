# News Llama Web Application - Mockup Screenshots

High-quality screenshots of the approved Phase 2 frontend mockup for marketing materials and GitHub documentation.

## Screenshots

### 01_home_profile_select.png
**Home Page / Profile Selection**
- Big centered logo (128px)
- Tagline: "No Drama, Just News Llama"
- Profile grid with avatar initials
- Clean coral and cream color scheme
- JetBrains Mono typography

**Use case**: Main landing page, GitHub README hero image

---

### 02_profile_create_interests.png
**Profile Creation with Interest Selection**
- Name input field
- Toggleable interest selection grid
- Pre-configured categories (AI, rust, LocalLLM, etc.)
- Selected interests displayed with click-to-remove
- Custom interest input field
- Interactive category buttons with coral accent

**Use case**: Feature showcase for personalization capabilities

---

### 03_calendar_view.png
**Calendar View**
- Monthly calendar grid
- Newsletter status indicators:
  - 🦙 = Newsletter ready
  - ⏳ = Generating
- Month navigation with HTMX
- User profile header with settings/switch profile actions
- Stats card showing newsletter counts
- Today highlighting with coral border

**Use case**: Main app interface showcase

---

### 04_profile_settings.png
**Profile Settings**
- Edit profile information
- Avatar upload placeholder
- Interest management (add/remove)
- Stats overview (total newsletters, completed, pending)
- Danger zone for profile deletion
- Form layout with warm cream cards

**Use case**: Settings and customization feature showcase

---

### 05_newsletter_modal.png
**Newsletter Modal View**
- Full-screen modal overlay
- Newsletter iframe with big centered logo (256px)
- Minimal modal header (date + close button)
- Coral accent close button
- Dark backdrop with click-to-close
- Newsletter content fully visible inside modal

**Use case**: Newsletter viewer feature, content showcase

---

## Technical Details

**Resolution**: 1920x1080 @ 2x (Retina/HiDPI)
**Format**: PNG
**Browser**: Chromium (Playwright headless)
**Captured**: October 22, 2025

## Design System

**Colors**:
- Coral accent: `#E85D4A`
- Coral light: `#FEE9E7`
- Warm cream background: `#F5F1EA`

**Typography**:
- Font: JetBrains Mono (all weights)
- Monospace aesthetic matching newsletter design

**Framework**:
- Tailwind CSS for utilities
- HTMX for SPA-like interactions
- Custom CSS for theme

## Regenerating Screenshots

To regenerate screenshots:

```bash
# Start development server
./venv/bin/uvicorn src.web.app:app --reload --port 8000

# Run screenshot script
./venv/bin/python take_screenshots.py
```

## Usage Guidelines

These screenshots are approved for:
- GitHub README
- Marketing materials
- Documentation
- Blog posts
- Social media

Maintain aspect ratio and don't crop out the branding elements (logo, tagline).
