VYAYAM coach voice clips (Phase F Part 2 — dormant until files exist)
======================================================================

Drop mp3 files into THIS directory. Any cue whose file exists plays the
recording; any cue whose file is missing falls back to browser speech
automatically. No code or config change is needed either way.

Record each clip with the exact phrase shown (natural, encouraging tone,
~ -16 LUFS, mono, 44.1 kHz mp3). Generate with ElevenLabs / Google
Cloud TTS Neural2 using your own account.

Tempo phase cues
  slowly_down.mp3      "Slowly down"
  hold.mp3             "Hold"
  up.mp3               "Up"
  pause.mp3            "Pause"

Session flow
  watch_me_first.mp3   "Watch me first. I will show you the movement."
  watch_me.mp3         "Watch me. I will show you the movement."
  one_more_time.mp3    "One more time. Watch the movement."
  now_you_try.mp3      "Now you try. Step into me."
  ready_step_in.mp3    "Ready. Step into the outline and begin when you are set."
  good_hold_there.mp3  "Good... hold it right there..."
  timer_starting.mp3   "Timer starting. Hold it."
  rest_over.mp3        "Rest over. Next set."
  next_set.mp3         "Next set."
  set_complete.mp3     "Set complete! Great work."
  last_one.mp3         "Last one. Give it everything."

Short encouragements
  nice_one.mp3         "Nice. One."
  two_keep_it_up.mp3   "Two. Keep it up."
  beautiful_hold.mp3   "Beautiful. Hold it right there."
  looking_good.mp3     "Looking good. Just a little more."
  getting_there.mp3    "You're getting there. Keep going."

Rep counts (spoken as bare numbers)
  num_1.mp3 .. num_10.mp3   "One" .. "Ten"

The phrase→file map lives in static/strength_app/js/voice_core.js
(COACH_CLIPS). If a spoken phrase in the app changes, update the map and
this list together.
