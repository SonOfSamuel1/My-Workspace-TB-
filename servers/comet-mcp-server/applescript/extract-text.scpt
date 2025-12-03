-- Extract text from Comet's response area using Accessibility API
on run
    tell application "System Events"
        tell process "Comet"
            set frontmost to true

            -- Try multiple methods to extract text
            set responseText to ""

            try
                -- Method 1: Get all static text elements from the window
                set allTexts to value of every static text of window 1
                set responseText to allTexts as string
            on error
                try
                    -- Method 2: Try to get text from web area or scroll area
                    set responseText to value of text area 1 of scroll area 1 of window 1
                on error
                    -- Method 3: Use clipboard as fallback
                    -- Select all text
                    keystroke "a" using {command down}
                    delay 0.2
                    -- Copy to clipboard
                    keystroke "c" using {command down}
                    delay 0.2
                    -- Get clipboard content
                    set responseText to the clipboard as string
                end try
            end try

            return responseText
        end tell
    end tell
end run