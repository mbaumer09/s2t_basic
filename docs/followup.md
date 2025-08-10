1. Audio Quality & Processing:
    - Should there be any noise reduction or audio preprocessing before sending to Whisper?
        - Help me understand the additional technical complexity required here and the likely improvement to product quality. If this is relatively simple to execute on and will substantially improve quality then we should do it but if its complex and a marginal improvement then we should not.
    - What's the expected behavior if multiple microphones are present?
        - One of the microphones should be selected as the active one by the user
    - Should we handle audio clipping or volume normalization?
        - same as the first question - how complex and how valuable?
  
  2. Error Handling:
    - What should happen if Whisper fails to transcribe (returns empty/gibberish)?
        - It should produce text of whatever it returns
    - How should the script handle microphone access errors?
        - It should guide the user to getting microphone access
    - Should failed transcriptions be logged somewhere?
        - All transcriptions should be logged, lets create a log directory with one .txt file per session

  3. Performance Targets:
    - What's the acceptable latency between key release and text appearing? (1s? 2s? 5s?)
        - <1s would be ideal, 5s would probably be too slow and we would need to figure out how to optimize
    - Should we implement a maximum recording duration to prevent memory issues?
        - Yes this is sensible, would batch processing be viable

  4. Text Output Behavior:
    - Should the transcribed text preserve capitalization and punctuation from Whisper?
        - it can keep it for now, we can fix it later if it is a problem
    - How should special characters or emojis in speech be handled?
        - no emojis or special characters just write out the word
    - Should we add a space before typing if the cursor is at the end of existing text?
        - sure

  5. User Feedback:
    - The PRD mentions console output, but should we consider audio beeps for recording start/stop?
        - yes an audio cue makes sense for this
    - Should there be any indication when the model is still loading on startup?
        - yes the console output should track loading progress

  6. Technical Details:
    - Why scipy specifically for WAV file writing when sounddevice can handle this?
        - i will let you determine the most sensible framework for writing audio files, just write out the options and the pros and cons of each and determine which is optimal
    - Should the temp file use the system's temp directory or current directory?
        - current directory
    - Any specific sample rate/bit depth requirements for audio recording?
        - whatever is required for reliable speech parsing

  7. Edge Cases:
    - What if the user holds the key for a very long time (>1 minute)?
        - per above, lets set a cap based on user's machine specs
    - Should rapid key press/release be ignored (debouncing)?
        - yea there can be a cooldown, if someone taps the key over and over it will turn on, then turn off, then there will be a cooldown before it will turn on again after being turned off
    - How to handle if the script loses focus while recording?
        - not sure what this means