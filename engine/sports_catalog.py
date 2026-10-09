"""
sports_catalog.py — the starter idea bank: 230+ hand-written video topics.
===========================================================================

WHAT THIS IS
A one-time seed, not a cage. Every row here becomes a real row in the
`topics` table the first time the app runs (see seed_all() / the
add-topics workflow) — after that, topic_synthesizer.py keeps inventing
NEW topics forever in the same spirit, the same way it already does for
every persona in the original project. This file exists so the channel has
~230 genuinely good, specific, curiosity-gap topics on day one instead of
an empty pool waiting on the first AI call.

THE 85/15 SPLIT
`sport` is either "cricket" or "other_sport". content_mix.py reads this
field to keep new-topic selection at roughly 85% cricket / 15% other
sports — see that module for how the ratio is actually enforced run to
run. This file does not need to hit 85/15 itself; it only needs a deep
enough pool on BOTH sides that the ratio has real material to draw from.
There is deliberately more here than 15% "other sport" so that side never
runs dry and starts repeating.

FIELDS
  name          — the specific video idea (same bar as topic_synthesizer's
                  own system prompt: specific enough to be one scene, not
                  a whole book; contains a real curiosity gap)
  description   — one sentence naming the angle, handed to brief.py/
                  script_generator.py as extra context
  sport         — "cricket" | "other_sport"
  sub_sport     — only set for sport == "other_sport" (e.g. "hockey")
  category      — see CATEGORIES below; also used for admin-panel filters
                  and for engine.archetypes routing (see archetype_for())
  engagement_tier — "high" | "standard". A STARTING GUESS only — a human
                  editorial judgment about which angles travel best, used
                  purely to seed content_mix's daily slot planner before
                  any real analytics exist. performance_loop.py OVERRIDES
                  this with real view/like/share data the moment a topic's
                  video has actually published and been measured — see
                  that module's `effective_engagement_tier()`.
  quiz_friendly — True if this naturally ends in a good "now guess the
                  related stat" CTA (engine/engagement.py uses this to
                  decide whether to force a quiz close).
"""

CATEGORIES = {
    "rules":              "Laws & Rules",
    "records_stats":      "Records & Stats",
    "player_story":       "Player Life Stories",
    "current_players":    "Current Players On The Rise",
    "where_are_they_now": "Where Are They Now",
    "unsung_history":     "Unnoticed Achievements",
    "team_history":       "Team & Country Histories",
    "world_cup":          "World Cup History",
    "ipl":                "IPL & Leagues",
    "governance_business": "Boards, Governance & Money",
    "technology":         "Cricket Technology",
    "iconic_matches":     "Iconic Matches To Watch",
    "controversies":      "Controversies, Factually",
    "training_science":   "Training, Fitness & Analytics",
    "womens_cricket":     "Women's Cricket",
    "domestic_cricket":   "Domestic Cricket",
    "weather_pitch":      "Pitches, Weather & Conditions",
    "trivia_quiz":        "Did You Know / Trivia",
    "commentary":         "Iconic Commentary & Moments",
    "global_reach":       "Cricket In Unusual Places",
}

# Maps a catalog category to the archetype defined in engine/archetypes.py
# (extended in this project with the sports-specific archetypes — see that
# file). One place, so a category's "kind of video" stays consistent
# everywhere it's used.
CATEGORY_ARCHETYPE = {
    "rules":               "rules_explainer",
    "records_stats":       "records_and_stats",
    "player_story":        "player_story",
    "current_players":     "player_story",
    "where_are_they_now":  "where_are_they_now",
    "unsung_history":      "unsung_history",
    "team_history":        "history_deep_dive",
    "world_cup":           "history_deep_dive",
    "ipl":                 "business_and_governance",
    "governance_business": "business_and_governance",
    "technology":          "informative",
    "iconic_matches":      "history_deep_dive",
    "controversies":       "myth_busting",
    "training_science":    "informative",
    "womens_cricket":      "unsung_history",
    "domestic_cricket":    "informative",
    "weather_pitch":       "informative",
    "trivia_quiz":         "quiz_challenge",
    "commentary":          "history_deep_dive",
    "global_reach":        "unsung_history",
}


def archetype_for(category: str) -> str:
    return CATEGORY_ARCHETYPE.get(category, "informative")


# ─── CRICKET (≈85% of the channel) ─────────────────────────────────────────

CRICKET_TOPICS = [
    # -- Laws & Rules --------------------------------------------------------
    ("Why LBW is the single most argued-about rule in cricket", "Break down what the umpire actually has to judge in half a second — line, impact, and where the ball was going.", "rules", "standard", True),
    ("The exact height and gap rules for cricket stumps nobody checks", "Real numbers: stump height, bail length, and the gap between stumps a ball can sneak through.", "rules", "standard", True),
    ("What actually counts as a no-ball, beyond just overstepping", "Height no-balls, front-foot no-balls, and the back-foot rule almost nobody can explain correctly.", "rules", "standard", True),
    ("How DRS actually decides an LBW — the three checks explained", "Pitching, impact, and wickets zones — and why 'umpire's call' isn't a cop-out, it's a designed margin of error.", "rules", "high", True),
    ("The Mankad rule — why running out a non-striker backing up is completely legal", "The history, the law, and why it keeps splitting the cricket world in half.", "rules", "high", True),
    ("What a 'timed out' dismissal actually requires", "The rarest way to get out in cricket, and the one real instance that made world headlines.", "rules", "standard", True),
    ("Why a boundary catch needs the fielder's first touch inside the rope", "The airborne-catch rule that decides some of cricket's most replayed moments.", "rules", "high", True),
    ("What obstructing the field actually means, and how rare it is", "One of cricket's strangest dismissals, and the real instances where it happened.", "rules", "standard", True),
    ("How the follow-on rule works, and why captains almost never enforce it anymore", "The 200-run threshold in Tests, and the modern reasoning against pressing the advantage.", "rules", "standard", False),
    ("Why powerplay overs exist and how the fielding restrictions actually work", "The exact over-by-over rules that shape the first 10 overs of every ODI.", "rules", "standard", False),
    ("The Super Over, explained — and what happens if THAT also ties", "Cricket's tie-breaker, and the boundary-count rule that decided a real World Cup final.", "rules", "high", True),
    ("Why bats have a maximum size, and who enforces it", "The exact width, edge and depth limits — and the bat gauge umpires actually carry.", "rules", "standard", True),
    ("The concussion substitute rule, and the real match that created it", "How one serious injury changed cricket's substitution laws forever.", "rules", "standard", False),
    ("What actually makes a ball 'wide' in white-ball cricket vs Test cricket", "The rule changes slightly by format, and almost no casual viewer knows it.", "rules", "standard", True),
    ("Why a soft signal exists in DRS reviews, and why it's controversial", "The on-field call that technology can overturn — but only sometimes.", "rules", "high", False),
    ("The real reason cricket has a 'new ball' every innings", "Ball wear, swing, and why bowlers change their whole approach as it ages.", "rules", "standard", False),
    ("What happens if a match is abandoned — how results are actually decided", "Duckworth-Lewis-Stern explained simply: the method nobody understands but everyone argues about.", "rules", "high", True),
    ("Why a batter can be given out 'hit wicket' even off their own bat", "The dismissal that punishes a batter for their own gear or footwork.", "rules", "standard", True),
    ("The actual over-rate penalty rules captains hate the most", "Why slow over-rates cost captains suspensions and fielding restrictions.", "rules", "standard", False),
    ("Why the pink ball exists, and the actual rules around day-night Tests", "Visibility science, seam differences, and why not every ground hosts one.", "rules", "standard", False),

    # -- Records & Stats -------------------------------------------------------
    ("Who actually holds the record for most Test wickets, and by how much", "The number that separates the greatest wicket-taker in Test history from everyone else.", "records_stats", "high", True),
    ("Who holds the most runs in Test cricket history, and the number that may never be broken", "A career-long record built over two decades — and what it would take to catch it.", "records_stats", "high", True),
    ("Who holds the most catches by a fielder in Test cricket", "The quiet record that gets far less attention than batting or bowling ones.", "records_stats", "standard", True),
    ("The fastest century in ODI cricket history, ball by ball", "How few deliveries it actually took, and what a innings like that even looks like.", "records_stats", "high", True),
    ("The highest individual score in Test cricket, and who's come closest since", "The number most players never get near, and the handful who have threatened it.", "records_stats", "high", True),
    ("The highest team total ever posted in an ODI innings", "How a team actually scores that many runs inside 50 overs.", "records_stats", "standard", True),
    ("The most sixes hit by a single player in international cricket", "A record built over hundreds of innings — and who's closing in on it now.", "records_stats", "high", True),
    ("Who holds the record for most centuries in ODI cricket", "The number of hundreds that took over a decade and a half to accumulate.", "records_stats", "high", True),
    ("The youngest player to ever debut in international cricket", "How young is too young — and the country that gave a teenager their international cap.", "records_stats", "standard", True),
    ("The oldest player to ever play a Test match", "Cricket careers that stretched decades longer than almost any other sport allows.", "records_stats", "standard", True),
    ("Most ducks in international cricket — the record nobody wants", "Even the greatest batters have this number, and it's higher than you'd guess.", "records_stats", "standard", True),
    ("The fastest bowled delivery ever recorded in cricket history", "The speed gun number that's stood for years, and who's tried to break it.", "records_stats", "high", True),
    ("Who has taken the most hat-tricks in international cricket", "Three wickets in three balls — and the bowlers who've done it more than once.", "records_stats", "standard", True),
    ("The most wickets taken in a single Test match by one bowler", "A near-impossible feat: dismissing almost an entire top order twice over.", "records_stats", "high", True),
    ("Who holds the record for most man-of-the-match awards in Test cricket", "The stat that measures consistent match-defining performances, not just totals.", "records_stats", "high", True),
    ("The most successful review rate by any team using DRS", "Which side actually reads the game best when the technology gets involved.", "records_stats", "standard", False),
    ("The longest six ever measured in professional cricket", "The physics of a ball hit far enough to be measured in hundreds of metres.", "records_stats", "standard", True),
    ("Most stumpings by a wicketkeeper in international cricket", "The lightning-fast skill that almost never gets its own highlight reel.", "records_stats", "standard", True),
    ("The most economical bowling figures ever recorded in a T20 international", "Bowling an entire spell and conceding almost nothing — how rare that actually is.", "records_stats", "standard", True),
    ("Who has captained their team to the most Test match wins", "Leadership records outlast almost every individual batting or bowling stat.", "records_stats", "standard", True),

    # -- Player life stories ---------------------------------------------------
    ("Sachin Tendulkar's first international century, and the pressure behind it", "A teenager walking out to bat for a nation that had waited years for exactly this.", "player_story", "high", True),
    ("How Kapil Dev built India's first World Cup-winning team from nothing", "The 1983 squad nobody backed, and the captain who refused to accept the odds.", "player_story", "high", True),
    ("MS Dhoni's journey from ticket collector to World Cup-winning captain", "The small-town path that led to lifting cricket's biggest trophy twice.", "player_story", "high", True),
    ("Shane Warne's first Test wicket, and why it became known as 'the ball of the century'", "One delivery that redefined what leg-spin could do to a world-class batter.", "player_story", "high", True),
    ("Don Bradman's batting average, and why it's considered statistically impossible", "A number so far ahead of the next-best player that statisticians still study it.", "player_story", "high", True),
    ("Brian Lara's world-record Test innings, and the story behind it", "The single innings that still stands as the highest score in Test history.", "player_story", "high", True),
    ("Imran Khan's path from fast bowler to World Cup-winning captain to Prime Minister", "A cricket career that became one of the most unusual life stories in the sport.", "player_story", "high", True),
    ("Wasim Akram's rise from a college trial to becoming the 'Sultan of Swing'", "How a teenager's audition in front of Pakistan's selectors changed fast bowling.", "player_story", "standard", True),
    ("Sunil Gavaskar's opening partnership record, and why it took decades to threaten", "The batting discipline that built the blueprint for every opener after him.", "player_story", "standard", True),
    ("Viv Richards batting without a helmet — the story behind cricket's most fearless approach", "An era of fast bowling with no protection, and the batter who dominated it anyway.", "player_story", "high", True),
    ("Ricky Ponting's record as the most successful ODI captain in World Cup history", "Back-to-back titles, and the leadership style that made Australia nearly unbeatable.", "player_story", "standard", True),
    ("Kumar Sangakkara's rise as one of the greatest wicketkeeper-batsmen ever", "The rare combination of technique and glovework that redefined the role.", "player_story", "standard", True),
    ("Muttiah Muralitharan's bowling action controversy, and how he answered it", "The biomechanical testing that settled one of cricket's most debated questions.", "player_story", "high", True),
    ("AB de Villiers and the invention of '360-degree batting'", "How one player made shots that didn't previously exist part of the modern game.", "player_story", "high", True),
    ("Jacques Kallis and the case for cricket's greatest all-rounder", "A player who could have made most teams as a specialist batter OR bowler alone.", "player_story", "standard", True),
    ("Virender Sehwag's approach that turned Test batting into T20 hitting", "The mindset that made 300 in a day look ordinary for one particular batter.", "player_story", "standard", True),
    ("Glenn McGrath's metronomic accuracy, and the line-and-length discipline behind it", "Not raw pace, not big spin — just relentless precision that broke batters down.", "player_story", "standard", False),
    ("Rahul Dravid's 'The Wall' nickname, and the innings that earned it", "Test cricket's most patient batter, and the marathon knocks behind the reputation.", "player_story", "standard", False),
    ("Jonty Rhodes and the run-out that changed how fielding is coached forever", "One dive in a World Cup match that made fielding a specialist skill overnight.", "player_story", "high", True),
    ("Shakib Al Hasan and Bangladesh's rise as a genuine all-rounder powerhouse", "How one player carried Bangladesh's cricket ambitions on both bat and ball.", "player_story", "standard", False),

    # -- Current players on the rise -------------------------------------------
    ("Shubman Gill's rapid rise from U-19 star to India's Test opener", "The junior-cricket dominance that fast-tracked him into the senior side.", "current_players", "high", True),
    ("Yashasvi Jaiswal's journey from selling pani puri to playing for India", "One of Indian cricket's most unlikely paths to the international stage.", "current_players", "high", True),
    ("Washington Sundar's rare skill as a genuine batting all-rounder for India", "An off-spinner who bats high enough to change a team's entire balance.", "current_players", "standard", True),
    ("Rinku Singh's record-breaking finish in the IPL that made him a household name", "Five sixes in the final over — the innings that rewrote what a 'finisher' could do.", "current_players", "high", True),
    ("Travis Head's aggressive batting style and why bowlers dread facing him", "The Australian batter whose big-match performances keep arriving at the worst time for opponents.", "current_players", "standard", True),
    ("Shaheen Shah Afridi's new-ball spell that shook a World Cup opener", "The Pakistani pacer whose opening burst decided a match before it really began.", "current_players", "high", True),
    ("Jasprit Bumrah's unusual bowling action, and why it's so hard to face", "A release point that doesn't match any textbook coaching manual — and works anyway.", "current_players", "high", True),
    ("Kane Williamson's quiet consistency as one of the modern game's best techniques", "Not the loudest name, but among the most technically complete batters of his era.", "current_players", "standard", False),
    ("Babar Azam's rise to becoming Pakistan's most consistent modern batter", "The technique comparisons to past greats, and the numbers behind them.", "current_players", "standard", False),
    ("Suryakumar Yadav and the shots that earned him the nickname '360'", "A T20 specialist whose range of strokes turns defence into scoring options.", "current_players", "high", True),
    ("Mohammed Siraj's journey from an auto driver's son to India's new-ball spearhead", "A Hyderabad upbringing that shaped one of India's most improved fast bowlers.", "current_players", "high", True),
    ("Nathan Lyon's rise as one of the most underrated off-spinners in Test cricket", "Consistently overlooked, consistently among the wicket charts for over a decade.", "current_players", "standard", False),
    ("Heinrich Klaasen's explosive finishing role for South Africa", "The wicketkeeper-batter turning the death overs into his own specialty.", "current_players", "standard", True),
    ("Rachin Ravindra's breakout World Cup that surprised even New Zealand fans", "An uncapped name before the tournament, a headline name by the end of it.", "current_players", "high", True),
    ("Arshdeep Singh's rise as India's death-overs yorker specialist", "The specific skill that made him indispensable in T20 cricket's toughest six overs.", "current_players", "standard", False),

    # -- Where are they now -----------------------------------------------------
    ("What happened to the 1983 World Cup-winning Indian squad after retirement", "Where the players who changed Indian cricket forever ended up in their post-playing lives.", "where_are_they_now", "high", True),
    ("What Sourav Ganguly does now, years after captaining India", "From the pitch to cricket administration — the second act of his career.", "where_are_they_now", "standard", False),
    ("What happened to VVS Laxman after his playing career ended", "The Hyderabad batter behind one of Test cricket's greatest comebacks, now coaching the next generation.", "where_are_they_now", "standard", False),
    ("Where Shane Warne's cricket legacy lives on since his passing", "How his influence on leg-spin and commentary still shapes the modern game.", "where_are_they_now", "standard", False),
    ("What Anil Kumble does now, away from the bowling crease", "From over 600 Test wickets to a role shaping Indian cricket's next generation.", "where_are_they_now", "standard", False),
    ("Where Brett Lee's career went after his playing days in Australia", "From express pace bowling to commentary boxes and cross-cultural cricket ties.", "where_are_they_now", "standard", False),
    ("What happened to the West Indies pace quartet after cricket's most feared era ended", "Four bowlers who terrorised batting line-ups for over a decade — and their lives after.", "where_are_they_now", "high", True),
    ("Where Adam Gilchrist's aggressive batting legacy shows up in today's game", "The wicketkeeper-opener whose approach influenced a generation of attacking gloveman.", "where_are_they_now", "standard", False),
    ("What Yuvraj Singh does now, after his six sixes and his cancer recovery", "One of India's most beloved all-rounders, and the life he's built since retiring.", "where_are_they_now", "high", True),
    ("Where Zaheer Khan's career took him after leading India's pace attack", "From spearheading India's bowling to shaping strategy from the coaching box.", "where_are_they_now", "standard", False),

    # -- Unsung / unnoticed achievements ----------------------------------------
    ("The bowler with a better economy rate than every 'great' you've heard of", "A statistic that rewards control over spectacle — and the overlooked name behind it.", "unsung_history", "high", True),
    ("The unheralded fielder whose catches quietly won matches nobody credits him for", "The players whose contributions never make the highlight reel but decide results.", "unsung_history", "standard", True),
    ("The domestic cricket record that outlasted every international one", "A number set far from international TV cameras that's never been touched since.", "unsung_history", "standard", True),
    ("The Associate-nation cricketer who outperformed Test regulars and got overlooked", "Talent that never got the stage the bigger cricket boards could offer.", "unsung_history", "high", True),
    ("The umpire whose decision accuracy is still the gold standard decades later", "The officiating career nobody talks about, but every board still studies.", "unsung_history", "standard", False),
    ("The substitute fielder who changed a World Cup final and is barely remembered", "One moment in the field that shifted a trophy — credited to almost nobody.", "unsung_history", "high", True),
    ("The bowler who invented a delivery that's now used by an entire generation", "Where the doosra, the carrom ball, or the knuckleball actually came from.", "unsung_history", "high", True),
    ("The first cricketer from their country to ever play international cricket", "Someone had to be first — and that story usually gets forgotten fastest.", "unsung_history", "standard", True),
    ("The coach behind a World Cup win who never gets mentioned in the highlights", "The tactical mind shaping a champion team from entirely off camera.", "unsung_history", "standard", False),
    ("The record partnership that saved a team from its worst-ever batting collapse", "Two batters, one genuine crisis, and an innings almost nobody remembers by name.", "unsung_history", "standard", True),

    # -- Team & country histories -------------------------------------------------
    ("How Afghanistan built a Test cricket team out of refugee camps", "A cricketing rise with almost no domestic infrastructure behind it — built from nothing.", "team_history", "high", True),
    ("South Africa's isolation from world cricket during apartheid, explained", "Two decades locked out of the international game, and the return that followed.", "team_history", "high", True),
    ("How the West Indies became cricket's most feared team of the 1980s", "A collection of islands that built one of the most dominant sides in sport history.", "team_history", "high", True),
    ("Why Bangladesh's rise to Test status took so much longer than expected", "The structural challenges behind building a competitive cricket nation from scratch.", "team_history", "standard", False),
    ("Ireland's long road to Test cricket status, and what it actually took", "Decades of Associate-level cricket before finally earning the sport's top tier.", "team_history", "standard", False),
    ("How New Zealand built a reputation as cricket's most respected underdog", "Consistently smaller resources, consistently competitive — how that culture formed.", "team_history", "standard", False),
    ("Zimbabwe's cricket golden era, and what happened to it since", "A genuinely strong Test side in the 1990s-2000s, and the decline that followed.", "team_history", "high", True),
    ("Why England is considered the 'home' of cricket, and how the sport actually spread from there", "The colonial-era spread of the sport, country by country, across the world.", "team_history", "standard", False),
    ("How Australia built its cricket academy system that keeps producing champions", "The structured pathway behind one of the most consistently successful cricket nations.", "team_history", "standard", False),
    ("Pakistan's reverse-swing revolution and how it changed fast bowling worldwide", "A skill pioneered in one country that every pace attack now tries to master.", "team_history", "high", True),
    ("Sri Lanka's 1996 World Cup win and the tactical revolution it started", "Aggressive powerplay batting that the rest of the cricket world copied for decades.", "team_history", "high", True),
    ("How the Netherlands keeps producing World Cup upsets with a part-time domestic system", "A cricket nation with almost no professional infrastructure still shocking Test teams.", "team_history", "standard", True),
    ("The USA's surprising cricket history, and why the sport is investing there now", "A country with almost no cricket culture suddenly co-hosting a World Cup.", "team_history", "high", True),
    ("India's transformation from cricket minnow to global powerhouse, decade by decade", "The infrastructure, money, and talent pipeline that changed everything after 1983.", "team_history", "high", True),
    ("Why Scotland keeps producing giant-killing performances against Full Member teams", "A small cricket nation with an outsized habit of beating teams ranked far above it.", "team_history", "standard", True),
    ("How Nepal built one of the most passionate, fastest-growing cricket fanbases in Asia", "A country with limited resources but a fan culture rivaling much bigger boards.", "team_history", "standard", False),
    ("The forgotten story of cricket in East Africa's early international tournaments", "A region's brief moment on the world cricket stage that's almost never discussed.", "team_history", "standard", False),
    ("Why Namibia's cricket program punches above its population size", "A small nation regularly qualifying for global tournaments against much bigger boards.", "team_history", "standard", False),

    # -- World Cup history ---------------------------------------------------------
    ("The story of the very first Cricket World Cup in 1975, and who won it", "The tournament that started it all, played in a format almost unrecognisable today.", "world_cup", "high", True),
    ("How India's 1983 World Cup win changed the entire economics of cricket", "A single upset victory that turned cricket into India's national obsession and biggest industry.", "world_cup", "high", True),
    ("The 1999 World Cup Super Six tie that's still debated for its tiebreaker rule", "A group-stage tie decided on a technicality that changed how future tournaments were structured.", "world_cup", "high", True),
    ("The 2019 World Cup final — the only one ever decided by a boundary countback", "Cricket's most dramatic finish: a tie, a Super Over, and then another tiebreaker.", "world_cup", "high", True),
    ("Kenya's unlikely run to the 2003 World Cup semi-final", "An Associate nation's underdog story that briefly shook the cricket establishment.", "world_cup", "high", True),
    ("The 1992 World Cup's rain-rule controversy that changed how cricket handles weather", "The match that exposed a broken rain formula and forced cricket to fix it.", "world_cup", "high", True),
    ("How the T20 World Cup was created, and why it changed cricket's entire format landscape", "The tournament that accelerated cricket's fastest-growing format worldwide.", "world_cup", "standard", False),
    ("The story of Zimbabwe hosting its first-ever World Cup matches in 2003", "A tournament overshadowed by political controversy on and off the pitch.", "world_cup", "standard", False),
    ("Why the 2007 World Cup upset (India's early exit) reshaped the sport's TV economics", "One shock elimination that changed broadcaster strategy and format planning for years.", "world_cup", "high", True),
    ("The Netherlands' 2023 World Cup upset over South Africa, explained", "A part-time domestic cricket team beating one of the tournament's genuine title contenders.", "world_cup", "high", True),
    ("How Australia became the most World Cup-winning team in cricket history", "A dominant run across formats that no other nation has matched.", "world_cup", "standard", True),
    ("The forgotten story of the first-ever Women's Cricket World Cup in 1973", "Two years before the men's tournament even existed — a history most fans never hear.", "world_cup", "high", True),

    # -- IPL & leagues -----------------------------------------------------------
    ("How the IPL auction actually decides a player's price", "The bidding mechanics, base prices, and purse rules behind cricket's richest league.", "ipl", "high", True),
    ("Why the IPL changed the economics of cricket forever", "From a domestic tournament to the second-richest sports league in the world by per-match value.", "ipl", "high", True),
    ("The story of the IPL's very first season and how close it came to not happening", "The 2008 launch that reshaped franchise cricket globally, against real early doubts.", "ipl", "standard", False),
    ("How an uncapped IPL player can out-earn established international stars", "The auction dynamics behind young, unproven talent commanding record prices.", "ipl", "high", True),
    ("Why some of the best T20 players never played in the IPL", "Scheduling conflicts, national contracts, and the players who missed cricket's biggest stage.", "ipl", "standard", False),
    ("The retention rule that decides which IPL stars stay with their franchise", "The behind-the-scenes mechanics that shape a team's roster before the auction even begins.", "ipl", "standard", False),
    ("How the Big Bash League changed Australian domestic cricket's audience completely", "A format built for TV and families that reshaped who actually watches cricket.", "ipl", "standard", False),
    ("The business model behind franchise cricket leagues around the world", "Broadcast rights, sponsorships, and city branding — how a league actually makes money.", "ipl", "standard", False),
    ("Why some IPL franchises have never won the title despite huge spending", "Money doesn't guarantee trophies — the teams that prove it every season.", "ipl", "standard", True),
    ("How the Hundred was created to try to simplify cricket for new fans", "A shorter, simpler format designed specifically to attract audiences outside traditional cricket countries.", "ipl", "standard", False),
    ("The impact tax rule that quietly reshaped how franchise leagues manage overseas talent", "The financial mechanics behind why some leagues cap foreign player minutes.", "ipl", "standard", False),
    ("How mystery spinners became franchise cricket's most valuable auction commodity", "Unusual bowling actions that are hard to face even with video analysis prepared.", "ipl", "standard", True),

    # -- Governance & business -------------------------------------------------
    ("How the BCCI was formed, and how it became cricket's most powerful board", "From a modest 1928 founding to controlling the sport's biggest revenue streams.", "governance_business", "high", True),
    ("Who actually runs the ICC, and how much real power it has over member boards", "The governance structure behind international cricket's global rulebook.", "governance_business", "standard", False),
    ("How broadcast rights deals actually fund international cricket", "Where the money from a TV deal actually goes once a board signs the contract.", "governance_business", "high", True),
    ("Why some cricket boards are broke while others are enormously wealthy", "The revenue-sharing gap that separates cricket's richest and poorest nations.", "governance_business", "high", True),
    ("How a cricket board decides which tours and series actually get scheduled", "The Future Tours Programme, explained — and the politics behind it.", "governance_business", "standard", False),
    ("The real financial gap between men's and women's international cricket contracts", "What the pay-equity numbers actually look like, board by board.", "governance_business", "high", True),
    ("How sponsorship logos on a cricket jersey are actually priced and sold", "The real economics behind the branding you see covering every international kit.", "governance_business", "standard", False),
    ("Why some countries struggle to build cricket stadiums despite huge fan bases", "Land, funding, and governance hurdles that slow down cricket infrastructure.", "governance_business", "standard", False),

    # -- Technology --------------------------------------------------------------
    ("How Hawk-Eye actually tracks a cricket ball's path in real time", "The camera and prediction system behind every DRS decision you see on screen.", "technology", "high", True),
    ("What Snickometer and UltraEdge actually detect that the human ear can't", "The sound-wave technology deciding thin edges umpires can't always hear.", "technology", "high", True),
    ("Why Hot Spot cameras were eventually phased out of most DRS systems", "The thermal-imaging technology that had a real, quietly-reported failure rate.", "technology", "standard", False),
    ("How ball-tracking predicts where a delivery would have gone after hitting the pad", "The physics modelling behind every LBW review's 'projected path'.", "technology", "standard", True),
    ("The story behind the invention of the pink ball for day-night Test cricket", "Why a completely different ball coating was needed just for visibility under lights.", "technology", "standard", False),
    ("How modern bat sensors are changing the way players train their technique", "Wearable and embedded sensors giving real-time swing and impact data.", "technology", "standard", False),
    ("Why stump cameras and micro-mics changed how fans experience cricket broadcasts", "The tiny hardware inside the stumps that transformed TV coverage entirely.", "technology", "standard", False),

    # -- Iconic matches to watch -----------------------------------------------
    ("The 2005 Ashes series that's considered the greatest Test series ever played", "Five matches, constant momentum swings, and a finish that redefined the rivalry.", "iconic_matches", "high", True),
    ("The 'Miracle of Headingley' 1981 Ashes Test that England had no business winning", "Following on and still somehow pulling off one of cricket's most famous comebacks.", "iconic_matches", "high", True),
    ("The 1999 World Cup semi-final tie between Australia and South Africa", "A run-out in the final over that decided who advanced to the final — pure chaos.", "iconic_matches", "high", True),
    ("The tied Test between Australia and India at Chennai in 1986", "Only the second tied Test in history, and the tension of the final over that created it.", "iconic_matches", "high", True),
    ("India's 2001 Kolkata Test comeback against Australia after following on", "One of the greatest Test comebacks ever, powered by two historic individual innings.", "iconic_matches", "high", True),
    ("The Bodyline series and why it nearly ended cricket relations between two nations", "A bowling tactic so aggressive it triggered a diplomatic incident.", "iconic_matches", "high", True),
    ("The 2016 World T20 final over that Carlos Brathwaite hit for four straight sixes", "One over, one batter, and a finish that's still replayed constantly.", "iconic_matches", "high", True),

    # -- Controversies, factually -----------------------------------------------
    ("The 2018 ball-tampering scandal that shook Australian cricket", "What sandpaper-gate actually involved, and the bans that followed.", "controversies", "high", True),
    ("How match-fixing scandals were actually uncovered in cricket's history", "The investigative work and sting operations that exposed corruption in the sport.", "controversies", "high", True),
    ("The underarm bowling incident that caused a genuine diplomatic dispute", "One legal-but-controversial delivery that strained relations between two countries.", "controversies", "high", True),
    ("Why ball-tampering rules exist, and what's actually allowed vs banned", "Where the legal line sits between polishing a ball and illegally altering it.", "controversies", "standard", True),
    ("The doping cases that have actually affected international cricket", "A sport not usually associated with doping scandals, and the real cases that happened anyway.", "controversies", "standard", False),

    # -- Training, fitness & analytics -----------------------------------------
    ("How modern cricket teams use data analytics to set fielding placements", "The statistical modelling behind where every fielder actually stands.", "training_science", "high", True),
    ("What a professional cricketer's actual training week looks like", "Strength, conditioning, skill drills, and recovery — the real schedule behind match day.", "training_science", "standard", False),
    ("How fast bowlers train to avoid the injuries that end careers early", "Workload management and biomechanics behind protecting a fast bowler's body.", "training_science", "standard", False),
    ("The sports science behind why fast bowlers get injured more than batters", "The repeated stress on the body that makes pace bowling one of sport's toughest jobs.", "training_science", "standard", False),
    ("How a batter actually trains to pick a bowler's variations before the ball is released", "The reaction-time and pattern-recognition training behind reading a delivery early.", "training_science", "high", True),
    ("How nutrition plans changed professional cricket over the last two decades", "From casual diets to precision sports nutrition built around match schedules.", "training_science", "standard", False),
    ("What sports psychologists actually work on with international cricketers", "The mental-game training that's become as structured as physical conditioning.", "training_science", "standard", False),
    ("How analysts break down opposition batters before a series even starts", "The video and data scouting that shapes a bowling attack's entire game plan.", "training_science", "standard", False),

    # -- Women's cricket -----------------------------------------------------------
    ("How the Women's Premier League changed the trajectory of women's cricket in India", "A franchise league that transformed contracts, visibility, and pay almost overnight.", "womens_cricket", "high", True),
    ("Mithali Raj's record as the most prolific run-scorer in women's ODI cricket", "A two-decade career that quietly built one of cricket's biggest batting records.", "womens_cricket", "high", True),
    ("Jhulan Goswami's record as the leading wicket-taker in women's ODI history", "The pace bowler whose longevity and skill reshaped women's fast bowling.", "womens_cricket", "high", True),
    ("How Australia built the most dominant women's cricket team in the world", "The structural investment behind a team that's rarely lost a global final.", "womens_cricket", "standard", False),
    ("The pay gap between men's and women's international cricket, in real numbers", "What match fees and central contracts actually look like on both sides.", "womens_cricket", "high", True),
    ("Smriti Mandhana's rise as one of women's cricket's most watched batters", "The elegant technique and consistency that's made her a genuine box-office name.", "womens_cricket", "standard", True),
    ("How the first Women's T20 World Cup final drew record attendance in 2020", "Over 86,000 fans — a number that reshaped expectations for the women's game.", "womens_cricket", "high", True),
    ("England's 2017 Women's World Cup win and its impact on domestic investment", "A home final win that directly led to professional contracts across the country.", "womens_cricket", "standard", False),
    ("The story of the first fully professional women's domestic cricket contracts", "Which board moved first, and how it changed the conversation everywhere else.", "womens_cricket", "standard", False),
    ("Ellyse Perry's case as the greatest all-rounder in women's cricket history", "A genuine dual international in two sports before focusing entirely on cricket.", "womens_cricket", "standard", True),

    # -- Domestic cricket -----------------------------------------------------------
    ("Why the Ranji Trophy is considered Indian cricket's real proving ground", "The domestic tournament that quietly decides who actually gets picked for India.", "domestic_cricket", "high", True),
    ("How English County Cricket built the technical foundation of Test batting for over a century", "The four-day domestic grind that shaped generations of England's best players.", "domestic_cricket", "standard", False),
    ("The Sheffield Shield's role in producing Australia's Test-ready batters", "Australia's domestic first-class competition, and why it's considered so demanding.", "domestic_cricket", "standard", False),
    ("Why domestic cricket pay is so much lower than international contracts almost everywhere", "The financial reality for players who never quite break into the national team.", "domestic_cricket", "standard", False),
    ("How South Africa's domestic structure keeps producing genuine pace-bowling talent", "The coaching pipeline behind one of the world's most consistent fast-bowling factories.", "domestic_cricket", "standard", False),
    ("The story behind cricket's oldest surviving domestic tournament", "A competition older than most modern sports leagues, still running today.", "domestic_cricket", "standard", False),

    # -- Weather, pitch & conditions ------------------------------------------------
    ("Why home advantage in cricket is bigger than almost any other sport", "Pitch preparation, conditions, and crowd factors that genuinely shift results.", "weather_pitch", "high", True),
    ("How groundstaff actually prepare a pitch differently for spin vs pace", "The real science behind why the same square plays completely differently match to match.", "weather_pitch", "high", True),
    ("Why overcast conditions make fast bowling so much more dangerous", "The swing-bowling science behind cloud cover and why batters dread it.", "weather_pitch", "standard", True),
    ("How the Duckworth-Lewis-Stern method actually recalculates a rain-affected target", "The maths behind cricket's most misunderstood rule, explained simply.", "weather_pitch", "high", True),
    ("Why some grounds are known as 'batting paradises' and others as 'bowler's graveyards'", "The real pitch and altitude factors that make certain venues so lopsided.", "weather_pitch", "standard", True),
    ("How dew affects a day-night match, and why teams fight to bowl first", "The science behind why the toss matters so much more under lights.", "weather_pitch", "standard", True),

    # -- Trivia / did-you-know / quiz --------------------------------------------
    ("The only player ever to be given out 'handled the ball' in a World Cup", "A dismissal so rare that most fans have never actually seen it happen.", "trivia_quiz", "high", True),
    ("The shortest completed Test match in cricket history", "How a Test match can end in barely more than a single day of play.", "trivia_quiz", "high", True),
    ("Why a cricket ball is exactly the weight and size that it is", "The regulations behind cricket's most fundamental piece of equipment.", "trivia_quiz", "standard", True),
    ("The strangest reason a match has ever been called off mid-play", "From swarms of bees to floodlight failures — cricket's oddest interruptions.", "trivia_quiz", "high", True),
    ("The only Test century ever scored entirely in boundaries", "A statistical oddity most fans have never heard was even possible.", "trivia_quiz", "standard", True),
    ("Why cricket is the only major sport where a draw and a tie mean different things", "The subtle rule distinction that trips up even long-time fans.", "trivia_quiz", "high", True),
    ("The real reason cricket matches use the term 'maiden over'", "Where the terminology actually comes from, and why it's stuck for over a century.", "trivia_quiz", "standard", True),
    ("The bizarre origin of the term 'googly' in cricket", "A delivery named after something that has nothing to do with bowling at all.", "trivia_quiz", "standard", True),
    ("Why a cricket pitch is exactly 22 yards long", "The historical reason behind cricket's most fundamental measurement.", "trivia_quiz", "high", True),
    ("The odd history behind why cricket umpires wear white coats", "A uniform tradition with a surprisingly practical original purpose.", "trivia_quiz", "standard", True),
    ("The only instance of a player being timed out in international cricket", "How rare this dismissal actually is, and the real controversy it caused.", "trivia_quiz", "high", True),
    ("Why a 'Nelson' (111) is considered an unlucky score in cricket folklore", "The superstition with no statistical basis that players still take seriously.", "trivia_quiz", "standard", True),
    ("The cricket ball seam's real role in swing bowling, explained simply", "Why six rows of stitching can make a ball move sideways through the air.", "trivia_quiz", "standard", False),
    ("The first-ever cricket match to be broadcast on television", "How far back TV cricket coverage actually goes, and how different it looked.", "trivia_quiz", "standard", False),
    ("Why some batters tap their bat on the crease before every single ball", "The routine and superstition behind cricket's most common pre-ball habit.", "trivia_quiz", "standard", True),

    # -- Commentary & iconic moments --------------------------------------------
    ("The most replayed cricket commentary line in broadcast history", "A single call that's been replayed millions of times across generations of fans.", "commentary", "standard", True),
    ("How cricket commentary teams actually prepare before a broadcast", "The stats, storylines, and pre-match research behind what sounds spontaneous on air.", "commentary", "standard", False),
    ("The story behind cricket's most famous 'silence' after a dismissal", "When commentators chose to say nothing — and why that became iconic too.", "commentary", "standard", False),
    ("Why certain cricket grounds have commentary boxes named after legendary callers", "The tradition of honouring broadcasters the same way as players.", "commentary", "standard", False),
    ("The evolution of cricket commentary from radio-only to today's multi-camera broadcasts", "How the entire viewing experience transformed across a century of the sport.", "commentary", "standard", False),

    # -- Global reach ------------------------------------------------------------
    ("How cricket became one of the most popular sports in the USA's immigrant communities", "The grassroots growth driving cricket's expansion in an unlikely market.", "global_reach", "high", True),
    ("Afghanistan's cricket story — built in refugee camps, now competing with the world's best", "A cricketing rise with almost no formal infrastructure behind it.", "global_reach", "high", True),
    ("How cricket is quietly growing in countries with almost no cricket history", "New markets, grassroots programs, and the ICC's global expansion strategy.", "global_reach", "standard", False),
    ("Why cricket struggles to break into mainstream popularity in continental Europe", "Cultural, scheduling, and infrastructure reasons the sport hasn't taken off there.", "global_reach", "standard", False),
    ("The story of cricket's growth in the Middle East through the UAE as a neutral hub", "How Dubai and Abu Dhabi became unexpected centres of world cricket.", "global_reach", "standard", False),
    ("How Papua New Guinea built a genuine cricket culture in the Pacific Islands", "A cricketing story that most fans have never even heard exists.", "global_reach", "standard", False),
]

# -- Cricket quiz-challenge format: end-of-video paired stat question ----------
# These are pre-built to feed engine.engagement's quiz CTA generator with a
# strong statement + a genuinely related follow-up question, exactly the
# "who holds most wickets... now who holds most man-of-the-match awards"
# pattern the channel is built around. script_generator can still invent its
# own pairing for any topic; these are dependable, pre-vetted starting points.
CRICKET_TOPICS += [
    ("Quiz: who holds the most catches AND the most runs in ODI history — same player?", "State the runs record, then challenge viewers to guess if the same player also holds the catches record.", "trivia_quiz", "high", True),
    ("Quiz: the bowler with most Test wickets vs the bowler with the best strike rate", "Two different 'greatest bowler' arguments — reveal one, ask viewers to name the other.", "trivia_quiz", "high", True),
    ("Quiz: which country has won the most World Cups across all formats combined", "State men's ODI World Cup winners, then ask about the combined men's + women's + T20 tally.", "trivia_quiz", "high", True),
    ("Quiz: name the only player with a Test triple century AND a hundred wickets", "A genuine all-rounder feat almost no one can name from memory.", "trivia_quiz", "high", True),
    ("Quiz: the fastest century in Test cricket vs the fastest in ODI cricket — same player?", "Two speed records from two different formats — ask if one man holds both.", "trivia_quiz", "high", True),
    ("Quiz: which wicketkeeper has the most dismissals in T20 internationals", "State the Test dismissals record, then challenge viewers on the T20I equivalent.", "trivia_quiz", "high", True),
    ("Quiz: who captained more World Cup-winning teams than anyone else in history", "A leadership record that spans multiple tournaments and still surprises people.", "trivia_quiz", "high", True),
    ("Quiz: the youngest Test centurion vs the youngest ODI centurion — same country?", "Two 'youngest ever' records — ask if they belong to the same cricket nation.", "trivia_quiz", "high", True),
]


# ─── OTHER SPORTS (≈15% of the channel) ─────────────────────────────────────
# Featuring current athletes on their own "achieving track", not only history.

OTHER_SPORT_TOPICS = [
    # -- Kabaddi --
    ("The actual rules of kabaddi, explained for someone who's never watched it", "Raids, tackles, and the single-breath 'cant' rule that makes the sport unique.", "kabaddi", "rules", "high", True),
    ("How the Pro Kabaddi League turned a village sport into a national broadcast hit", "The business model that took kabaddi from rural fields to prime-time TV.", "kabaddi", "governance_business", "standard", False),
    ("The raiding technique that makes India's top kabaddi players nearly unstoppable", "The footwork and breath control behind the sport's most valuable skill.", "kabaddi", "training_science", "standard", True),
    ("Why kabaddi is one of the few sports where defense is a full team sport by design", "The 'anti-raid' formations that make stopping a single raider genuinely difficult.", "kabaddi", "rules", "standard", False),
    ("How kabaddi went from an Asian Games sport to chasing Olympic recognition", "The international push behind expanding kabaddi's global reach.", "kabaddi", "global_reach", "standard", False),

    # -- Hockey --
    ("How India won six straight Olympic hockey gold medals, and why that streak ended", "Field hockey's most dominant international run in any sport's history — and its decline.", "hockey", "team_history", "high", True),
    ("The weird offside-style rule in field hockey almost no casual fan understands", "A positional rule that changed dramatically over the sport's history.", "hockey", "rules", "standard", True),
    ("Why field hockey's move to artificial turf changed the entire sport's speed and style", "The surface change that made hockey faster and more technical almost overnight.", "hockey", "technology", "standard", False),
    ("The business struggles behind why hockey lost its spotlight in India to cricket", "Sponsorship, media rights, and youth participation — what actually shifted.", "hockey", "governance_business", "high", True),
    ("Dhyan Chand's legendary goal-scoring record that's still talked about today", "The hockey player once considered among the greatest athletes in any sport.", "hockey", "player_story", "standard", True),
    ("How the Hockey India League tried to replicate the IPL's franchise model", "A league built on cricket's business blueprint — and how it actually fared.", "hockey", "ipl", "standard", False),

    # -- Football --
    ("The strangest rule change in football history that fans forget even happened", "A law that quietly reshaped how the sport is played at every level.", "football", "rules", "standard", True),
    ("Why some of the world's best football leagues are financially underrated outside Europe", "The competitive talent that goes unnoticed because of where it's based.", "football", "governance_business", "standard", False),
    ("How the offside rule in football actually works, explained simply", "The positional rule that causes more confusion than almost any other in sport.", "football", "rules", "standard", True),
    ("The business behind football transfer fees, and how a player's value is actually set", "Scouting, contracts, and release clauses — the real economics of a transfer.", "football", "governance_business", "standard", False),

    # -- Badminton --
    ("How Indian badminton went from a niche sport to producing Olympic medalists", "The structural investment behind India's rise in world badminton.", "badminton", "team_history", "high", True),
    ("PV Sindhu's rise to becoming India's most decorated badminton player", "The training path behind back-to-back world championship medals.", "badminton", "player_story", "high", True),
    ("The physics behind why a badminton shuttlecock behaves so differently from a ball", "Feathers, drag, and deceleration — why the sport's fastest shots still slow down fast.", "badminton", "trivia_quiz", "standard", True),
    ("How the Premier Badminton League tried to build badminton's own franchise economy", "A league modeled on cricket's success, built for a completely different sport.", "badminton", "ipl", "standard", False),

    # -- Athletics / Olympics --
    ("How Neeraj Chopra's javelin throw won India its first Olympic athletics gold", "The training and technique behind a historic individual Olympic medal.", "athletics", "player_story", "high", True),
    ("The science behind why 100m sprint world records keep getting broken by fractions", "Biomechanics, track technology, and training science pushing the limit lower.", "athletics", "training_science", "standard", True),
    ("Why some countries dominate specific Olympic events generation after generation", "The coaching, culture, and investment behind national sporting specialties.", "athletics", "training_science", "standard", False),

    # -- Chess --
    ("How Viswanathan Anand became India's first chess World Champion", "The rise of a player who put Indian chess on the global map decades before it was trendy.", "chess", "player_story", "high", True),
    ("Gukesh's rise as the youngest World Chess Champion in history", "A teenager's path to defeating the world's best at the highest level of the game.", "chess", "current_players", "high", True),
    ("Why chess is now treated as a genuine spectator esport with prize pools to match", "The streaming boom and online platforms that turned chess into mass entertainment.", "chess", "governance_business", "standard", False),
    ("The business behind chess engines, and how they quietly changed how the game is played", "AI analysis tools that reshaped preparation at every serious level of competition.", "chess", "technology", "standard", False),

    # -- Wrestling --
    ("How India's akhara wrestling tradition produced modern Olympic medalists", "The centuries-old training culture behind a surprisingly modern sporting pipeline.", "wrestling", "team_history", "standard", True),
    ("Sakshi Malik and India's first Olympic wrestling medal for a woman", "The breakthrough that opened doors for a generation of Indian women wrestlers.", "wrestling", "player_story", "high", True),
    ("The difference between freestyle and Greco-Roman wrestling, explained simply", "Two Olympic wrestling styles with genuinely different rules most fans conflate.", "wrestling", "rules", "standard", True),

    # -- Boxing --
    ("Mary Kom's rise to become a six-time World Champion boxer", "The training path and comeback story behind one of India's most decorated athletes.", "boxing", "player_story", "high", True),
    ("How amateur Olympic boxing scoring actually works, and why it's controversial", "The judging system that's been criticized and reformed across multiple Olympic cycles.", "boxing", "rules", "standard", True),

    # -- Tennis --
    ("The business behind why tennis players keep almost all their own prize money", "Unlike team sports, how tennis's individual-earnings model actually works.", "tennis", "governance_business", "standard", False),
    ("The physics behind why grass, clay, and hard courts play so differently", "Surface friction and bounce height — why the same shot behaves completely differently.", "tennis", "trivia_quiz", "standard", True),
    ("How India built a strong doubles tennis tradition despite limited singles success", "The specific pathway that produced world-class doubles specialists.", "tennis", "team_history", "standard", False),

    # -- F1 --
    ("The business behind how an F1 team's budget actually gets spent each season", "Car development, driver salaries, and the cost cap reshaping the sport's economics.", "f1", "governance_business", "standard", False),
    ("Why F1's cost cap rule was introduced, and how teams try to work around it", "The financial rule designed to level a historically unequal playing field.", "f1", "rules", "standard", False),

    # -- Esports --
    ("How esports prize pools now rival some of the richest traditional sporting events", "The sponsorship and streaming economy behind competitive gaming's rapid growth.", "esports", "governance_business", "standard", True),
    ("Why esports athletes train almost as intensely as traditional professional athletes", "Reaction time, strategy drilling, and burnout — the real physical side of competitive gaming.", "esports", "training_science", "standard", False),

    # -- Rugby --
    ("The brutal scoring and tackling rules that make rugby so different from football", "A full breakdown of how tries, conversions, and tackling actually work.", "rugby", "rules", "standard", True),
    ("Why rugby sevens became an Olympic sport when traditional rugby hasn't", "The format change that made a niche sport suddenly Olympic-friendly.", "rugby", "governance_business", "standard", False),

    # -- Cross-sport business & underrated-sport spotlight --
    ("Why some of the most physically demanding sports get the least sponsorship money", "The gap between athletic difficulty and commercial visibility across different sports.", "cross_sport", "governance_business", "high", True),
    ("The hidden business empires built entirely around under-the-radar sports", "Equipment, coaching academies, and media rights in sports most fans overlook.", "cross_sport", "governance_business", "standard", False),
    ("Why some Olympic sports get almost zero mainstream coverage despite huge global participation", "The broadcast and sponsorship economics that decide which sports get airtime.", "cross_sport", "governance_business", "high", True),
    ("How athlete pay compares across different sports for a similar level of dominance", "A side-by-side look at how unevenly sport rewards its very best performers.", "cross_sport", "governance_business", "high", True),
    ("The strangest rule that exists in a sport most people have never watched", "A deep cut into an obscure sport's rulebook that turns out to be genuinely fascinating.", "cross_sport", "rules", "high", True),
]


def _norm_cricket(row):
    name, desc, category, tier, quiz = row
    return {
        "name": name, "description": desc, "sport": "cricket", "sub_sport": None,
        "category": category, "engagement_tier": tier, "quiz_friendly": quiz,
        "archetype": archetype_for(category),
    }


def _norm_other(row):
    name, desc, sub_sport, category, tier, quiz = row
    return {
        "name": name, "description": desc, "sport": "other_sport", "sub_sport": sub_sport,
        "category": category, "engagement_tier": tier, "quiz_friendly": quiz,
        "archetype": archetype_for(category),
    }


def all_topics() -> list:
    """Every catalog topic as a flat list of dicts, ready for seeding."""
    return [_norm_cricket(r) for r in CRICKET_TOPICS] + [_norm_other(r) for r in OTHER_SPORT_TOPICS]


def stats() -> dict:
    topics = all_topics()
    cricket = [t for t in topics if t["sport"] == "cricket"]
    other = [t for t in topics if t["sport"] == "other_sport"]
    return {
        "total": len(topics),
        "cricket": len(cricket),
        "other_sport": len(other),
        "cricket_pct": round(100 * len(cricket) / max(len(topics), 1), 1),
        "by_category": {c: len([t for t in topics if t["category"] == c]) for c in CATEGORIES},
    }


def seed_examples(sport: str = None, n: int = 25) -> list:
    """A handful of catalog entries, for handing to topic_synthesizer as
    'examples of the domain's shape' — same role personas.py's seed_topics
    plays for every other persona in this project."""
    import random
    pool = all_topics()
    if sport:
        pool = [t for t in pool if t["sport"] == sport]
    random.shuffle(pool)
    return [t["name"] for t in pool[:n]]


if __name__ == "__main__":
    import json
    print(json.dumps(stats(), indent=2))
