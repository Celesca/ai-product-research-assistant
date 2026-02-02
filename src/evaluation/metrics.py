"""
Evaluation metrics for RAG and Agent performance.
"""
from typing import List, Dict, Any, Union, Set
import numpy as np
from collections import Counter

class RAGMetrics:
    """Metrics for Retrieval-Augmented Generation."""
    
    @staticmethod
    def calculate_mrr(relevant_docs: List[str], retrieved_docs: List[str]) -> float:
        """
        Calculate Mean Reciprocal Rank (MRR).
        Checks if the first relevant document appears in the retrieved list.
        """
        for i, doc in enumerate(retrieved_docs):
            if doc in relevant_docs:
                return 1.0 / (i + 1)
        return 0.0

    @staticmethod
    def calculate_context_recall(relevant_facts: List[str], retrieved_context: str) -> float:
        """
        Calculate Context Recall.
        Percentage of relevant facts that are present in the retrieved context.
        Note: Simple string matching for demonstration. In production, use LLM or embedding similarity.
        """
        if not relevant_facts:
            return 0.0
        
        matches = 0
        context_lower = retrieved_context.lower()
        
        for fact in relevant_facts:
            if fact.lower() in context_lower:
                matches += 1
                
        return matches / len(relevant_facts)

    @staticmethod
    def calculate_context_precision(relevant_docs: List[str], retrieved_docs: List[str]) -> float:
        """
        Calculate Context Precision.
        Ratio of relevant documents retrieved to total retrieved documents.
        """
        if not retrieved_docs:
            return 0.0
            
        relevant_set = set(relevant_docs)
        retrieved_set = set(retrieved_docs)
        
        intersection = relevant_set.intersection(retrieved_set)
        return len(intersection) / len(retrieved_set)

    @staticmethod
    def calculate_faithfulness(answer: str, context: str) -> float:
        """
        Calculate Faithfulness (Hallucination check).
        Checks if the answer is supported by the context.
        Note: This usually requires an LLM. Here we use a heuristic overlap for demo.
        """
        if not answer or not context:
            return 0.0
            
        answer_words = set(answer.lower().split())
        context_words = set(context.lower().split())
        
        # Remove stopwords (simplified)
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'in', 'on', 'at', 'of', 'for', 'and', 'or'}
        answer_words = answer_words - stopwords
        
        if not answer_words:
            return 1.0 # Empty answer (or only stopwords) is effectively faithful if it says nothing
            
        overlap = answer_words.intersection(context_words)
        return len(overlap) / len(answer_words)


class AgentMetrics:
    """Metrics for Agent Performance."""
    
    @staticmethod
    def calculate_tool_selection_accuracy(expected_tools: List[str], actual_tools: List[str]) -> float:
        """
        Calculate Tool Selection Accuracy (Jaccard Similarity).
        """
        if not expected_tools and not actual_tools:
            return 1.0
            
        expected_set = set(expected_tools)
        actual_set = set(actual_tools)
        
        intersection = expected_set.intersection(actual_set)
        union = expected_set.union(actual_set)
        
        return len(intersection) / len(union) if union else 0.0

    @staticmethod
    def calculate_goal_completion(expected_outcome: Dict[str, Any], actual_outcome: Dict[str, Any]) -> float:
        """
        Calculate Goal Completion Rate.
        Checks if key expected information is present in the output.
        """
        if not expected_outcome:
            return 1.0
            
        matches = 0
        total_criteria = len(expected_outcome)
        
        for key, value in expected_outcome.items():
            if key in actual_outcome:
                # If value is a list (e.g., products), check if at least one matches
                if isinstance(value, list) and isinstance(actual_outcome[key], list):
                    if any(item in actual_outcome[key] for item in value):
                        matches += 1
                # Exact match or substring match for text
                elif str(value).lower() in str(actual_outcome[key]).lower():
                    matches += 1
                    
        return matches / total_criteria
