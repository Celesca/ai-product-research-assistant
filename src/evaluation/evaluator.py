"""
Automated evaluation pipeline for the AI Research Assistant.
"""
import asyncio
import json
import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.evaluation.metrics import RAGMetrics, AgentMetrics
# Import agent factory - handle potential import errors gracefully if not set up
try:
    from src.agent.research_agent import create_agent
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False
    print("Warning: Could not import ResearchAgent. Tests will assume mock responses.")

class Evaluator:
    def __init__(self, test_cases_path: str = "src/evaluation/test_cases.json"):
        self.test_cases_path = test_cases_path
        self.results = []
        self.agent = create_agent() if AGENT_AVAILABLE else None
        
    def load_test_cases(self) -> List[Dict]:
        """Load test cases from JSON file."""
        try:
            with open(self.test_cases_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Test cases file not found at {self.test_cases_path}")
            return []

    async def run_evaluation(self):
        """Run all test cases and calculate metrics."""
        test_cases = self.load_test_cases()
        print(f"Starting evaluation of {len(test_cases)} test cases...")
        
        for case in test_cases:
            print(f"Running test: {case['id']} - {case['query'][:50]}...")
            
            # Run query through agent
            if self.agent:
                try:
                    response = await self.agent.aquery(case['query'])
                except Exception as e:
                    print(f"Error running query: {e}")
                    response = {"error": str(e), "tools_used": [], "products": []}
            else:
                # Mock response for testing the evaluator itself
                response = {
                    "answer": "Mock answer", 
                    "tools_used": case["expected_tools"],
                    "products": case["expected_outcome"].get("products", [])
                }
            
            # Calculate Metrics
            metrics = {}
            
            # 1. Tool Selection Accuracy
            actual_tools = response.get("tools_used", [])
            expected_tools = case.get("expected_tools", [])
            metrics["tool_accuracy"] = AgentMetrics.calculate_tool_selection_accuracy(expected_tools, actual_tools)
            
            # 2. Goal Completion (Heuristic)
            metrics["goal_completion"] = AgentMetrics.calculate_goal_completion(
                case.get("expected_outcome", {}), 
                response
            )
            
            # 3. RAG/Generation Metrics (if answer present)
            if "answer" in response:
                # Faithfulness (using reasoning/sources as context proxy)
                context = str(response.get("products", "")) + str(response.get("reasoning", ""))
                metrics["faithfulness"] = RAGMetrics.calculate_faithfulness(response["answer"], context)
            
            # Store result
            result = {
                "id": case["id"],
                "category": case["category"],
                "query": case["query"],
                "metrics": metrics,
                "details": {
                    "expected_tools": expected_tools,
                    "actual_tools": actual_tools
                }
            }
            self.results.append(result)
            
        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate aggregate report."""
        if not self.results:
            return {"status": "no results"}
            
        categories = set(r["category"] for r in self.results)
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "aggregate_scores": {
                "mean_tool_accuracy": np.mean([r["metrics"].get("tool_accuracy", 0) for r in self.results]),
                "mean_goal_completion": np.mean([r["metrics"].get("goal_completion", 0) for r in self.results]),
                "mean_faithfulness": np.mean([r["metrics"].get("faithfulness", 0) for r in self.results])
            },
            "category_breakdown": {}
        }
        
        for cat in categories:
            cat_results = [r for r in self.results if r["category"] == cat]
            report["category_breakdown"][cat] = {
                "tool_accuracy": np.mean([r["metrics"].get("tool_accuracy", 0) for r in cat_results]),
                "count": len(cat_results)
            }
            
        # Save detailed report to file
        os.makedirs("evaluation_reports", exist_ok=True)
        report_path = f"evaluation_reports/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        full_output = {"summary": report, "detailed_results": self.results}
        with open(report_path, "w") as f:
            json.dump(full_output, f, indent=2)
            
        print(f"Evaluation complete. Report saved to {report_path}")
        return report

if __name__ == "__main__":
    evaluator = Evaluator()
    asyncio.run(evaluator.run_evaluation())
