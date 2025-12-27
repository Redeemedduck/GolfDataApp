"""
Vertex AI Conversational Agent for Golf Data Analysis

This module provides a conversational AI agent with:
- Multi-turn conversation memory
- Direct BigQuery access for golf data
- Custom tools for swing analysis
- Web grounding for golf tips and PGA Tour comparisons
- Proactive insights based on historical data

Architecture:
- Uses Vertex AI generative models (Gemini 2.0 Flash)
- Function calling for BigQuery queries and analysis
- Session management for conversation context
- Integration with existing golf_stats.db and BigQuery warehouse
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    Tool,
    FunctionDeclaration,
    Content,
    Part,
)


class GolfCoachAgent:
    """
    Conversational AI Golf Coach with memory and BigQuery access.

    Features:
    - Multi-turn conversations with context memory
    - Direct BigQuery queries for historical analysis
    - PGA Tour benchmark comparisons
    - Personalized swing recommendations
    - Proactive insight generation
    """

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-2.0-flash-exp",
        dataset_id: str = "golf_data",
        table_id: str = "shots"
    ):
        """
        Initialize the Golf Coach Agent.

        Args:
            project_id: Google Cloud project ID
            location: GCP region for Vertex AI
            model_name: Gemini model to use
            dataset_id: BigQuery dataset name
            table_id: BigQuery table name
        """
        self.project_id = project_id
        self.location = location
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.full_table_id = f"{project_id}.{dataset_id}.{table_id}"

        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        # Initialize BigQuery client
        self.bq_client = bigquery.Client(project=project_id)

        # Define custom tools for golf analysis
        self.tools = self._create_tools()

        # Initialize generative model with tools
        self.model = GenerativeModel(
            model_name=model_name,
            tools=[self.tools],
            system_instruction=self._get_system_instruction()
        )

        # Conversation history (for multi-turn context)
        self.chat_history: List[Content] = []

        # Session metadata
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.total_shots_analyzed = 0

    def _get_system_instruction(self) -> str:
        """Get the system instruction for the golf coach agent."""
        return """You are an expert golf coach AI with deep knowledge of swing mechanics,
ball flight physics, and golf instruction. You have direct access to the golfer's
complete shot history via BigQuery and can provide personalized analysis.

Your capabilities:
1. Query BigQuery for historical shot data and trends
2. Analyze swing mechanics (club path, face angle, attack angle, spin rates)
3. Compare performance to PGA Tour averages (adjusted for Denver altitude)
4. Identify patterns and correlations in shot data
5. Provide specific, actionable recommendations
6. Track improvement over time across multiple sessions

When analyzing data:
- Always consider altitude effects (Denver = ~5,280 ft, expect 10% more distance)
- Look for correlations between swing metrics and ball flight
- Identify consistency issues (standard deviation analysis)
- Compare to optimal launch conditions for each club
- Suggest specific drills or swing changes

Be conversational, encouraging, and data-driven. Remember context from earlier
in the conversation to provide coherent multi-turn coaching sessions."""

    def _create_tools(self) -> Tool:
        """Create function declarations for golf analysis tools."""

        # Tool 1: Query BigQuery for shot data
        query_shots = FunctionDeclaration(
            name="query_golf_shots",
            description="Query BigQuery for golf shot data with filters. Returns comprehensive shot metrics including carry distance, ball speed, spin rates, launch angles, club path, face angle, and more.",
            parameters={
                "type": "object",
                "properties": {
                    "club": {
                        "type": "string",
                        "description": "Filter by club name (e.g., 'Driver', '7 Iron', 'Pitching Wedge'). Leave empty for all clubs."
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Filter by specific practice session ID. Leave empty for all sessions."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of shots to return. Default 100.",
                        "default": 100
                    },
                    "order_by": {
                        "type": "string",
                        "description": "Order results by field (e.g., 'date_added DESC', 'carry DESC'). Default 'date_added DESC'.",
                        "default": "date_added DESC"
                    }
                }
            }
        )

        # Tool 2: Get club performance statistics
        get_club_stats = FunctionDeclaration(
            name="get_club_statistics",
            description="Get aggregated statistics for a specific club including averages, standard deviations, min/max values, and shot count. Useful for understanding consistency and performance trends.",
            parameters={
                "type": "object",
                "properties": {
                    "club": {
                        "type": "string",
                        "description": "Club name to analyze (e.g., 'Driver', '7 Iron')"
                    }
                },
                "required": ["club"]
            }
        )

        # Tool 3: Compare clubs performance
        compare_clubs = FunctionDeclaration(
            name="compare_clubs_performance",
            description="Compare performance metrics across multiple clubs. Returns side-by-side statistics for distance, accuracy, consistency, and swing mechanics.",
            parameters={
                "type": "object",
                "properties": {
                    "clubs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of clubs to compare (e.g., ['Driver', '3 Wood', '5 Iron'])"
                    }
                },
                "required": ["clubs"]
            }
        )

        # Tool 4: Analyze shot patterns
        analyze_patterns = FunctionDeclaration(
            name="analyze_shot_patterns",
            description="Analyze patterns and correlations in shot data. Looks for relationships between swing metrics and ball flight, identifies tendencies (slice/hook patterns), and finds consistency issues.",
            parameters={
                "type": "object",
                "properties": {
                    "club": {
                        "type": "string",
                        "description": "Club to analyze. Leave empty for all clubs."
                    },
                    "metric": {
                        "type": "string",
                        "description": "Specific metric to focus on (e.g., 'club_path', 'face_angle', 'side_spin'). Leave empty for comprehensive analysis."
                    }
                },
            }
        )

        # Tool 5: Get session summary
        get_session_summary = FunctionDeclaration(
            name="get_session_summary",
            description="Get a comprehensive summary of a practice session including total shots, clubs used, best shots, areas for improvement, and key insights.",
            parameters={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID to summarize. If empty, summarizes the most recent session."
                    }
                }
            }
        )

        # Combine all tools
        return Tool(function_declarations=[
            query_shots,
            get_club_stats,
            compare_clubs,
            analyze_patterns,
            get_session_summary
        ])

    def query_golf_shots(
        self,
        club: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 100,
        order_by: str = "date_added DESC"
    ) -> Dict[str, Any]:
        """Execute BigQuery query for golf shots."""
        try:
            query = f"""
            SELECT
                shot_id,
                session_id,
                date_added,
                club,
                carry,
                total,
                ball_speed,
                club_speed,
                smash,
                launch_angle,
                side_angle,
                club_path,
                face_angle,
                attack_angle,
                dynamic_loft,
                back_spin,
                side_spin,
                apex,
                flight_time,
                side_distance,
                impact_x,
                impact_y,
                shot_type
            FROM `{self.full_table_id}`
            WHERE carry > 0  -- Filter out invalid shots
            """

            if club:
                query += f" AND LOWER(club) = LOWER('{club}')"
            if session_id:
                query += f" AND session_id = '{session_id}'"

            query += f" ORDER BY {order_by} LIMIT {limit}"

            result = self.bq_client.query(query).to_dataframe()
            self.total_shots_analyzed += len(result)

            return {
                "success": True,
                "shot_count": len(result),
                "data": result.to_dict(orient="records")
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_club_statistics(self, club: str) -> Dict[str, Any]:
        """Get aggregated statistics for a specific club."""
        try:
            query = f"""
            SELECT
                COUNT(*) as shot_count,
                AVG(carry) as avg_carry,
                STDDEV(carry) as stddev_carry,
                MIN(carry) as min_carry,
                MAX(carry) as max_carry,
                AVG(ball_speed) as avg_ball_speed,
                AVG(club_speed) as avg_club_speed,
                AVG(smash) as avg_smash,
                AVG(launch_angle) as avg_launch_angle,
                STDDEV(launch_angle) as stddev_launch_angle,
                AVG(back_spin) as avg_back_spin,
                AVG(side_spin) as avg_side_spin,
                STDDEV(side_spin) as stddev_side_spin,
                AVG(club_path) as avg_club_path,
                STDDEV(club_path) as stddev_club_path,
                AVG(face_angle) as avg_face_angle,
                STDDEV(face_angle) as stddev_face_angle,
                AVG(attack_angle) as avg_attack_angle,
                AVG(ABS(side_distance)) as avg_dispersion
            FROM `{self.full_table_id}`
            WHERE LOWER(club) = LOWER('{club}')
              AND carry > 0
            """

            result = self.bq_client.query(query).to_dataframe()

            if len(result) == 0:
                return {"success": False, "error": f"No data found for club: {club}"}

            stats = result.iloc[0].to_dict()
            stats["success"] = True
            stats["club"] = club

            return stats

        except Exception as e:
            return {"success": False, "error": str(e)}

    def compare_clubs_performance(self, clubs: List[str]) -> Dict[str, Any]:
        """Compare performance across multiple clubs."""
        comparison = {"success": True, "clubs": {}}

        for club in clubs:
            stats = self.get_club_statistics(club)
            if stats.get("success"):
                comparison["clubs"][club] = stats

        return comparison

    def analyze_shot_patterns(
        self,
        club: Optional[str] = None,
        metric: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze patterns and correlations in shot data."""
        try:
            # Query for pattern analysis
            query = f"""
            SELECT
                club,
                club_path,
                face_angle,
                side_spin,
                side_distance,
                launch_angle,
                back_spin,
                carry,
                shot_type
            FROM `{self.full_table_id}`
            WHERE carry > 0
            """

            if club:
                query += f" AND LOWER(club) = LOWER('{club}')"

            query += " ORDER BY date_added DESC LIMIT 200"

            result = self.bq_client.query(query).to_dataframe()

            # Calculate correlations
            correlations = result.corr().to_dict() if len(result) > 5 else {}

            # Shot type distribution
            shot_type_dist = result['shot_type'].value_counts().to_dict() if 'shot_type' in result else {}

            return {
                "success": True,
                "shot_count": len(result),
                "correlations": correlations,
                "shot_type_distribution": shot_type_dist,
                "summary_stats": result.describe().to_dict()
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_session_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive summary of a practice session."""
        try:
            # Get most recent session if not specified
            if not session_id:
                session_query = f"""
                SELECT DISTINCT session_id
                FROM `{self.full_table_id}`
                ORDER BY session_id DESC
                LIMIT 1
                """
                session_result = self.bq_client.query(session_query).to_dataframe()
                if len(session_result) == 0:
                    return {"success": False, "error": "No sessions found"}
                session_id = session_result.iloc[0]['session_id']

            # Query session data
            query = f"""
            SELECT
                session_id,
                MIN(date_added) as session_start,
                MAX(date_added) as session_end,
                COUNT(*) as total_shots,
                COUNT(DISTINCT club) as clubs_used,
                STRING_AGG(DISTINCT club ORDER BY club) as clubs_list,
                AVG(carry) as avg_carry,
                MAX(carry) as best_carry,
                AVG(smash) as avg_smash,
                MAX(smash) as best_smash
            FROM `{self.full_table_id}`
            WHERE session_id = '{session_id}'
              AND carry > 0
            GROUP BY session_id
            """

            summary = self.bq_client.query(query).to_dataframe().iloc[0].to_dict()
            summary["success"] = True

            return summary

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_function_call(self, function_name: str, args: Dict[str, Any]) -> str:
        """Execute a function call from the model and return formatted results."""

        function_map = {
            "query_golf_shots": self.query_golf_shots,
            "get_club_statistics": self.get_club_statistics,
            "compare_clubs_performance": self.compare_clubs_performance,
            "analyze_shot_patterns": self.analyze_shot_patterns,
            "get_session_summary": self.get_session_summary
        }

        if function_name not in function_map:
            return json.dumps({"error": f"Unknown function: {function_name}"})

        result = function_map[function_name](**args)
        return json.dumps(result, default=str)

    def chat(self, message: str, reset_history: bool = False) -> str:
        """
        Send a message to the golf coach and get a response.

        Args:
            message: User's question or request
            reset_history: If True, clears conversation history (starts new session)

        Returns:
            Agent's response as a string
        """
        if reset_history:
            self.chat_history = []
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create chat session
        chat = self.model.start_chat(history=self.chat_history)

        # Send message and get response
        response = chat.send_message(message)

        # Handle function calls (tool usage)
        # Check all parts for function calls
        while any(hasattr(part, 'function_call') and part.function_call for part in response.candidates[0].content.parts):
            # Find the first function call
            function_call = None
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    break

            if function_call:
                function_name = function_call.name
                function_args = dict(function_call.args)

                # Execute the function
                function_result = self._execute_function_call(function_name, function_args)

                # Send result back to model
                response = chat.send_message(
                    Part.from_function_response(
                        name=function_name,
                        response={"content": function_result}
                    )
                )

        # Update chat history
        self.chat_history = chat.history

        # Extract text from response (handle multiple text parts)
        text_parts = []
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'text') and part.text:
                text_parts.append(part.text)

        return ''.join(text_parts) if text_parts else "I apologize, but I couldn't generate a response. Please try again."

    def get_proactive_insights(self) -> str:
        """
        Generate proactive insights based on recent performance without user prompting.

        Returns:
            AI-generated insights and recommendations
        """
        prompt = """Analyze my recent golf performance and provide proactive insights.
        Look for:
        1. Recent trends (improving or declining metrics)
        2. Consistency patterns across clubs
        3. Areas that need immediate attention
        4. Specific drills or practice recommendations
        5. Positive developments to build on

        Be specific and actionable."""

        return self.chat(prompt, reset_history=False)


def create_golf_coach(
    project_id: str = None,
    location: str = "us-central1"
) -> GolfCoachAgent:
    """
    Factory function to create a Golf Coach Agent instance.

    Args:
        project_id: Google Cloud project ID (defaults to GCP_PROJECT_ID env var)
        location: GCP region

    Returns:
        Initialized GolfCoachAgent instance
    """
    if project_id is None:
        project_id = os.getenv("GCP_PROJECT_ID")
        if not project_id:
            raise ValueError("project_id must be provided or GCP_PROJECT_ID env var must be set")

    return GolfCoachAgent(project_id=project_id, location=location)


# Example usage
if __name__ == "__main__":
    # Create agent
    coach = create_golf_coach()

    print("🏌️ Golf Coach AI Agent initialized!")
    print(f"Session ID: {coach.session_id}")
    print(f"Connected to BigQuery: {coach.full_table_id}\n")

    # Example conversation
    print("=" * 60)
    print("Example Conversation:")
    print("=" * 60)

    response1 = coach.chat("What's my average carry distance with the Driver?")
    print(f"\n🤖 Coach: {response1}\n")

    response2 = coach.chat("How does that compare to PGA Tour averages?")
    print(f"\n🤖 Coach: {response2}\n")

    response3 = coach.chat("What should I focus on improving?")
    print(f"\n🤖 Coach: {response3}\n")

    print(f"\n📊 Total shots analyzed in this session: {coach.total_shots_analyzed}")
