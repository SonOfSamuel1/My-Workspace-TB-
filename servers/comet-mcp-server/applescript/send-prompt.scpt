-- Send a prompt to Comet's assistant field
on run argv
    set promptText to item 1 of argv

    tell application "System Events"
        tell process "Comet"
            set frontmost to true

            -- Try to find and click the prompt input field
            -- This may need adjustment based on Comet's actual UI structure
            try
                -- Method 1: Try to find a text field
                click text field 1 of window 1
            on error
                -- Method 2: Use keyboard shortcut if available
                keystroke "l" using {command down}
            end try

            -- Small delay to ensure field is focused
            delay 0.2

            -- Clear the field first
            keystroke "a" using {command down}
            delay 0.1

            -- Type the prompt
            keystroke promptText
            delay 0.2

            -- Send the prompt (press Enter)
            key code 36
        end tell
    end tell

    return "Prompt sent: " & promptText
end run