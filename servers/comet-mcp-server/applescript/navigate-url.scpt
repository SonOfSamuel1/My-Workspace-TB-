-- Navigate to a URL in Comet browser
on run argv
    set targetURL to item 1 of argv

    tell application "System Events"
        tell process "Comet"
            set frontmost to true

            -- Open URL using keyboard shortcut
            keystroke "l" using {command down}
            delay 0.2

            -- Clear the address bar
            keystroke "a" using {command down}
            delay 0.1

            -- Type the URL
            keystroke targetURL
            delay 0.2

            -- Navigate to the URL
            key code 36 -- Enter key

            -- Wait for page to start loading
            delay 1.0
        end tell
    end tell

    return "Navigated to: " & targetURL
end run