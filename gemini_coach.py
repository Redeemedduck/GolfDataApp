"""
Gemini 3.0 AI Coach Module with Function Calling

This module provides a cloud-native AI coaching experience using Google's Gemini 3.0 models.
It leverages function calling to query golf data and provide personalized insights.

Features:
- Multi-model support (gemini-3.0-flash-preview, gemini-3.0-pro-preview)
- Function calling for dynamic data access
- Conversation history management
- Flexible thinking levels for reasoning control
"""

import os
import google.generativeai as genai
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
import golf_db


class GeminiCoach:
    """
    AI Golf Coach powered by Gemini 3.0 with function calling capabilities.

    Attributes:
        model_name (str): Current Gemini model being used
        thinking_level (str): Reasoning intensity (minimal, low, medium, high)
        conversation_history (list): Chat history for multi-turn conversations
        available_functions (dict): Registered function calling tools
    """

    # Available Gemini 3.0 models
    MODELS = {
        'flash': 'gemini-3.0-flash-preview',  # Fast, cost-effective ($0.50/1M in, $3/1M out)
        'pro': 'gemini-3.0-pro-preview',      # Complex reasoning and agentic workflows
    }

    THINKING_LEVELS = ['minimal', 'low', 'medium', 'high']

    def __init__(self, model_type: str = 'flash', thinking_level: str = 'medium', api_key: Optional[str] = None):
        """
        Initialize the Gemini Coach.

        Args:
            model_type: 'flash' or 'pro'
            thinking_level: Reasoning intensity ('minimal', 'low', 'medium', 'high')
            api_key: Google API key (reads from GEMINI_API_KEY env var if not provided)
        """
        # Configure API key
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set and no API key provided")

        genai.configure(api_key=self.api_key)

        # Model configuration
        self.model_name = self.MODELS.get(model_type, self.MODELS['flash'])
        self.thinking_level = thinking_level if thinking_level in self.THINKING_LEVELS else 'medium'

        # Initialize model with generation config
        self.generation_config = {
            'temperature': 0.7,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 8192,
        }

        # Conversation state
        self.conversation_history = []
        self.chat_session = None

        # Register function calling tools
        self.available_functions = self._register_functions()

        # Initialize chat with system instruction
        self._initialize_chat()

    def _register_functions(self) -> Dict:
        """
        Register all available function calling tools.

        Returns:
            Dictionary mapping function names to callable implementations
        """
        return {
            'query_shot_data': self._query_shot_data,
            'calculate_statistics': self._calculate_statistics,
            'get_user_profile': self._get_user_profile,
            'analyze_trends': self._analyze_trends,
            'get_club_gapping': self._get_club_gapping,
            'find_outliers': self._find_outliers,
        }

    def _get_function_declarations(self) -> List[Dict]:
        """
        Get function declarations for Gemini function calling.

        Returns:
            List of function declaration schemas
        """
        return [
            {
                'name': 'query_shot_data',
                'description': 'Query golf shot data from the database. Use this to retrieve shot information for analysis.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'session_id': {
                            'type': 'string',
                            'description': 'Optional session ID to filter by. Leave empty for all sessions.'
                        },
                        'club': {
                            'type': 'string',
                            'description': 'Optional club name to filter by (e.g., "Driver", "7 Iron"). Leave empty for all clubs.'
                        },
                        'limit': {
                            'type': 'integer',
                            'description': 'Maximum number of shots to return. Default is 50.'
                        }
                    }
                }
            },
            {
                'name': 'calculate_statistics',
                'description': 'Calculate statistical metrics for golf performance (average, std dev, min, max, etc.).',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'session_id': {
                            'type': 'string',
                            'description': 'Optional session ID to analyze. Leave empty for all sessions.'
                        },
                        'club': {
                            'type': 'string',
                            'description': 'Optional club name to analyze. Leave empty for all clubs.'
                        },
                        'metric': {
                            'type': 'string',
                            'description': 'Metric to analyze (carry, total, ball_speed, club_speed, smash, launch_angle, back_spin, etc.)'
                        }
                    },
                    'required': ['metric']
                }
            },
            {
                'name': 'get_user_profile',
                'description': 'Get user performance profile and baselines for a specific club or overall.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'club': {
                            'type': 'string',
                            'description': 'Optional club name. Leave empty for overall profile.'
                        }
                    }
                }
            },
            {
                'name': 'analyze_trends',
                'description': 'Analyze performance trends over time across multiple sessions.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'club': {
                            'type': 'string',
                            'description': 'Club name to analyze trends for.'
                        },
                        'metric': {
                            'type': 'string',
                            'description': 'Metric to track (carry, ball_speed, smash, etc.)'
                        }
                    },
                    'required': ['club', 'metric']
                }
            },
            {
                'name': 'get_club_gapping',
                'description': 'Analyze distance gaps between clubs to identify gapping issues.',
                'parameters': {
                    'type': 'object',
                    'properties': {}
                }
            },
            {
                'name': 'find_outliers',
                'description': 'Find outlier shots that are statistically unusual or potentially erroneous.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'session_id': {
                            'type': 'string',
                            'description': 'Optional session ID to check. Leave empty for all sessions.'
                        },
                        'club': {
                            'type': 'string',
                            'description': 'Optional club name to check. Leave empty for all clubs.'
                        }
                    }
                }
            }
        ]

    def _initialize_chat(self):
        """Initialize chat session with system instruction and function declarations."""
        system_instruction = """You are an expert golf coach with deep knowledge of swing mechanics,
ball flight physics, and equipment optimization. You have access to the user's golf shot data through
function calling tools.

Your role is to:
1. Analyze golf performance data to identify strengths and weaknesses
2. Provide actionable coaching insights based on data patterns
3. Explain technical concepts in an accessible way
4. Suggest drills and practice strategies
5. Help with equipment gapping and club selection

When analyzing data:
- Use function calls to query specific shot data
- Calculate statistics to support your insights
- Identify trends and patterns over time
- Compare performance to typical benchmarks
- Be specific with numbers and examples

Provide coaching in a friendly, encouraging tone while being technically accurate.
Focus on actionable advice the golfer can implement in their next practice session."""

        model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            system_instruction=system_instruction,
            tools=self._get_function_declarations()
        )

        self.chat_session = model.start_chat(history=[])

    # Function calling implementations

    def _query_shot_data(self, session_id: Optional[str] = None, club: Optional[str] = None, limit: int = 50) -> str:
        """
        Query shot data from database.

        Returns:
            JSON string with shot data
        """
        try:
            df = golf_db.get_all_shots()

            if df.empty:
                return json.dumps({'error': 'No shot data available in database'})

            # Apply filters
            if session_id:
                df = df[df['session_id'] == session_id]
            if club:
                df = df[df['club'] == club]

            # Limit results
            df = df.head(limit)

            # Select relevant columns
            cols = ['session_id', 'shot_number', 'club', 'carry', 'total', 'ball_speed',
                   'club_speed', 'smash_factor', 'launch_angle', 'back_spin', 'side_spin']
            df = df[[col for col in cols if col in df.columns]]

            # Convert to records
            result = {
                'count': len(df),
                'shots': df.to_dict('records')
            }

            return json.dumps(result)
        except Exception as e:
            return json.dumps({'error': str(e)})

    def _calculate_statistics(self, metric: str, session_id: Optional[str] = None, club: Optional[str] = None) -> str:
        """
        Calculate statistics for a metric.

        Returns:
            JSON string with statistics
        """
        try:
            df = golf_db.get_all_shots()

            if df.empty:
                return json.dumps({'error': 'No shot data available'})

            # Apply filters
            if session_id:
                df = df[df['session_id'] == session_id]
            if club:
                df = df[df['club'] == club]

            if metric not in df.columns:
                return json.dumps({'error': f'Metric {metric} not found in data'})

            # Filter valid values (exclude zeros, NaN, 99999)
            data = df[metric].replace([0, 99999], np.nan).dropna()

            if len(data) == 0:
                return json.dumps({'error': f'No valid data for {metric}'})

            stats = {
                'metric': metric,
                'count': int(len(data)),
                'mean': float(data.mean()),
                'median': float(data.median()),
                'std': float(data.std()),
                'min': float(data.min()),
                'max': float(data.max()),
                'q25': float(data.quantile(0.25)),
                'q75': float(data.quantile(0.75)),
                'coefficient_of_variation': float((data.std() / data.mean()) * 100) if data.mean() != 0 else 0
            }

            return json.dumps(stats)
        except Exception as e:
            return json.dumps({'error': str(e)})

    def _get_user_profile(self, club: Optional[str] = None) -> str:
        """
        Get user performance profile.

        Returns:
            JSON string with profile data
        """
        try:
            df = golf_db.get_all_shots()

            if df.empty:
                return json.dumps({'error': 'No shot data available'})

            if club:
                df = df[df['club'] == club]

            # Calculate baselines for key metrics
            metrics = ['carry', 'total', 'ball_speed', 'club_speed', 'smash_factor', 'launch_angle', 'back_spin']
            profile = {}

            for metric in metrics:
                if metric in df.columns:
                    data = df[metric].replace([0, 99999], np.nan).dropna()
                    if len(data) > 0:
                        profile[metric] = {
                            'average': float(data.mean()),
                            'std_dev': float(data.std()),
                            'consistency_score': float(100 - min((data.std() / data.mean()) * 100, 100)) if data.mean() != 0 else 0
                        }

            # Add club-specific info if applicable
            if club:
                profile['club'] = club
                profile['total_shots'] = int(len(df))
            else:
                # Overall profile with club breakdown
                club_stats = df.groupby('club').size().to_dict()
                profile['clubs'] = {str(k): int(v) for k, v in club_stats.items()}
                profile['total_shots'] = int(len(df))

            return json.dumps(profile)
        except Exception as e:
            return json.dumps({'error': str(e)})

    def _analyze_trends(self, club: str, metric: str) -> str:
        """
        Analyze performance trends over sessions.

        Returns:
            JSON string with trend analysis
        """
        try:
            df = golf_db.get_all_shots()

            if df.empty:
                return json.dumps({'error': 'No shot data available'})

            # Filter by club
            df = df[df['club'] == club]

            if metric not in df.columns:
                return json.dumps({'error': f'Metric {metric} not found'})

            # Group by session and calculate average
            session_avg = df.groupby('session_id')[metric].apply(
                lambda x: x.replace([0, 99999], np.nan).dropna().mean()
            ).dropna()

            if len(session_avg) < 2:
                return json.dumps({'error': 'Need at least 2 sessions for trend analysis'})

            # Calculate trend
            x = np.arange(len(session_avg))
            y = session_avg.values

            # Linear regression
            coeffs = np.polyfit(x, y, 1)
            slope = float(coeffs[0])

            trend_analysis = {
                'club': club,
                'metric': metric,
                'sessions': len(session_avg),
                'first_value': float(session_avg.iloc[0]),
                'latest_value': float(session_avg.iloc[-1]),
                'trend_slope': slope,
                'improvement': float(session_avg.iloc[-1] - session_avg.iloc[0]),
                'improvement_pct': float(((session_avg.iloc[-1] - session_avg.iloc[0]) / session_avg.iloc[0]) * 100) if session_avg.iloc[0] != 0 else 0,
                'session_data': session_avg.to_dict()
            }

            return json.dumps(trend_analysis)
        except Exception as e:
            return json.dumps({'error': str(e)})

    def _get_club_gapping(self) -> str:
        """
        Analyze distance gaps between clubs.

        Returns:
            JSON string with gapping analysis
        """
        try:
            df = golf_db.get_all_shots()

            if df.empty:
                return json.dumps({'error': 'No shot data available'})

            # Calculate average carry for each club
            club_avg = df.groupby('club')['carry'].apply(
                lambda x: x.replace([0, 99999], np.nan).dropna().mean()
            ).dropna().sort_values(ascending=False)

            if len(club_avg) < 2:
                return json.dumps({'error': 'Need at least 2 clubs for gapping analysis'})

            # Calculate gaps
            gaps = []
            for i in range(len(club_avg) - 1):
                gap = club_avg.iloc[i] - club_avg.iloc[i + 1]
                gaps.append({
                    'longer_club': club_avg.index[i],
                    'longer_distance': float(club_avg.iloc[i]),
                    'shorter_club': club_avg.index[i + 1],
                    'shorter_distance': float(club_avg.iloc[i + 1]),
                    'gap': float(gap)
                })

            result = {
                'club_averages': {str(k): float(v) for k, v in club_avg.items()},
                'gaps': gaps,
                'avg_gap': float(np.mean([g['gap'] for g in gaps]))
            }

            return json.dumps(result)
        except Exception as e:
            return json.dumps({'error': str(e)})

    def _find_outliers(self, session_id: Optional[str] = None, club: Optional[str] = None) -> str:
        """
        Find outlier shots.

        Returns:
            JSON string with outlier information
        """
        try:
            df = golf_db.get_all_shots()

            if df.empty:
                return json.dumps({'error': 'No shot data available'})

            # Apply filters
            if session_id:
                df = df[df['session_id'] == session_id]
            if club:
                df = df[df['club'] == club]

            outliers = []

            # Check for unrealistic values
            checks = [
                ('carry', 0, 400, 'Carry distance'),
                ('total', 0, 450, 'Total distance'),
                ('ball_speed', 0, 250, 'Ball speed'),
                ('club_speed', 0, 200, 'Club speed'),
                ('smash_factor', 1.2, 1.6, 'Smash factor'),
                ('launch_angle', -10, 60, 'Launch angle'),
                ('back_spin', -2000, 12000, 'Back spin'),
            ]

            for metric, min_val, max_val, label in checks:
                if metric in df.columns:
                    invalid = df[(df[metric] < min_val) | (df[metric] > max_val)]
                    for _, row in invalid.iterrows():
                        outliers.append({
                            'session_id': row.get('session_id', 'unknown'),
                            'shot_number': int(row.get('shot_number', 0)),
                            'club': row.get('club', 'unknown'),
                            'metric': label,
                            'value': float(row[metric]),
                            'expected_range': f'{min_val}-{max_val}'
                        })

            result = {
                'total_outliers': len(outliers),
                'outliers': outliers[:20]  # Limit to 20 most recent
            }

            return json.dumps(result)
        except Exception as e:
            return json.dumps({'error': str(e)})

    def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Send a message to the AI coach and get a response with function calling.

        Args:
            user_message: User's question or request

        Returns:
            Dictionary with response and any function calls made
        """
        try:
            # Send message
            response = self.chat_session.send_message(user_message)

            # Track function calls
            function_calls = []

            # Handle function calling if present
            while response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]

                # Check if this is a function call
                if hasattr(part, 'function_call'):
                    fn_call = part.function_call
                    fn_name = fn_call.name
                    fn_args = dict(fn_call.args)

                    # Execute function
                    if fn_name in self.available_functions:
                        fn_result = self.available_functions[fn_name](**fn_args)

                        # Track the call
                        function_calls.append({
                            'function': fn_name,
                            'arguments': fn_args,
                            'result': fn_result
                        })

                        # Send function response back to model
                        response = self.chat_session.send_message(
                            genai.protos.Content(
                                parts=[genai.protos.Part(
                                    function_response=genai.protos.FunctionResponse(
                                        name=fn_name,
                                        response={'result': fn_result}
                                    )
                                )]
                            )
                        )
                    else:
                        break
                else:
                    # No more function calls, we have the final response
                    break

            # Extract final text response
            final_text = response.text if hasattr(response, 'text') else "Sorry, I couldn't generate a response."

            return {
                'response': final_text,
                'function_calls': function_calls,
                'model': self.model_name,
                'thinking_level': self.thinking_level
            }

        except Exception as e:
            return {
                'response': f"Error: {str(e)}",
                'function_calls': [],
                'error': str(e)
            }

    def reset_conversation(self):
        """Reset the conversation history and start fresh."""
        self._initialize_chat()
        self.conversation_history = []

    def get_conversation_history(self) -> List[Dict]:
        """Get the full conversation history."""
        return self.conversation_history

    def switch_model(self, model_type: str):
        """
        Switch to a different Gemini model.

        Args:
            model_type: 'flash' or 'pro'
        """
        if model_type in self.MODELS:
            self.model_name = self.MODELS[model_type]
            self._initialize_chat()

    def set_thinking_level(self, level: str):
        """
        Set the thinking level for reasoning.

        Args:
            level: 'minimal', 'low', 'medium', or 'high'
        """
        if level in self.THINKING_LEVELS:
            self.thinking_level = level


# Singleton instance
_coach_instance = None


def get_coach(model_type: str = 'flash', thinking_level: str = 'medium') -> GeminiCoach:
    """
    Get or create singleton GeminiCoach instance.

    Args:
        model_type: 'flash' or 'pro'
        thinking_level: Reasoning intensity

    Returns:
        GeminiCoach instance
    """
    global _coach_instance
    if _coach_instance is None:
        _coach_instance = GeminiCoach(model_type=model_type, thinking_level=thinking_level)
    return _coach_instance
