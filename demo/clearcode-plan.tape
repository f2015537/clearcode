# clearcode /plan demo — records the full plan→execute flow and outputs a GIF
# PlaybackSpeed 4 compresses a ~3-5 min run into a ~45-75 sec watchable GIF.

Output demo/clearcode-plan.gif

Set Shell "bash"
Set FontSize 13
Set Width 1800
Set Height 950
Set Theme "Dracula"
Set Framerate 15
Set PlaybackSpeed 8
Set WindowBar Rings
Set BorderRadius 8
Set Padding 20
Set TypingSpeed 40ms

# Run the demo script — setup (cd, clean, activate) is embedded inside it.
# The script auto-approves the plan so no interactive input is needed.
Type "/private/tmp/demo_setup.sh"
Enter

# Wait for plan + execution + re-index to complete (up to 20 min for gpt-5.5).
# At PlaybackSpeed 8 a 15-min run → ~112 sec GIF.
Sleep 800s
Sleep 30s
