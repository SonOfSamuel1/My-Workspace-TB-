-- Activate Comet browser and bring it to the foreground
on run
    tell application "Comet"
        activate
    end tell

    -- Wait for the window to be ready
    delay 0.5

    return "Comet activated"
end run