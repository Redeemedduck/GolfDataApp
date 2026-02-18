The Core Problem: Session Name ≠ Club Name
Your app's "club" field is being populated with whatever the Uneekor session name is, but you're naming your sessions inconsistently across three very different categories:
Actual clubs — "Iron 1", "Driver", "9", "PW", "56", "GW", "SW"
Courses/rounds — "sgt pebble", "estes park", "broadmoar", "broadmore east front", "dpc scottsdale", "Sgt Plantation Course", "Sgt Rd 2 Kapalua", "Streamsong Front", "Silvertip Rd2"
Drills/activities — "warmup", "warmup 8 dst", "3/4 Speed Towel Drill", "1/2 Swing", "Dst Compressor 8", "Path Focus", "60 Shot Challenge", "Par 3 Tourney", "Bag Mapping", "Simtour"
In contrast, the Uneekor Power U Report has a two-level hierarchy: the top level is the session name (e.g., "sgt pebble"), and within that session, it breaks shots into actual club groups (e.g., IRON1, 50WEDGE, PITCHINGWEDGE). Your app appears to be grabbing the session-level name and using it as the club for all shots in that session, which is why "estes park" shows up as a "club" with 3 wildly different shots (carry ranging from 16.7 to 291.2 yards).
What This Breaks
Your Club Profiles page becomes useless because "estes park" and "Sgt Sony Open 1" show up alongside actual clubs like "7 Iron" and "Driver." The Multi-Metric Club Comparison radar chart on the Dashboard is comparing apples to oranges. And the "Club Naming Anomalies" detector is saying everything is fine, which it clearly isn't.

Recommendations for Better Classification
1. Separate "Session Type" from "Club" at the data model level. You need two distinct concepts: a session-level classification (what kind of practice this was) and a per-shot club identification (what club was actually used). Uneekor already provides per-shot club info within each report — you should pull that in during import rather than only using the session name.
2. Use your existing tag system to classify session types. You already have tags (Fitting, Practice, Round, Warmup). These map naturally to your naming patterns: "sgt pebble" → Round, "warmup 8 dst" → Warmup, "Dst Compressor 8" → Practice/Drill, "Iron 1" → Practice (single-club focused). You could auto-assign tags during import by pattern-matching the session name — keywords like "sgt", "rd1", "rd2", course names → Round; "warmup", "wmup" → Warmup; "dst", "drill", "towel", "compressor", "path focus" → Drill; standalone club names → Practice.
3. Normalize club names. Even when you do have actual club names, they're inconsistent: "1 Iron" vs "Iron 1" vs "Iron1", "7" vs "7 Iron" vs "M 7 Iron", "Wedge 50" vs "50WEDGE" vs "50 Warmup", "PW" vs "Wedge Pitching" vs "PITCHINGWEDGE" vs "Warmup Pw". Build a club name normalization map that consolidates these into canonical names like "1 Iron", "7 Iron", "50° Wedge", "Pitching Wedge", "Driver", "3 Wood", etc.
4. For round/course sessions, extract per-shot club data from Uneekor. The sgt pebble report already knows shots 1-52 were IRON1, shots 53-67 were 50WEDGE, etc. If your import process is only reading the session name and applying it to all shots, you're losing this valuable club-level detail that Uneekor provides.
5. Add a "session context" field with modifiers. Something like "8 Iron Magnolia" could be parsed as club = "8 Iron", context = "Magnolia" (course). "7 Iron Shoulders Right" = club "7 Iron", drill = "Shoulders Right". This lets you keep the rich context without polluting the club namespace.

1. Dashboard — Make It a Real Landing Page
Right now the Dashboard drops you into a single session view with a numeric session ID ("Session: 44266") that means nothing to a user. A golfer opening this wants to see how they're doing lately, not raw data from one arbitrary session.
Replace the session-first view with a "Recent Activity" overview — show a summary of the last 5-7 sessions with date, session name (from Uneekor), session type tag (Practice/Round/Warmup), total shots, and a quick highlight stat like best carry or avg smash. Think of it like a training log. The user can click into any session to get the deep-dive view you currently have.
The session selector is buried at the bottom of the sidebar — it's below Appearance, Dark Mode, and Data Source settings. The most important control on the page is the hardest to find. Move session selection front-and-center, ideally as a prominent selector near the top of the main content area, not tucked in the sidebar below theme toggles.
The session ID format "44266 (2026-02-10 1...)" is developer-facing, not user-facing. Show something like "Iron 1 Practice — Feb 10" or "Scottsdale Round — Feb 2" instead. The numeric ID is meaningless to a golfer.
The smash factor target of 1.50 seems hardcoded and is showing red for a 1.22 average. That's a driver-level target being applied to what might be a 1-iron session. Targets should be dynamic per club — a 1.22 smash on a 1-iron is actually decent.

2. Fix the Information Architecture (Session vs. Club vs. Drill)
This is the biggest structural problem. The Uneekor report for "dpc scottsdale" beautifully breaks out 8 different club groups in a left sidebar (dpc scottsdale, Iron 8, Driver, 70 yds, Wedge 50, Wedge Pitching, Iron 9, Wedge 60, warmup). Your app flattens all of that into one blob.
Add a session type classification system. When importing, detect or let the user tag whether this is a Round (multi-club, course play), Practice (single-club focused repetition), Warmup (short, pre-session), Drill (specific swing focus like "3/4 Speed Towel Drill"), or Fitting. This should drive how data is displayed — a Round should show a hole-by-hole or club-by-club breakdown, while a Practice session should show progression/consistency metrics for that one club.
For Round sessions, show a club breakdown similar to Uneekor's left sidebar. Let users drill into each club used during the round. Right now you're averaging a 3.6-yard wedge warmup shot together with a 324-yard driver max — that summary stat is garbage.

3. Club Profiles — The Most Broken Page
The dropdown has ~60+ entries that are a chaotic mix of clubs, courses, drills, and abbreviations. "estes park" sits next to "7 Iron" sits next to "3/4 Speed Towel Drill" sits next to "Sgt Sony Open 1." This page is unusable.
After fixing the data model, this page should only show actual golf clubs — organized in bag order: Driver, 3 Wood, 1 Iron, 6 Iron, 7 Iron, 8 Iron, 9 Iron, PW, 50°, 56°, 60°, SW, GW, etc. Show it as a visual "bag" with cards, not a giant dropdown.
Add a "My Bag" configuration where the user defines their 14 clubs with canonical names. Then map all the Uneekor club names (IRON1, Iron 1, Iron1, 1 Iron) to those canonical clubs. This immediately cleans up everything downstream.
The Distance Over Time chart has absurd x-axis labels ("23:59:59.999 Jan 20, 2026" to "00:00:00.0005") — these are timestamp formatting bugs. Should just show clean dates.
The "Compare with Other Clubs" section defaults to comparing 1 Iron with "1/2 Swing" and "3/4 Speed Towel Drill" — that's meaningless. Default to comparing with adjacent clubs in the bag (e.g., if viewing 7 Iron, auto-suggest 6 Iron and 8 Iron).

4. Big 3 Deep Dive — Good Concept, Needs Polish
The Big 3 Impact Laws section (Face Angle, Club Path, Strike Location) is genuinely well-conceived. The distribution histograms, the colored summary cards, and the D-Plane scatter plot are all valuable.
The summary cards' text is barely readable — dark cards with dark text. The actual degree values are nearly invisible. Increase contrast significantly.
Add shot-by-shot trend lines within a session. Golfers want to know: "Am I getting better as I warm up, or worse as I fatigue?" A simple line chart showing face angle or club path progression across shot numbers 1 through N within a session would be very useful.
The D-Plane scatter plot is great but has no quadrant labels. Add labels for the four zones (draw, fade, pull, push) so a golfer can instantly see their shot shape tendency without interpreting raw numbers.

5. The Sidebar Is Overloaded and Poorly Organized
The left sidebar mixes navigation, appearance settings, session selection, club filtering, and data source configuration all in one scrollable column. A golfer opening the app shouldn't need to scroll past "Supabase shots: 2159" and "Read Mode: Auto (SQLite first)" to find the session they want.
Move all developer/technical controls (Data Source, Read Mode, SQLite/Supabase indicators) to the Settings page exclusively. The main sidebar should only have navigation and context-relevant filters.
The duplicate navigation (top nav list and "Navigation" section below it) is confusing — consolidate to one nav.

6. Missing Features That Uneekor Has
Trajectory visualization. Uneekor's Side, Top, and Group views showing ball flight arcs are the most visually compelling part of their report. Your app has nothing like this. Even a simplified 2D trajectory overlay (side view showing height vs. distance) would add a lot.
Shot-by-shot navigation. Uneekor lets you click through shots one by one with arrow buttons, showing each shot's full details and trajectory. Your Shots tab shows a table, which is useful for data people but not for golfers who want to remember what each shot felt like.
Per-shot club impact visualization. The Club tab in Uneekor shows a visual of the clubface with dynamic loft, face angle, and attack angle. This is the kind of visual that helps golfers understand what's happening at impact intuitively rather than staring at numbers.

7. Overall UX Flow Improvements
There's no onboarding or empty state guidance. If someone opens this fresh, they see a bunch of technical controls and no indication of what to do first. A simple "Import your first Uneekor session to get started" wizard would help.
No date range filtering. Golfers think in terms of "how did I do this week" or "last month's progress." There's no way to view data across a date range — it's always one session at a time or all sessions aggregated.
No goal/progress tracking. The smash factor bar hints at this, but there's no way for a golfer to set goals ("get my 7-iron carry to 165") and track progress toward them over time.
No session notes. After a practice session, a golfer might want to jot down "was working on keeping right elbow tucked" — there's no place for this context that would make the data meaningful later.

Summary Priority List for Claude Code
If you're handing this to Claude Code, I'd suggest this order: first, fix the data model (session type + club normalization + bag mapping), second, rebuild the Dashboard as a training log landing page, third, clean up Club Profiles to only show real clubs in bag order, fourth, add date range filtering and session notes, fifth, improve Big 3 card readability and add quadrant labels, sixth, add trajectory visualization, and seventh, add goal tracking.
The data model fix unblocks everything else — without it, every view will continue to show noise.