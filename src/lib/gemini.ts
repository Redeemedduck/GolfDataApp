import { GoogleGenerativeAI } from '@google/generative-ai';
import { getOverallStats, getClubPerformance, getRecentShots } from './bigquery';

const apiKey = process.env.GEMINI_API_KEY;

let genAI: GoogleGenerativeAI | null = null;

function getGeminiClient() {
  if (!genAI && apiKey) {
    genAI = new GoogleGenerativeAI(apiKey);
  }
  return genAI;
}

export interface ChatContext {
  conversationHistory: Array<{
    role: 'user' | 'model';
    parts: string;
  }>;
}

export async function generateGolfInsights(
  userMessage: string,
  context?: ChatContext
): Promise<string> {
  const client = getGeminiClient();

  if (!client) {
    throw new Error('Gemini API key not configured');
  }

  // Fetch recent golf data from BigQuery
  const [stats, clubPerf] = await Promise.all([
    getOverallStats(30),
    getClubPerformance(30),
  ]);

  // Build context about the golfer's data
  const dataContext = `
You are an expert golf coach analyzing shot data from a TrackMan/Uneekor launch monitor.
This golfer practices at Denver altitude (5,280 ft).

CURRENT PERFORMANCE DATA (Last 30 Days):
- Total Shots: ${stats.totalShots}
- Practice Sessions: ${stats.recentSessions}
- Clubs Used: ${stats.clubs.join(', ')}
- Average Carry: ${stats.avgCarry.toFixed(1)} yards
- Average Smash Factor: ${stats.avgSmash.toFixed(2)}
- Average Ball Speed: ${stats.avgBallSpeed.toFixed(1)} mph

CLUB-BY-CLUB PERFORMANCE:
${clubPerf.map(c => `
- ${c.club}:
  * ${c.shots} shots
  * Avg Carry: ${c.avgCarry.toFixed(1)} yards
  * Smash Factor: ${c.avgSmash.toFixed(2)}
  * Ball Speed: ${c.avgBallSpeed.toFixed(1)} mph
  * Consistency (Std Dev): ${c.consistency.toFixed(1)} yards
`).join('')}

INSTRUCTIONS:
- Provide specific, actionable insights based on the data above
- Reference actual numbers from their performance
- Compare to PGA Tour averages when relevant (adjusted for Denver altitude)
- Be encouraging but honest about areas needing improvement
- For questions about specific clubs, focus your analysis on that club's data
- If asked about trends, note that you're analyzing the last 30 days
- Keep responses concise and focused (2-3 paragraphs max)
`;

  const model = client.getGenerativeModel({
    model: 'gemini-1.5-flash',
    systemInstruction: dataContext,
  });

  // Build conversation history
  const history = context?.conversationHistory || [];

  const chat = model.startChat({
    history: history.map(msg => ({
      role: msg.role,
      parts: [{ text: msg.parts }],
    })),
  });

  const result = await chat.sendMessage(userMessage);
  const response = result.response;
  return response.text();
}
