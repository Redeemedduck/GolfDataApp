Podcast rec   
  
/**  
  
- ============================================================  
- “Duck’s AI Picks” — A curated recommendation engine for Aaron  
- ============================================================  
-   
- PURPOSE:  
- A beautifully designed, filterable PWA that showcases AI-related  
- podcasts, influencers, newsletters, YouTube channels, and tools.  
- Built as a personalized gift from Duck to Aaron.  
-   
- KEY FEATURES:  
- 1. CLAUDE AI INTEGRATION — Paste a link or describe a source in  
- plain text, and Claude will extract structured recommendation  
- data (name, type, author, description, tags, URL).  
- 1. HIDE/REMOVE — Any card can be hidden from Aaron’s view. Hidden  
- cards are accessible in a management panel so you can restore  
- them later.  
- 1. SEARCH & FILTER — Full-text search, category pills, tag filters,  
- and a favorites system.  
-   
- HOW TO CUSTOMIZE:  
- - Edit the INITIAL_RECOMMENDATIONS array below to change defaults  
- - Use the “Add with AI” panel in the app to add new picks live  
- - Use the hide button (✕) on any card to remove it temporarily  
- ============================================================  
  */  
  
import { useState, useMemo, useEffect, useCallback } from “react”;  
  
/* ──────────────────────────────────────────────────────────────  
SECTION 1: INITIAL RECOMMENDATION DATA  
  
This is the starting data set. New recommendations added via  
the Claude AI panel are appended to state at runtime.  
  
Fields:  
  
- id:          Unique number (auto-incremented for new entries)  
- name:        Title displayed on the card  
- type:        “Podcast”, “YouTube”, “Newsletter”, “Influencer”,  
- ```  
           "Tool", or "Blog"  
  ```  
- author:      Creator/host name  
- description: 1-2 sentence blurb shown on the card  
- tags:        Array of tag strings for filtering  
- url:         Link to the resource  
- duck_note:   Optional personal note from Duck to Aaron  
- hidden:      Boolean — if true, card is hidden from main view  
  ────────────────────────────────────────────────────────────── */  
  
const INITIAL_RECOMMENDATIONS = [  
{  
id: 1,  
name: “Latent Space”,  
type: “Podcast”,  
author: “Swyx & Alessio”,  
description:  
“Deep technical conversations with AI engineers and researchers. Consistently one of the best sources for understanding what’s actually happening under the hood.”,  
tags: [“Technical”, “Engineering”, “Interviews”, “Deep Dives”],  
url: “https://www.latent.space/podcast”,  
duck_note: “Start with their year-in-review episodes — incredible overviews.”,  
hidden: false,  
},  
{  
id: 2,  
name: “The Cognitive Revolution”,  
type: “Podcast”,  
author: “Nathan Labenz”,  
description:  
“Wide-ranging interviews covering AI safety, capabilities, and the business side. Nathan asks the questions most people are too afraid to ask.”,  
tags: [“Business”, “Safety”, “Interviews”, “Strategy”],  
url: “https://www.cognitiverevolution.ai/”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 3,  
name: “Practical AI”,  
type: “Podcast”,  
author: “Changelog Media”,  
description:  
“Focused on making AI approachable and practical. Great for understanding how real teams implement AI in production.”,  
tags: [“Beginner-Friendly”, “Engineering”, “Practical”],  
url: “https://changelog.com/practicalai”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 4,  
name: “Last Week in AI”,  
type: “Podcast”,  
author: “Skynet Today”,  
description:  
“Weekly news roundup that cuts through the noise. Perfect for staying current without doomscrolling Twitter.”,  
tags: [“News”, “Weekly Roundup”, “Beginner-Friendly”],  
url: “https://lastweekinai.com/”,  
duck_note: “Best way to stay current if you only have 30 min/week.”,  
hidden: false,  
},  
{  
id: 5,  
name: “AI Explained”,  
type: “YouTube”,  
author: “Philip”,  
description:  
“Thoughtful, well-researched breakdowns of AI papers and developments. Avoids hype and focuses on what actually matters.”,  
tags: [“Technical”, “Research”, “Deep Dives”, “Explainers”],  
url: “https://www.youtube.com/@aiexplained-official”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 6,  
name: “Matt Wolfe”,  
type: “YouTube”,  
author: “Matt Wolfe”,  
description:  
“Weekly AI tool roundups and tutorials. Great at demoing new tools and showing what’s actually useful vs. just hype.”,  
tags: [“Tools”, “News”, “Beginner-Friendly”, “Weekly Roundup”],  
url: “https://www.youtube.com/@maboroshi”,  
duck_note: “His Future Tools website is also a goldmine.”,  
hidden: false,  
},  
{  
id: 7,  
name: “Two Minute Papers”,  
type: “YouTube”,  
author: “Károly Zsolnai-Fehér”,  
description:  
“Bite-sized, enthusiastic breakdowns of cutting-edge research papers. ‘What a time to be alive!’ energy in every episode.”,  
tags: [“Research”, “Beginner-Friendly”, “Explainers”],  
url: “https://www.youtube.com/@TwoMinutePapers”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 8,  
name: “Ben’s Bites”,  
type: “Newsletter”,  
author: “Ben Tossell”,  
description:  
“Daily AI newsletter that’s concise and actually readable. Curated links with just enough context to know if you should click.”,  
tags: [“News”, “Daily”, “Business”, “Beginner-Friendly”],  
url: “https://bensbites.beehiiv.com/”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 9,  
name: “The Neuron”,  
type: “Newsletter”,  
author: “Pete & Noah”,  
description:  
“AI news delivered with personality and humor. Makes dense topics feel accessible without dumbing them down.”,  
tags: [“News”, “Daily”, “Beginner-Friendly”],  
url: “https://www.theneurondaily.com/”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 10,  
name: “Simon Willison’s Weblog”,  
type: “Blog”,  
author: “Simon Willison”,  
description:  
“One of the most thoughtful voices in AI. Simon builds things, writes about what he learns, and shares with radical transparency.”,  
tags: [“Technical”, “Engineering”, “Practical”, “Deep Dives”],  
url: “https://simonwillison.net/”,  
duck_note: “One of the best follows in all of tech right now.”,  
hidden: false,  
},  
{  
id: 11,  
name: “Ethan Mollick”,  
type: “Influencer”,  
author: “Wharton Professor”,  
description:  
“Bridges academic rigor with practical AI usage. His experiments with AI in education and business are must-reads.”,  
tags: [“Business”, “Strategy”, “Research”, “Practical”],  
url: “https://www.oneusefulthing.org/”,  
duck_note: “His book ‘Co-Intelligence’ is a great starting point.”,  
hidden: false,  
},  
{  
id: 12,  
name: “Andrej Karpathy”,  
type: “Influencer”,  
author: “Former Tesla AI / OpenAI”,  
description:  
“Legendary AI researcher who makes complex neural network concepts accessible. His YouTube lectures are a masterclass.”,  
tags: [“Technical”, “Research”, “Deep Dives”, “Explainers”],  
url: “https://karpathy.ai/”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 13,  
name: “Anthropic Research Blog”,  
type: “Blog”,  
author: “Anthropic”,  
description:  
“Technical deep dives into AI safety, interpretability, and the thinking behind Claude. Unmatched transparency from an AI lab.”,  
tags: [“Safety”, “Research”, “Technical”, “Deep Dives”],  
url: “https://www.anthropic.com/research”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 14,  
name: “The AI Daily Brief”,  
type: “Podcast”,  
author: “Nathaniel Whittemore”,  
description:  
“Short daily episodes covering the most important AI story of the day. Perfect for commutes or quick catch-ups.”,  
tags: [“News”, “Daily”, “Beginner-Friendly”, “Business”],  
url: “https://podcasts.apple.com/us/podcast/the-ai-daily-brief/id1680633614”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 15,  
name: “Cursor / AI Coding Tools”,  
type: “Tool”,  
author: “Various”,  
description:  
“AI-powered code editors and assistants that are changing how software gets built. Worth exploring even if you’re not a daily coder.”,  
tags: [“Tools”, “Engineering”, “Practical”],  
url: “https://cursor.sh/”,  
duck_note: “This is the stuff I’ve been building with — game changer.”,  
hidden: false,  
},  
{  
id: 16,  
name: “No Priors”,  
type: “Podcast”,  
author: “Sarah Guo & Elad Gil”,  
description:  
“Top-tier VC perspective on AI startups and trends. Guests are consistently founders and researchers at the frontier.”,  
tags: [“Business”, “Strategy”, “Interviews”, “Deep Dives”],  
url: “https://www.nopriors.ai/”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 17,  
name: “Hard Fork”,  
type: “Podcast”,  
author: “Kevin Roose & Casey Newton”,  
description:  
“The New York Times’ flagship tech podcast. Kevin and Casey bring sharp, funny, and deeply informed takes on AI, social media, and the forces reshaping technology and culture.”,  
tags: [“News”, “Business”, “Beginner-Friendly”, “Deep Dives”],  
url: “https://www.nytimes.com/column/hard-fork”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 18,  
name: “Behind the Craft”,  
type: “Podcast”,  
author: “Peter Yang”,  
description:  
“Expert interviews and practical guides for product leaders and creators looking to level up fast. Peter digs into the craft behind building great products.”,  
tags: [“Business”, “Interviews”, “Strategy”, “Practical”],  
url: “https://open.spotify.com/show/3DpAbiHuflIjaQFjbHbQR9”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 19,  
name: “How I AI”,  
type: “Podcast”,  
author: “Claire Vo (ChatPRD)”,  
description:  
“Deep-dive conversations with practitioners who are actually building with AI day to day. Covers real workflows, custom tooling, and practical strategies for integrating AI into development and product work.”,  
tags: [“Technical”, “Engineering”, “Interviews”, “Practical”],  
url: “https://open.spotify.com/show/4aRP2XSavdtrLG5FZoonOK”,  
duck_note: “”,  
hidden: false,  
},  
{  
id: 20,  
name: “Lenny’s Podcast”,  
type: “Podcast”,  
author: “Lenny Rachitsky”,  
description:  
“One of the most respected voices in product and growth. Lenny interviews world-class product leaders with a focus on concrete, tactical advice — and increasingly covers how AI is reshaping product work.”,  
tags: [“Business”, “Strategy”, “Interviews”, “Practical”],  
url: “https://www.lennysnewsletter.com/podcast”,  
duck_note: “His newsletter is equally great. Also check out Lennybot — he built an AI version of himself.”,  
hidden: false,  
},  
{  
id: 21,  
name: “Dwarkesh Podcast”,  
type: “Podcast”,  
author: “Dwarkesh Patel”,  
description:  
“Deeply researched, intellectually rigorous long-form interviews with the biggest names in AI — Dario Amodei, Ilya Sutskever, Mark Zuckerberg, Satya Nadella. The Economist called him ‘Silicon Valley’s favourite podcaster.’”,  
tags: [“Deep Dives”, “Research”, “Interviews”, “Strategy”],  
url: “https://www.dwarkesh.com/podcast”,  
duck_note: “His book ‘The Scaling Era’ is essentially a curated best-of from the podcast. Incredible resource.”,  
hidden: false,  
},  
{  
id: 22,  
name: “Fireship”,  
type: “YouTube”,  
author: “Jeff Delaney”,  
description:  
“Punchy, fast-paced explainers and news recaps for developers. His ‘100 seconds of X’ format is legendary — perfect for getting up to speed on AI tools and concepts without the fluff.”,  
tags: [“News”, “Engineering”, “Beginner-Friendly”, “Explainers”],  
url: “https://www.youtube.com/@Fireship”,  
duck_note: “The weekly ‘Code Report’ episodes are the best 5-minute AI/dev news roundup out there.”,  
hidden: false,  
},  
{  
id: 23,  
name: “ThursdAI”,  
type: “Podcast”,  
author: “Alex Volkov”,  
description:  
“Weekly AI news roundup from the builder community. Alex gathers practitioners and researchers every Thursday to break down the biggest developments — great energy, great signal-to-noise ratio.”,  
tags: [“News”, “Weekly Roundup”, “Engineering”, “Practical”],  
url: “https://thursdai.news/”,  
duck_note: “”,  
hidden: false,  
},  
];  
  
/* ──────────────────────────────────────────────────────────────  
SECTION 2: CATEGORY CONFIGURATION  
  
Controls the filter pill options shown in the UI.  
The “icon” is an emoji displayed next to each category name.  
────────────────────────────────────────────────────────────── */  
  
const CATEGORIES = [  
{ label: “All”, icon: “✦” },  
{ label: “Podcast”, icon: “🎙” },  
{ label: “YouTube”, icon: “▶” },  
{ label: “Newsletter”, icon: “📬” },  
{ label: “Blog”, icon: “✍” },  
{ label: “Influencer”, icon: “👤” },  
{ label: “Tool”, icon: “⚡” },  
];  
  
/* ──────────────────────────────────────────────────────────────  
SECTION 3: DESIGN TOKENS  
  
Central style configuration. Edit these values to change the  
entire look and feel of the app — colors, fonts, radii, etc.  
Referenced throughout all component styles below.  
────────────────────────────────────────────────────────────── */  
  
const T = {  
fontSerif: “‘Newsreader’, ‘Georgia’, serif”,  
fontSans: “‘DM Sans’, ‘Helvetica Neue’, sans-serif”,  
bgCream: “#faf8f5”,  
ink: “#2c2420”,  
inkLight: “#7a6e62”,  
accent: “#c9553a”,  
accentHover: “#a8432e”,  
cardBg: “#ffffff”,  
cardBorder: “#ebe6df”,  
radius: 14,  
radiusPill: 100,  
};  
  
/* ──────────────────────────────────────────────────────────────  
SECTION 4: CLAUDE API HELPER  
  
Sends user input (a link, episode title, or plain text  
description) to the Anthropic API. Claude extracts structured  
recommendation data and returns JSON we can add to the list.  
  
The system prompt constrains Claude to:  
  
- Identify the source name, host/creator, and type  
- Write a concise 1-2 sentence description  
- Select relevant tags from a known set  
- Extract a URL if one was provided  
- Return ONLY valid JSON with no other text  
  ────────────────────────────────────────────────────────────── */  
  
async function extractRecommendation(userInput) {  
/**  
  
- We combine the system instructions and user input into a single  
- user message. This is the most reliable approach in the artifact  
- environment where the API key is handled automatically.  
  */  
  const prompt = `You are a recommendation data extractor for an AI media guide.  
  
I will give you a link, episode title, podcast name, YouTube channel, newsletter, blog, tool, or a plain text description of an AI-related media source.  
  
Your job: extract structured data and return ONLY valid JSON. No markdown, no backticks, no preamble, no explanation — just the raw JSON object.  
  
Return this exact structure:  
{“name”:“Name of the show/channel/newsletter/blog/tool”,“type”:“Podcast”,“author”:“Creator or host”,“description”:“1-2 sentence description in a warm editorial tone.”,“tags”:[“tag1”,“tag2”],“url”:“https://…”}  
  
Rules:  
  
- “type” must be one of: Podcast, YouTube, Newsletter, Blog, Influencer, Tool  
- “tags” must use ONLY these options: Technical, Engineering, Interviews, Deep Dives, Business, Safety, Strategy, Beginner-Friendly, Practical, News, Weekly Roundup, Daily, Research, Explainers, Tools  
- Pick 2-4 tags that best fit  
- If the input is a URL, identify the source from the URL structure and your knowledge  
- For podcast episode links, identify the PARENT SHOW not the individual episode  
- If you don’t know the URL, set it to “”  
  
Here is the input to extract from:  
  
${userInput}`;  
  
/**  
  
- Call the Anthropic Messages API.  
- No API key is needed — the artifact environment handles auth.  
  */  
  const response = await fetch(“https://api.anthropic.com/v1/messages”, {  
  method: “POST”,  
  headers: {  
  “Content-Type”: “application/json”,  
  },  
  body: JSON.stringify({  
  model: “claude-sonnet-4-20250514”,  
  max_tokens: 1000,  
  messages: [{ role: “user”, content: prompt }],  
  }),  
  });  
  
/**  
  
- Check if the HTTP request itself failed (network error,  
- server error, auth issue, etc.) before trying to parse.  
  */  
  if (!response.ok) {  
  const errorText = await response.text().catch(() => “Unknown error”);  
  throw new Error(`API returned status ${response.status}: ${errorText}`);  
  }  
  
const data = await response.json();  
  
/**  
  
- Validate the response has the expected structure.  
- The API returns { content: [{ type: “text”, text: “…” }] }  
  */  
  if (!data.content || !Array.isArray(data.content) || data.content.length === 0) {  
  throw new Error(“API returned an unexpected response structure”);  
  }  
  
/**  
  
- Extract text from all content blocks, strip any accidental  
- markdown code fences or whitespace, then parse as JSON.  
  */  
  const rawText = data.content  
  .filter((block) => block.type === “text”)  
  .map((block) => block.text)  
  .join(””);  
  
const cleanText = rawText  
.replace(/`json\s*/gi, "") .replace(/`\s*/g, “”)  
.trim();  
  
/**  
  
- Try to parse the cleaned text as JSON. If it fails,  
- try to find a JSON object within the text using regex  
- as a fallback (in case Claude added some preamble).  
  */  
  try {  
  return JSON.parse(cleanText);  
  } catch (parseError) {  
  // Fallback: try to find a JSON object in the response  
  const jsonMatch = cleanText.match(/{[\s\S]*}/);  
  if (jsonMatch) {  
  return JSON.parse(jsonMatch[0]);  
  }  
  throw new Error(“Could not parse a valid recommendation from Claude’s response”);  
  }  
  }  
  
/* ──────────────────────────────────────────────────────────────  
SECTION 5: MAIN APP COMPONENT  
  
Root React component. Manages all app state and composes  
the full page layout from child components.  
────────────────────────────────────────────────────────────── */  
  
export default function App() {  
// — Core data: all recommendations (initial + AI-added) —  
const [recs, setRecs] = useState(INITIAL_RECOMMENDATIONS);  
  
// — Filter state —  
const [search, setSearch] = useState(””);  
const [activeCategory, setActiveCategory] = useState(“All”);  
const [activeTags, setActiveTags] = useState([]);  
  
// — Favorites —  
const [favorites, setFavorites] = useState(new Set());  
const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);  
  
// — UI panel toggles —  
const [addPanelOpen, setAddPanelOpen] = useState(false);  
const [hiddenPanelOpen, setHiddenPanelOpen] = useState(false);  
  
// — AI input state —  
const [aiInput, setAiInput] = useState(””);  
const [aiLoading, setAiLoading] = useState(false);  
const [aiError, setAiError] = useState(””);  
const [aiSuccess, setAiSuccess] = useState(””);  
  
// — Animation trigger —  
const [animKey, setAnimKey] = useState(0);  
  
// Dynamically extract all unique tags from current data  
const allTags = useMemo(  
() => […new Set(recs.flatMap((r) => r.tags))].sort(),  
[recs]  
);  
  
// Count hidden items for badge display  
const hiddenCount = useMemo(() => recs.filter((r) => r.hidden).length, [recs]);  
  
/* ── Event Handlers ── */  
  
const toggleTag = (tag) => {  
setActiveTags((prev) =>  
prev.includes(tag) ? prev.filter((t) => t !== tag) : […prev, tag]  
);  
};  
  
const toggleFavorite = (id) => {  
setFavorites((prev) => {  
const next = new Set(prev);  
next.has(id) ? next.delete(id) : next.add(id);  
return next;  
});  
};  
  
/** Hide a card from main view (recoverable) */  
const hideRec = (id) => {  
setRecs((prev) =>  
prev.map((r) => (r.id === id ? { …r, hidden: true } : r))  
);  
};  
  
/** Restore a hidden card back to main view */  
const restoreRec = (id) => {  
setRecs((prev) =>  
prev.map((r) => (r.id === id ? { …r, hidden: false } : r))  
);  
};  
  
/** Permanently delete a card (not recoverable) */  
const permanentlyRemove = (id) => {  
setRecs((prev) => prev.filter((r) => r.id !== id));  
setFavorites((prev) => {  
const next = new Set(prev);  
next.delete(id);  
return next;  
});  
};  
  
/**  
  
- AI SUBMIT: Sends input to Claude, parses the response,  
- and adds the extracted recommendation to the list.  
  */  
  const handleAiSubmit = useCallback(async () => {  
  if (!aiInput.trim() || aiLoading) return;  
  
```  
setAiLoading(true);  
setAiError("");  
setAiSuccess("");  
  
try {  
  const extracted = await extractRecommendation(aiInput);  
  
  const newRec = {  
    id: Date.now(),  
    name: extracted.name || "Unknown Source",  
    type: extracted.type || "Blog",  
    author: extracted.author || "Unknown",  
    description: extracted.description || "",  
    tags: extracted.tags || [],  
    url: extracted.url || "",  
    duck_note: "",  
    hidden: false,  
  };  
  
  // Prepend so new additions appear first  
  setRecs((prev) => [newRec, ...prev]);  
  setAiSuccess(`Added "${newRec.name}" by ${newRec.author}`);  
  setAiInput("");  
  setTimeout(() => setAiSuccess(""), 4000);  
} catch (err) {  
  setAiError(  
    `Couldn't extract that one — ${err.message || "unknown error"}. Try pasting a direct URL or adding more detail.`  
  );  
} finally {  
  setAiLoading(false);  
}  
```  
  
}, [aiInput, aiLoading]);  
  
/* ── Filtering Logic ── */  
  
const filtered = useMemo(() => {  
return recs.filter((rec) => {  
if (rec.hidden) return false;  
if (showFavoritesOnly && !favorites.has(rec.id)) return false;  
if (activeCategory !== “All” && rec.type !== activeCategory) return false;  
if (activeTags.length > 0 && !activeTags.every((t) => rec.tags.includes(t)))  
return false;  
if (search.trim()) {  
const q = search.toLowerCase();  
const haystack =  
`${rec.name} ${rec.author} ${rec.description} ${rec.tags.join(" ")}`.toLowerCase();  
if (!haystack.includes(q)) return false;  
}  
return true;  
});  
}, [recs, search, activeCategory, activeTags, showFavoritesOnly, favorites]);  
  
useEffect(() => {  
setAnimKey((k) => k + 1);  
}, [filtered.length, activeCategory, search, activeTags, showFavoritesOnly]);  
  
/* ── Render ── */  
  
return (  
<div style={styles.page}>  
<div style={styles.bgDecor} />  
  
```  
  {/* === HEADER === */}  
  <header style={styles.header}>  
    <div style={styles.headerInner}>  
      <span style={styles.eyebrow}>Curated for Aaron</span>  
      <h1 style={styles.title}>  
        The AI<br />  
        <span style={styles.titleAccent}>Field Guide</span>  
      </h1>  
      <p style={styles.subtitle}>  
        A hand-picked collection of podcasts, channels, newsletters, and  
        people worth following in the AI space — from one curious nerd to  
        another.  
      </p>  
      <div style={styles.noteBadge}>  
        <span style={styles.noteBadgeIcon}>💌</span>  
        <span style={styles.noteBadgeText}>  
          Picks marked with a <span style={{ color: T.accent }}>★</span>{" "}  
          have a personal note. Click to reveal it.  
        </span>  
      </div>  
    </div>  
  </header>  
  
  {/* === MAIN === */}  
  <main style={styles.main}>  
  
    {/* ── Admin Toolbar ── */}  
    <div style={styles.adminBar}>  
      <button  
        onClick={() => { setAddPanelOpen(!addPanelOpen); setHiddenPanelOpen(false); }}  
        style={{ ...styles.adminBtn, ...(addPanelOpen ? styles.adminBtnActive : {}) }}  
      >  
        <span style={{ fontSize: 16 }}>✦</span> Add with AI  
      </button>  
      <button  
        onClick={() => { setHiddenPanelOpen(!hiddenPanelOpen); setAddPanelOpen(false); }}  
        style={{ ...styles.adminBtn, ...(hiddenPanelOpen ? styles.adminBtnActive : {}) }}  
      >  
        <span style={{ fontSize: 14 }}>🗂</span> Hidden{hiddenCount > 0 ? ` (${hiddenCount})` : ""}  
      </button>  
    </div>  
  
    {/* ── Add with AI Panel ──  
        Expandable panel for pasting links or describing sources.  
        Claude processes the input and creates a structured card. */}  
    {addPanelOpen && (  
      <div style={styles.aiPanel}>  
        <h3 style={styles.aiPanelTitle}>Add a Recommendation with Claude</h3>  
        <p style={styles.aiPanelDesc}>  
          Paste a link to a podcast episode, YouTube channel, newsletter, blog  
          post, or just describe it in your own words. Claude will extract the  
          details and create a card.  
        </p>  
  
        <textarea  
          value={aiInput}  
          onChange={(e) => setAiInput(e.target.value)}  
          placeholder={`Examples:\n• https://youtube.com/@3blue1brown\n• "Lex Fridman podcast - great long-form AI interviews"\n• https://open.spotify.com/show/2MAi0BvDc6GTFvKFPXnkCL`}  
          style={styles.aiTextarea}  
          rows={4}  
          onKeyDown={(e) => {  
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleAiSubmit();  
          }}  
        />  
  
        <div style={styles.aiActions}>  
          <button  
            onClick={handleAiSubmit}  
            disabled={aiLoading || !aiInput.trim()}  
            style={{  
              ...styles.aiSubmitBtn,  
              ...(aiLoading || !aiInput.trim() ? styles.aiSubmitBtnDisabled : {}),  
            }}  
          >  
            {aiLoading ? <span style={styles.spinner}>⟳</span> : "Extract & Add"}  
          </button>  
          <span style={styles.aiHint}>⌘ + Enter to submit</span>  
        </div>  
  
        {aiSuccess && (  
          <div style={styles.aiFeedback}>  
            <span style={{ marginRight: 6 }}>✓</span> {aiSuccess}  
          </div>  
        )}  
        {aiError && (  
          <div style={styles.aiFeedbackError}>  
            <span style={{ marginRight: 6 }}>⚠</span> {aiError}  
          </div>  
        )}  
      </div>  
    )}  
  
    {/* ── Hidden Items Panel ──  
        Shows all hidden cards with restore/delete options. */}  
    {hiddenPanelOpen && (  
      <div style={styles.hiddenPanel}>  
        <h3 style={styles.aiPanelTitle}>Hidden Picks</h3>  
        {hiddenCount === 0 ? (  
          <p style={styles.hiddenEmpty}>  
            No hidden picks. Use the <strong>✕</strong> button on any card to hide it.  
          </p>  
        ) : (  
          <div style={styles.hiddenList}>  
            {recs.filter((r) => r.hidden).map((rec) => (  
              <div key={rec.id} style={styles.hiddenItem}>  
                <div style={styles.hiddenItemInfo}>  
                  <span style={styles.hiddenItemType}>{rec.type}</span>  
                  <span style={styles.hiddenItemName}>{rec.name}</span>  
                  <span style={styles.hiddenItemAuthor}>by {rec.author}</span>  
                </div>  
                <div style={styles.hiddenItemActions}>  
                  <button onClick={() => restoreRec(rec.id)} style={styles.restoreBtn}>  
                    Restore  
                  </button>  
                  <button onClick={() => permanentlyRemove(rec.id)} style={styles.deleteBtn}>  
                    Delete  
                  </button>  
                </div>  
              </div>  
            ))}  
          </div>  
        )}  
      </div>  
    )}  
  
    {/* ── Search Bar ── */}  
    <div style={styles.searchWrap}>  
      <span style={styles.searchIcon}>⌕</span>  
      <input  
        type="text"  
        placeholder="Search by name, topic, or keyword..."  
        value={search}  
        onChange={(e) => setSearch(e.target.value)}  
        style={styles.searchInput}  
      />  
      {search && (  
        <button onClick={() => setSearch("")} style={styles.clearBtn}>✕</button>  
      )}  
    </div>  
  
    {/* ── Category Pills ── */}  
    <div style={styles.filterRow}>  
      {CATEGORIES.map((cat) => (  
        <button  
          key={cat.label}  
          onClick={() => setActiveCategory(cat.label)}  
          style={{  
            ...styles.categoryPill,  
            ...(activeCategory === cat.label ? styles.categoryPillActive : {}),  
          }}  
        >  
          <span style={{ marginRight: 6 }}>{cat.icon}</span>  
          {cat.label}  
        </button>  
      ))}  
    </div>  
  
    {/* ── Tag Pills ── */}  
    <div style={styles.tagRow}>  
      {allTags.map((tag) => (  
        <button  
          key={tag}  
          onClick={() => toggleTag(tag)}  
          style={{  
            ...styles.tagPill,  
            ...(activeTags.includes(tag) ? styles.tagPillActive : {}),  
          }}  
        >  
          {tag}  
        </button>  
      ))}  
    </div>  
  
    {/* ── Results Count + Favorites ── */}  
    <div style={styles.resultsBar}>  
      <span style={styles.resultsCount}>  
        {filtered.length} {filtered.length === 1 ? "pick" : "picks"}  
        {activeTags.length > 0 && (  
          <button onClick={() => setActiveTags([])} style={styles.clearTags}>  
            Clear tags  
          </button>  
        )}  
      </span>  
      <button  
        onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}  
        style={{  
          ...styles.favToggle,  
          ...(showFavoritesOnly ? styles.favToggleActive : {}),  
        }}  
      >  
        {showFavoritesOnly ? "♥ Favorites" : "♡ Show Favorites"}  
      </button>  
    </div>  
  
    {/* ── Card Grid ── */}  
    <div style={styles.grid} key={animKey}>  
      {filtered.map((rec, i) => (  
        <RecCard  
          key={rec.id}  
          rec={rec}  
          index={i}  
          isFav={favorites.has(rec.id)}  
          onToggleFav={() => toggleFavorite(rec.id)}  
          onHide={() => hideRec(rec.id)}  
        />  
      ))}  
      {filtered.length === 0 && (  
        <div style={styles.emptyState}>  
          <span style={{ fontSize: 48, marginBottom: 12 }}>🔍</span>  
          <p style={{ margin: 0, fontSize: 17, fontWeight: 500 }}>  
            No picks match your filters  
          </p>  
          <p style={{ margin: "8px 0 0", opacity: 0.6, fontSize: 14 }}>  
            Try broadening your search or clearing some tags.  
          </p>  
        </div>  
      )}  
    </div>  
  </main>  
  
  {/* === FOOTER === */}  
  <footer style={styles.footer}>  
    <p style={styles.footerText}>  
      Built with care by Duck · Powered by curiosity & Claude  
    </p>  
    <p style={styles.footerSub}>  
      Add to your home screen for the full experience · AI-powered recommendations via Claude  
    </p>  
  </footer>  
  
  {/* === GLOBAL CSS === */}  
  <style>{`  
    @import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500;0,6..72,600;0,6..72,700;1,6..72,400&family=DM+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap');  
  
    @keyframes cardIn {  
      from { opacity: 0; transform: translateY(24px); }  
      to   { opacity: 1; transform: translateY(0); }  
    }  
    @keyframes softPulse {  
      0%, 100% { opacity: 0.7; }  
      50%      { opacity: 1; }  
    }  
    @keyframes spin {  
      from { transform: rotate(0deg); }  
      to   { transform: rotate(360deg); }  
    }  
    @keyframes slideDown {  
      from { opacity: 0; transform: translateY(-12px); }  
      to   { opacity: 1; transform: translateY(0); }  
    }  
    @keyframes feedbackIn {  
      from { opacity: 0; transform: translateY(-8px); }  
      to   { opacity: 1; transform: translateY(0); }  
    }  
  
    *:focus-visible {  
      outline: 2px solid #c9553a;  
      outline-offset: 2px;  
    }  
    input::placeholder, textarea::placeholder {  
      font-style: italic;  
      color: #a09888;  
    }  
    .rec-card:hover {  
      transform: translateY(-4px) !important;  
      box-shadow: 0 12px 40px rgba(60,40,20,0.12) !important;  
    }  
    .hide-btn {  
      opacity: 0.4;  
      transition: opacity 0.2s;  
    }  
    .hide-btn:hover {  
      opacity: 1 !important;  
      color: #c9553a !important;  
    }  
    @media (max-width: 720px) {  
      .card-grid {  
        grid-template-columns: 1fr !important;  
      }  
    }  
  `}</style>  
</div>  
```  
  
);  
}  
  
/* ──────────────────────────────────────────────────────────────  
SECTION 6: RECOMMENDATION CARD COMPONENT  
  
Renders a single card with:  
  
- Type badge (color-coded by category)  
- Hide button (✕, visible on hover)  
- Favorite toggle (♡/♥)  
- Name, author, description  
- Expandable “Duck’s note” if present  
- Tag pills  
- Visit link  
  ────────────────────────────────────────────────────────────── */  
  
function RecCard({ rec, index, isFav, onToggleFav, onHide }) {  
const [showNote, setShowNote] = useState(false);  
  
const typeColor = {  
Podcast: [”#fdf0e9”, “#c9553a”],  
YouTube: [”#fce8e8”, “#b83232”],  
Newsletter: [”#e8f0f8”, “#2a5a8a”],  
Blog: [”#eef5ec”, “#3a7a3a”],  
Influencer: [”#f3edf8”, “#6a3a8a”],  
Tool: [”#fef9e8”, “#8a7a2a”],  
};  
  
const [bgColor, textColor] = typeColor[rec.type] || [”#f0f0f0”, “#555”];  
  
return (  
<div  
className=“rec-card”  
style={{  
…styles.card,  
animation: `cardIn 0.5s cubic-bezier(0.22, 1, 0.36, 1) ${index * 0.06}s both`,  
}}  
>  
<div style={styles.cardTop}>  
<span style={{ …styles.typeBadge, backgroundColor: bgColor, color: textColor }}>  
{rec.type}  
</span>  
<div style={{ display: “flex”, alignItems: “center”, gap: 8 }}>  
<button  
className="hide-btn"  
onClick={onHide}  
style={styles.hideBtn}  
title="Hide this pick (can restore later)"  
>  
✕  
</button>  
<button  
onClick={onToggleFav}  
style={styles.favBtn}  
title={isFav ? “Remove from favorites” : “Add to favorites”}  
>  
{isFav ? “♥” : “♡”}  
</button>  
</div>  
</div>  
  
```  
  <h3 style={styles.cardName}>{rec.name}</h3>  
  <p style={styles.cardAuthor}>by {rec.author}</p>  
  <p style={styles.cardDesc}>{rec.description}</p>  
  
  {rec.duck_note && (  
    <div style={styles.duckNoteWrap}>  
      <button onClick={() => setShowNote(!showNote)} style={styles.duckNoteToggle}>  
        <span style={{ color: T.accent }}>★</span>{" "}  
        {showNote ? "Hide note" : "Duck's note"}  
      </button>  
      {showNote && <p style={styles.duckNoteText}>"{rec.duck_note}"</p>}  
    </div>  
  )}  
  
  <div style={styles.cardTags}>  
    {rec.tags.map((tag) => (  
      <span key={tag} style={styles.cardTag}>{tag}</span>  
    ))}  
  </div>  
  
  {rec.url && (  
    <a href={rec.url} target="_blank" rel="noopener noreferrer" style={styles.visitLink}>  
      Visit →  
    </a>  
  )}  
</div>  
```  
  
);  
}  
  
/* ──────────────────────────────────────────────────────────────  
SECTION 7: STYLES  
  
All styles as JS objects. Organized by component area.  
Design tokens (T) are referenced throughout for consistency.  
────────────────────────────────────────────────────────────── */  
  
const styles = {  
/* Page */  
page: {  
fontFamily: T.fontSans, color: T.ink,  
backgroundColor: T.bgCream,  
minHeight: “100vh”, position: “relative”, overflowX: “hidden”,  
},  
bgDecor: {  
position: “absolute”, top: 0, left: 0, right: 0, height: 500,  
background: “linear-gradient(180deg, #f0e8df 0%, #faf8f5 100%)”,  
zIndex: 0, pointerEvents: “none”,  
},  
  
/* Header */  
header: {  
position: “relative”, zIndex: 1,  
padding: “60px 24px 40px”, textAlign: “center”,  
},  
headerInner: { maxWidth: 640, margin: “0 auto” },  
eyebrow: {  
fontFamily: T.fontSans, fontSize: 12, fontWeight: 600,  
letterSpacing: “0.15em”, textTransform: “uppercase”,  
color: T.accent, animation: “softPulse 3s ease-in-out infinite”,  
display: “inline-block”, marginBottom: 16,  
},  
title: {  
fontFamily: T.fontSerif, fontSize: “clamp(36px, 7vw, 64px)”,  
fontWeight: 700, lineHeight: 1.05,  
margin: “0 0 20px”, letterSpacing: “-0.02em”, color: T.ink,  
},  
titleAccent: { fontStyle: “italic”, color: T.accent },  
subtitle: {  
fontFamily: T.fontSerif, fontSize: “clamp(16px, 2.5vw, 20px)”,  
lineHeight: 1.6, color: T.inkLight,  
maxWidth: 520, margin: “0 auto 24px”, fontWeight: 400,  
},  
noteBadge: {  
display: “inline-flex”, alignItems: “center”, gap: 8,  
backgroundColor: “#fff”, border: `1px solid ${T.cardBorder}`,  
borderRadius: T.radiusPill, padding: “8px 18px”,  
fontSize: 13, color: T.inkLight,  
},  
noteBadgeIcon: { fontSize: 16 },  
noteBadgeText: { lineHeight: 1.4 },  
  
/* Main */  
main: {  
position: “relative”, zIndex: 1,  
maxWidth: 960, margin: “0 auto”, padding: “0 24px 60px”,  
},  
  
/* Admin toolbar */  
adminBar: {  
display: “flex”, gap: 10, marginBottom: 20,  
paddingBottom: 20, borderBottom: `1px solid ${T.cardBorder}`,  
},  
adminBtn: {  
display: “inline-flex”, alignItems: “center”, gap: 8,  
padding: “10px 20px”, fontSize: 14,  
fontFamily: T.fontSans, fontWeight: 600,  
border: `1.5px solid ${T.cardBorder}`, borderRadius: 10,  
backgroundColor: “#fff”, color: T.ink,  
cursor: “pointer”, transition: “all 0.2s”,  
},  
adminBtnActive: {  
backgroundColor: T.ink, color: “#fff”, borderColor: T.ink,  
},  
  
/* AI Panel */  
aiPanel: {  
backgroundColor: “#fff”, border: `1.5px solid ${T.cardBorder}`,  
borderRadius: 14, padding: 28, marginBottom: 24,  
animation: “slideDown 0.3s ease both”,  
},  
aiPanelTitle: {  
fontFamily: T.fontSerif, fontSize: 20, fontWeight: 600,  
margin: “0 0 8px”, color: T.ink,  
},  
aiPanelDesc: {  
fontSize: 14, lineHeight: 1.6, color: T.inkLight, margin: “0 0 18px”,  
},  
aiTextarea: {  
width: “100%”, boxSizing: “border-box”, padding: 16,  
fontSize: 15, fontFamily: T.fontSans,  
border: `1.5px solid ${T.cardBorder}`, borderRadius: 10,  
backgroundColor: T.bgCream, color: T.ink,  
resize: “vertical”, minHeight: 100, lineHeight: 1.5,  
},  
aiActions: {  
display: “flex”, alignItems: “center”, gap: 14, marginTop: 14,  
},  
aiSubmitBtn: {  
padding: “12px 28px”, fontSize: 14,  
fontFamily: T.fontSans, fontWeight: 600,  
border: “none”, borderRadius: 10,  
backgroundColor: T.accent, color: “#fff”,  
cursor: “pointer”, transition: “all 0.2s”,  
display: “inline-flex”, alignItems: “center”, gap: 8,  
},  
aiSubmitBtnDisabled: { opacity: 0.5, cursor: “not-allowed” },  
aiHint: { fontSize: 12, color: T.inkLight, fontStyle: “italic” },  
spinner: {  
display: “inline-block”, animation: “spin 1s linear infinite”, fontSize: 18,  
},  
aiFeedback: {  
marginTop: 14, padding: “10px 16px”,  
backgroundColor: “#eef5ec”, borderRadius: 8,  
fontSize: 14, fontWeight: 500, color: “#3a7a3a”,  
animation: “feedbackIn 0.3s ease both”,  
display: “flex”, alignItems: “center”,  
},  
aiFeedbackError: {  
marginTop: 14, padding: “10px 16px”,  
backgroundColor: “#fdf0e9”, borderRadius: 8,  
fontSize: 14, fontWeight: 500, color: “#c9553a”,  
animation: “feedbackIn 0.3s ease both”,  
display: “flex”, alignItems: “center”,  
},  
  
/* Hidden Panel */  
hiddenPanel: {  
backgroundColor: “#fff”, border: `1.5px solid ${T.cardBorder}`,  
borderRadius: 14, padding: 28, marginBottom: 24,  
animation: “slideDown 0.3s ease both”,  
},  
hiddenEmpty: {  
fontSize: 14, color: T.inkLight, margin: “8px 0 0”, lineHeight: 1.6,  
},  
hiddenList: {  
display: “flex”, flexDirection: “column”, gap: 10, marginTop: 14,  
},  
hiddenItem: {  
display: “flex”, justifyContent: “space-between”, alignItems: “center”,  
padding: “12px 16px”, backgroundColor: T.bgCream,  
borderRadius: 10, flexWrap: “wrap”, gap: 10,  
},  
hiddenItemInfo: {  
display: “flex”, alignItems: “center”, gap: 10, flexWrap: “wrap”,  
},  
hiddenItemType: {  
fontSize: 10, fontWeight: 600, textTransform: “uppercase”,  
letterSpacing: “0.06em”, padding: “2px 8px”,  
borderRadius: T.radiusPill, backgroundColor: “#ebe6df”, color: T.inkLight,  
},  
hiddenItemName: { fontFamily: T.fontSerif, fontSize: 15, fontWeight: 600 },  
hiddenItemAuthor: { fontSize: 13, color: T.inkLight },  
hiddenItemActions: { display: “flex”, gap: 8 },  
restoreBtn: {  
padding: “6px 14px”, fontSize: 12,  
fontFamily: T.fontSans, fontWeight: 600,  
border: “1.5px solid #3a7a3a”, borderRadius: 8,  
backgroundColor: “transparent”, color: “#3a7a3a”, cursor: “pointer”,  
},  
deleteBtn: {  
padding: “6px 14px”, fontSize: 12,  
fontFamily: T.fontSans, fontWeight: 600,  
border: “1.5px solid #c9553a”, borderRadius: 8,  
backgroundColor: “transparent”, color: “#c9553a”, cursor: “pointer”,  
},  
  
/* Search */  
searchWrap: { position: “relative”, marginBottom: 24 },  
searchIcon: {  
position: “absolute”, left: 18, top: “50%”,  
transform: “translateY(-50%)”, fontSize: 20,  
color: T.inkLight, pointerEvents: “none”,  
},  
searchInput: {  
width: “100%”, boxSizing: “border-box”,  
padding: “16px 48px 16px 50px”, fontSize: 16,  
fontFamily: T.fontSans, border: `1.5px solid ${T.cardBorder}`,  
borderRadius: 12, backgroundColor: “#fff”, color: T.ink,  
transition: “border-color 0.2s”,  
},  
clearBtn: {  
position: “absolute”, right: 16, top: “50%”,  
transform: “translateY(-50%)”, background: “none”,  
border: “none”, fontSize: 16, color: T.inkLight,  
cursor: “pointer”, padding: 4,  
},  
  
/* Filters */  
filterRow: { display: “flex”, flexWrap: “wrap”, gap: 8, marginBottom: 16 },  
categoryPill: {  
display: “inline-flex”, alignItems: “center”,  
padding: “8px 16px”, fontSize: 14,  
fontFamily: T.fontSans, fontWeight: 500,  
border: `1.5px solid ${T.cardBorder}`, borderRadius: T.radiusPill,  
backgroundColor: “#fff”, color: T.inkLight,  
cursor: “pointer”, transition: “all 0.2s”,  
},  
categoryPillActive: {  
backgroundColor: T.ink, color: “#fff”, borderColor: T.ink,  
},  
tagRow: { display: “flex”, flexWrap: “wrap”, gap: 6, marginBottom: 24 },  
tagPill: {  
padding: “5px 12px”, fontSize: 12,  
fontFamily: T.fontSans, fontWeight: 500,  
border: `1px solid ${T.cardBorder}`, borderRadius: T.radiusPill,  
backgroundColor: “transparent”, color: T.inkLight,  
cursor: “pointer”, transition: “all 0.2s”,  
},  
tagPillActive: {  
backgroundColor: T.accent, color: “#fff”, borderColor: T.accent,  
},  
  
/* Results bar */  
resultsBar: {  
display: “flex”, justifyContent: “space-between”, alignItems: “center”,  
marginBottom: 20, paddingBottom: 16,  
borderBottom: `1px solid ${T.cardBorder}`,  
},  
resultsCount: {  
fontSize: 14, fontWeight: 500, color: T.inkLight,  
display: “flex”, alignItems: “center”, gap: 10,  
},  
clearTags: {  
background: “none”, border: “none”, color: T.accent,  
cursor: “pointer”, fontSize: 12, fontWeight: 600,  
padding: 0, textDecoration: “underline”, fontFamily: T.fontSans,  
},  
favToggle: {  
padding: “6px 14px”, fontSize: 13,  
fontFamily: T.fontSans, fontWeight: 500,  
border: `1.5px solid ${T.cardBorder}`, borderRadius: T.radiusPill,  
backgroundColor: “#fff”, color: T.inkLight,  
cursor: “pointer”, transition: “all 0.2s”,  
},  
favToggleActive: {  
backgroundColor: “#fdf0e9”, borderColor: T.accent, color: T.accent,  
},  
  
/* Grid */  
grid: {  
display: “grid”,  
gridTemplateColumns: “repeat(auto-fill, minmax(340px, 1fr))”,  
gap: 20,  
},  
  
/* Card */  
card: {  
backgroundColor: T.cardBg, border: `1.5px solid ${T.cardBorder}`,  
borderRadius: T.radius, padding: 28,  
display: “flex”, flexDirection: “column”,  
transition: “transform 0.25s ease, box-shadow 0.25s ease”,  
cursor: “default”,  
},  
cardTop: {  
display: “flex”, justifyContent: “space-between”,  
alignItems: “center”, marginBottom: 14,  
},  
typeBadge: {  
fontSize: 11, fontWeight: 600,  
letterSpacing: “0.06em”, textTransform: “uppercase”,  
padding: “4px 12px”, borderRadius: T.radiusPill,  
},  
hideBtn: {  
background: “none”, border: “none”, fontSize: 14,  
cursor: “pointer”, color: T.inkLight,  
padding: “2px 4px”, borderRadius: 4, transition: “color 0.2s”,  
},  
favBtn: {  
background: “none”, border: “none”, fontSize: 22,  
cursor: “pointer”, color: T.accent,  
padding: 0, lineHeight: 1, transition: “transform 0.2s”,  
},  
cardName: {  
fontFamily: T.fontSerif, fontSize: 22, fontWeight: 600,  
margin: “0 0 4px”, lineHeight: 1.2, letterSpacing: “-0.01em”,  
},  
cardAuthor: {  
fontSize: 13, color: T.inkLight, margin: “0 0 12px”, fontWeight: 500,  
},  
cardDesc: {  
fontSize: 14.5, lineHeight: 1.6, color: “#4a4039”,  
margin: “0 0 14px”, flex: 1,  
},  
duckNoteWrap: { marginBottom: 14 },  
duckNoteToggle: {  
background: “none”, border: “none”, fontSize: 13,  
fontFamily: T.fontSans, fontWeight: 600,  
color: T.inkLight, cursor: “pointer”, padding: 0,  
display: “flex”, alignItems: “center”, gap: 4,  
},  
duckNoteText: {  
fontSize: 13, fontFamily: T.fontSerif, fontStyle: “italic”,  
color: T.accent, margin: “8px 0 0”, padding: “10px 14px”,  
backgroundColor: “#fdf8f5”, borderRadius: 8,  
borderLeft: `3px solid ${T.accent}`, lineHeight: 1.5,  
},  
cardTags: { display: “flex”, flexWrap: “wrap”, gap: 5, marginBottom: 16 },  
cardTag: {  
fontSize: 11, fontWeight: 500, color: T.inkLight,  
backgroundColor: T.bgCream, padding: “3px 9px”, borderRadius: T.radiusPill,  
},  
visitLink: {  
fontSize: 13, fontWeight: 600, color: T.accent,  
textDecoration: “none”, display: “inline-flex”,  
alignItems: “center”, gap: 4, marginTop: “auto”,  
transition: “color 0.2s”,  
},  
emptyState: {  
gridColumn: “1 / -1”, textAlign: “center”, padding: “60px 20px”,  
color: T.inkLight, display: “flex”, flexDirection: “column”,  
alignItems: “center”,  
},  
  
/* Footer */  
footer: {  
textAlign: “center”, padding: “40px 24px 60px”,  
borderTop: `1px solid ${T.cardBorder}`,  
maxWidth: 960, margin: “0 auto”,  
},  
footerText: {  
fontFamily: T.fontSerif, fontSize: 15, color: T.inkLight,  
margin: “0 0 8px”, fontStyle: “italic”,  
},  
footerSub: {  
fontSize: 12, color: T.inkLight, opacity: 0.6, margin: 0,  
},  
};  
