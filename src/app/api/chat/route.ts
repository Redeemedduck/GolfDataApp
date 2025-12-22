import { NextRequest, NextResponse } from 'next/server';
import { generateGolfInsights, ChatContext } from '@/lib/gemini';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 60; // Allow up to 60 seconds for AI response

// In-memory conversation storage (in production, use Redis or database)
const conversations = new Map<string, ChatContext>();

/**
 * Chat API Route - Integrates with Gemini AI + BigQuery
 *
 * This endpoint provides conversational golf data analysis powered by:
 * - Gemini AI for intelligent coaching insights
 * - BigQuery for real-time access to shot data
 * - Conversation memory for multi-turn dialogues
 */
export async function POST(request: NextRequest) {
  try {
    const { message, sessionId, conversationHistory } = await request.json();

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    // Get or create conversation context
    const currentSessionId = sessionId || `session-${Date.now()}`;
    let context = conversations.get(currentSessionId);

    if (!context && conversationHistory) {
      context = { conversationHistory };
      conversations.set(currentSessionId, context);
    }

    // Generate AI response with BigQuery data
    const aiResponse = await generateGolfInsights(message, context);

    // Update conversation history
    if (context) {
      context.conversationHistory.push(
        { role: 'user', parts: message },
        { role: 'model', parts: aiResponse }
      );
    } else {
      conversations.set(currentSessionId, {
        conversationHistory: [
          { role: 'user', parts: message },
          { role: 'model', parts: aiResponse },
        ],
      });
    }

    return NextResponse.json({
      response: aiResponse,
      sessionId: currentSessionId,
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error('Chat API error:', error);

    // Provide user-friendly error messages
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

    if (errorMessage.includes('API key')) {
      return NextResponse.json(
        { error: 'AI service not configured. Please set GEMINI_API_KEY environment variable.' },
        { status: 503 }
      );
    }

    if (errorMessage.includes('BigQuery')) {
      return NextResponse.json(
        { error: 'Database connection error. Please check BigQuery configuration.' },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { error: `Failed to process chat message: ${errorMessage}` },
      { status: 500 }
    );
  }
}
