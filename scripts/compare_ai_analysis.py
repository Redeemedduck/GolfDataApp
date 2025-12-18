#!/usr/bin/env python3
"""
Multi-Agent Golf Analysis Comparison Tool

Runs both Claude and Gemini on the same golf data to provide complementary insights.

Why Compare?
- Different AI models notice different patterns
- Claude excels at: conversational analysis, nuanced coaching, structured explanations
- Gemini excels at: code execution, mathematical analysis, statistical patterns
- When both agree → high confidence recommendation
- When they differ → interesting insight requiring human judgment

Usage:
    python compare_ai_analysis.py                 # Compare all clubs
    python compare_ai_analysis.py Driver          # Compare specific club
    python compare_ai_analysis.py --save          # Save results to file
    python compare_ai_analysis.py Driver --claude-model=opus  # Use Opus for Claude
"""
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def print_header(text, char="="):
    """Print a formatted header"""
    width = 80
    print(f"\n{char*width}")
    print(text.center(width))
    print(f"{char*width}\n")

def run_claude_analysis(club=None, model="sonnet"):
    """
    Run Claude analysis and capture output

    Args:
        club: Optional club filter
        model: Claude model to use (opus, sonnet, haiku)

    Returns:
        dict with analysis results
    """
    print_header("🔵 RUNNING CLAUDE ANALYSIS", "-")

    try:
        from claude_analysis import analyze_with_claude

        start_time = time.time()
        result = analyze_with_claude(club=club, model=model, show_usage=False)
        elapsed = time.time() - start_time

        if result:
            return {
                "success": True,
                "analysis": result,
                "model": model,
                "elapsed_seconds": elapsed,
                "error": None
            }
        else:
            return {
                "success": False,
                "analysis": None,
                "model": model,
                "elapsed_seconds": elapsed,
                "error": "Claude analysis returned no results"
            }

    except ImportError:
        return {
            "success": False,
            "analysis": None,
            "model": model,
            "elapsed_seconds": 0,
            "error": "claude_analysis.py not found or import failed"
        }
    except Exception as e:
        return {
            "success": False,
            "analysis": None,
            "model": model,
            "elapsed_seconds": 0,
            "error": str(e)
        }

def run_gemini_analysis(club=None):
    """
    Run Gemini analysis and capture output

    Args:
        club: Optional club filter

    Returns:
        dict with analysis results
    """
    print_header("🟢 RUNNING GEMINI ANALYSIS (with Code Execution)", "-")

    try:
        from gemini_analysis import analyze_with_gemini_code_interpreter

        start_time = time.time()

        # Gemini prints directly, so we'll capture that it ran
        analyze_with_gemini_code_interpreter(club=club)

        elapsed = time.time() - start_time

        return {
            "success": True,
            "analysis": "[Output displayed above]",
            "model": "gemini-3-pro-preview",
            "elapsed_seconds": elapsed,
            "error": None
        }

    except ImportError:
        return {
            "success": False,
            "analysis": None,
            "model": "gemini-3-pro-preview",
            "elapsed_seconds": 0,
            "error": "gemini_analysis.py not found or import failed"
        }
    except Exception as e:
        return {
            "success": False,
            "analysis": None,
            "model": "gemini-3-pro-preview",
            "elapsed_seconds": 0,
            "error": str(e)
        }

def display_comparison_summary(claude_result, gemini_result, club=None):
    """
    Display a summary comparing both AI analyses

    Args:
        claude_result: Results from Claude
        gemini_result: Results from Gemini
        club: Club being analyzed
    """
    print_header("📊 MULTI-AGENT ANALYSIS SUMMARY", "=")

    print(f"**Analysis Target:** {club if club else 'All Clubs'}")
    print(f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Performance comparison
    print("### Performance Comparison\n")
    print("| AI Model | Status | Time (seconds) |")
    print("|----------|--------|----------------|")

    claude_status = "✅ Success" if claude_result["success"] else f"❌ {claude_result['error']}"
    gemini_status = "✅ Success" if gemini_result["success"] else f"❌ {gemini_result['error']}"

    print(f"| Claude {claude_result['model'].capitalize()} | {claude_status} | {claude_result['elapsed_seconds']:.2f}s |")
    print(f"| Gemini Code Execution | {gemini_status} | {gemini_result['elapsed_seconds']:.2f}s |")

    print("\n### Key Insights\n")

    if claude_result["success"] and gemini_result["success"]:
        print("✅ Both AI models successfully analyzed your data!\n")
        print("**Claude's Approach:**")
        print("- Conversational coaching style")
        print("- Nuanced swing interpretation")
        print("- Actionable drill recommendations")
        print("- Comparison to altitude-adjusted Tour averages\n")

        print("**Gemini's Approach:**")
        print("- Python code execution for statistical analysis")
        print("- Mathematical correlations and patterns")
        print("- Data-driven insights")
        print("- Dispersion and consistency calculations\n")

        print("💡 **Action Items:**")
        print("1. Look for patterns both AIs identified - those are your priorities!")
        print("2. Use Claude's drills for practice structure")
        print("3. Use Gemini's stats to track improvement objectively")
        print("4. Run this comparison weekly to validate progress\n")

    elif claude_result["success"]:
        print("ℹ️ Claude analysis succeeded, but Gemini encountered an issue.")
        print("You still have comprehensive coaching insights from Claude.\n")

    elif gemini_result["success"]:
        print("ℹ️ Gemini analysis succeeded, but Claude encountered an issue.")
        print("You still have statistical insights from Gemini.\n")

    else:
        print("⚠️ Both AI analyses encountered issues. Please check:")
        print("- API keys are set correctly in .env file")
        print("- BigQuery connection is working")
        print("- Required Python packages are installed\n")

def save_comparison_to_file(claude_result, gemini_result, club=None):
    """
    Save comparison results to a markdown file

    Args:
        claude_result: Claude analysis results
        gemini_result: Gemini analysis results
        club: Club being analyzed

    Returns:
        str: Path to saved file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    club_str = club.replace(" ", "_") if club else "all_clubs"
    filename = f"comparison_{club_str}_{timestamp}.md"
    filepath = os.path.join("analysis_reports", filename)

    # Create directory if it doesn't exist
    os.makedirs("analysis_reports", exist_ok=True)

    with open(filepath, "w") as f:
        f.write(f"# Multi-Agent Golf Analysis Comparison\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Club:** {club if club else 'All Clubs'}\n\n")

        f.write("---\n\n")

        # Claude section
        f.write("## 🔵 Claude Analysis\n\n")
        f.write(f"**Model:** {claude_result['model']}\n")
        f.write(f"**Status:** {'Success' if claude_result['success'] else 'Failed'}\n")
        f.write(f"**Time:** {claude_result['elapsed_seconds']:.2f} seconds\n\n")

        if claude_result["success"]:
            f.write(claude_result["analysis"])
        else:
            f.write(f"**Error:** {claude_result['error']}\n")

        f.write("\n\n---\n\n")

        # Gemini section
        f.write("## 🟢 Gemini Analysis\n\n")
        f.write(f"**Model:** {gemini_result['model']}\n")
        f.write(f"**Status:** {'Success' if gemini_result['success'] else 'Failed'}\n")
        f.write(f"**Time:** {gemini_result['elapsed_seconds']:.2f} seconds\n\n")

        if gemini_result["success"]:
            f.write(gemini_result["analysis"])
            f.write("\n\n*Note: Gemini's detailed output was displayed during execution.*\n")
        else:
            f.write(f"**Error:** {gemini_result['error']}\n")

        f.write("\n\n---\n\n")

        # Comparison notes
        f.write("## 💡 Comparative Insights\n\n")
        f.write("### How to Use This Report:\n\n")
        f.write("1. **Agreement = Priority:** If both AIs identified the same issue, prioritize fixing it\n")
        f.write("2. **Disagreement = Investigate:** Different perspectives may reveal nuanced patterns\n")
        f.write("3. **Claude for Coaching:** Use Claude's drills and feel-based recommendations\n")
        f.write("4. **Gemini for Stats:** Use Gemini's numerical analysis to track progress\n")
        f.write("5. **Weekly Review:** Run this comparison after each practice week\n\n")

        f.write("### Next Steps:\n\n")
        f.write("- [ ] Review both analyses for common themes\n")
        f.write("- [ ] Choose 1-2 specific drills from Claude's recommendations\n")
        f.write("- [ ] Set measurable goals based on Gemini's statistics\n")
        f.write("- [ ] Schedule next analysis session (recommended: 7 days)\n")

    return filepath

def print_usage():
    """Print CLI usage instructions"""
    print("""
Multi-Agent Golf Analysis Comparison Tool

BASIC USAGE:
    python compare_ai_analysis.py                    # Compare all clubs
    python compare_ai_analysis.py Driver             # Compare specific club
    python compare_ai_analysis.py "7 Iron"           # Use quotes for spaces

OPTIONS:
    --save                           Save results to analysis_reports/
    --claude-model=opus              Use Claude Opus (default: sonnet)
    --claude-model=haiku             Use Claude Haiku (faster, cheaper)

EXAMPLES:
    # Basic comparison
    python compare_ai_analysis.py Driver

    # Deep analysis with Opus, save results
    python compare_ai_analysis.py Driver --claude-model=opus --save

    # Quick comparison with Haiku
    python compare_ai_analysis.py --claude-model=haiku

WHY COMPARE?
    Different AI models have different strengths:

    Claude Strengths:
    - Conversational coaching style
    - Nuanced swing interpretation
    - Structured drill recommendations
    - Better at contextual explanations

    Gemini Strengths:
    - Python code execution for stats
    - Mathematical pattern detection
    - Correlation analysis
    - Quantitative precision

    When both identify the same issue → High priority!
    When they differ → Interesting insight to explore

WORKFLOW:
    1. Run comparison after each practice session
    2. Look for themes both AIs agree on
    3. Use Claude's drills for practice structure
    4. Use Gemini's stats to measure progress
    5. Re-run weekly to validate improvement

COST:
    Claude: $0.004 - $0.25 (depending on model)
    Gemini: ~$0.10
    Total:  $0.11 - $0.35 per comparison

    Tip: Use --claude-model=haiku for daily checks (cheaper)
         Use --claude-model=opus for weekly deep dives (best quality)
""")

def main():
    """Main CLI entry point"""
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print_usage()
        return 0

    # Parse arguments
    club = None
    claude_model = "sonnet"
    save_results = False

    for arg in args:
        if arg.startswith("--claude-model="):
            claude_model = arg.split("=")[1].lower()
            if claude_model not in ["opus", "sonnet", "haiku"]:
                print(f"Error: Invalid Claude model '{claude_model}'. Choose from: opus, sonnet, haiku")
                return 1
        elif arg == "--save" or arg == "-s":
            save_results = True
        elif not arg.startswith("--"):
            club = arg

    # Print intro
    print_header("🤖 MULTI-AGENT GOLF ANALYSIS 🏌️", "=")
    print(f"\n**Configuration:**")
    print(f"  - Club: {club if club else 'All Clubs'}")
    print(f"  - Claude Model: {claude_model.capitalize()}")
    print(f"  - Gemini Model: gemini-3-pro-preview (with Code Execution)")
    print(f"  - Save Results: {'Yes' if save_results else 'No'}\n")

    input("Press Enter to start dual AI analysis...")

    # Run both analyses
    claude_result = run_claude_analysis(club=club, model=claude_model)
    print("\n")  # Spacing
    gemini_result = run_gemini_analysis(club=club)

    # Display comparison
    display_comparison_summary(claude_result, gemini_result, club=club)

    # Save if requested
    if save_results:
        filepath = save_comparison_to_file(claude_result, gemini_result, club=club)
        print(f"\n💾 **Results saved to:** {filepath}\n")

    print_header("COMPARISON COMPLETE", "=")

    return 0

if __name__ == "__main__":
    sys.exit(main())
