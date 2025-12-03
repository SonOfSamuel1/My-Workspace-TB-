-- Check if Comet browser is running
on run
    tell application "System Events"
        set appList to name of every process
        if "Comet" is in appList then
            return "running"
        else
            return "not running"
        end if
    end tell
end run