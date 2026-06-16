# Changelog

All notable changes to this project will be documented in this file.

---

## [0.5.0] - 2026-06-06

### Added
- **Player-Driven Rooms & Lobbies:** Shipped a full room-based game architecture allowing players to create lobbies, generate 4-character room codes, and join rooms without requiring platform admin setup.
- **Lobby Ready States:** Added player readiness toggles with real-time status indicators in the waiting room layout.
- **Host Administrative Delegation:** Granted room creators host-level administrative controls, authorizing them to start the game, calculate round results, and close game sessions.
- **Seamless Session Recovery:** Created `/api/rooms/active-player-game/{player_id}` to automatically restore active game rooms and WebSocket channels upon page refresh.
- **Custom Player PINs:** Allowed players to specify their own 4-6 digit numeric passcode/PIN during registration, or have one auto-generated if left blank.
- **Unified Login Status Badges:** Introduced styled retro badges (`👤 Player Name | PIN: XXXX` and `⚙️ ADMIN MODE`) across all headers (`index.html`, `two-thirds-game.html`, `fish-pond-game.html`, `horse-race-game.html`) to display user authentication states clearly.
- **Centralized Admin Control Panel:** Enhanced the dashboard to support starting both the Two-Thirds game and the Fish Pond game directly from the home page.
- **Admin Player Management Panel:** Added a fully-featured table listing all players, their PINs (for easy recovery), their score, and a delete action to remove individual players.
- **Admin Database Utilities:** Created new admin utility endpoints to reset all player scores to 0 (`/api/players/reset-scores`) and clear all players (`/api/players/clear-all`) for quick session restarts.

### Fixed
- **Fish Pond Settings Display Bug:** Corrected a bug where the "Fish Pond" game was displayed as "Horse Racing" in the visibility toggle panel.
- **Fish Pond Navigation Setting Check:** Ensured that Fish Pond buttons in the main menu are properly toggled (hidden/shown) according to the admin's global game visibility settings.

## [0.4.0] - 2026-06-04

### Added
- **Retro-Tech Theme & Aesthetics:** Complete overhaul of frontend styling, retro-arcade theme. Featuring:
  - Deep earthy chocolate background and dark-khaki card backgrounds.
  - Flat 3D offset shadows (`box-shadow: 6px 6px 0px #180902`) and thick solid dark borders.
  - Pixel star ornaments (`✦`) rendered dynamically at card corners using CSS pseudo-elements.
  - Active hover/click animations where buttons translate `2px` to simulate mechanical clicks.
- **Floating Stack Widgets:** Custom floating terminal widget (`>_`) and achievement widget (`🏆`) in the bottom-right corner for quick scroll and navigation.
- **Google Typography:** Integrated Google Fonts (`Outfit` for geometric layout headings and `Share Tech Mono` for monospace stats/values).
- **Unified Brand Header:** Refactored header navigation into a single consistent bar featuring the `T2` logo box and horizontal navigation tabs across all pages (`index.html`, `two-thirds-game.html`, `horse-race-game.html`).

### Fixed
- **Stored XSS Vulnerabilities (Security Hardening):** Fixed multiple stored Cross-Site Scripting (XSS) injection vectors where player names retrieved from the database were rendered unsanitized using `.innerHTML`.
  - Added secure `escapeHTML()` utility.
  - Sanitized leaderboard entries in [script.js](file:///home/shantanu/programming/think-twice-V0.3/frontend/script.js).
  - Sanitized guesses and winner renders in [two-thirds-game.html](file:///home/shantanu/programming/think-twice-V0.3/frontend/two-thirds-game.html).
  - Sanitized participants, rankings, and horse listings in [horse-race-game.html](file:///home/shantanu/programming/think-twice-V0.3/frontend/horse-race-game.html).
- **Content Security Policy (CSP):** Implemented strict meta CSP tags to block unauthorized script execution and exfiltration attempts, preventing token theft from `localStorage`.
