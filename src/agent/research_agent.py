"""
AI Research Agent using LangGraph and Ollama.

This agent intelligently routes queries to the appropriate tools:
- Product Catalog RAG: For internal product searches
- Web Search: For market trends and competitor info
- Price Analysis: For margin calculations and pricing insights

The agent uses LangGraph for state management and tool orchestration.
"""
from typing import Dict, Any, List, Optional, TypedDict, Annotated, Sequence
from typing_extensions import TypedDict
import operator
import json
import asyncio

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool, BaseTool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import settings
from src.tools.product_catalog_rag import ProductCatalogRAGTool
from src.tools.web_search import WebSearchTool
from src.tools.price_analysis import PriceAnalysisTool


# Define the agent state
class AgentState(TypedDict):
    """State maintained across the agent's execution."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    tools_used: List[str]
    reasoning: str
    final_answer: str
    confidence: float


# Tool input schemas for Ollama function calling
class ProductSearchInput(BaseModel):
    """Input schema for product catalog search."""
    query: str = Field(description="Natural language search query for products")
    category: Optional[str] = Field(default=None, description="Filter by product category")
    brand: Optional[str] = Field(default=None, description="Filter by brand name")
    min_price: Optional[float] = Field(default=None, description="Minimum price filter")
    max_price: Optional[float] = Field(default=None, description="Maximum price filter")
    min_rating: Optional[float] = Field(default=None, description="Minimum rating filter")
    in_stock: Optional[bool] = Field(default=None, description="Filter for products in stock only")
    limit: int = Field(default=5, description="Maximum number of results to return")


class WebSearchInput(BaseModel):
    """Input schema for web search."""
    query: str = Field(description="Search query for web search")
    limit: int = Field(default=5, description="Maximum number of results")


class PriceAnalysisInput(BaseModel):
    """Input schema for price analysis."""
    analysis_type: str = Field(
        default="lowest_margins",
        description="Type of analysis: lowest_margins, highest_margins, below_threshold, category_analysis, brand_analysis"
    )
    category: Optional[str] = Field(default=None, description="Filter by category")
    brand: Optional[str] = Field(default=None, description="Filter by brand")
    threshold: float = Field(default=40.0, description="Margin threshold for below_threshold analysis")
    limit: int = Field(default=10, description="Maximum number of products to return")


class ResearchAgent:
    """
    AI Research Agent that intelligently routes queries to appropriate tools.
    
    Uses LangGraph for orchestration and Ollama for LLM inference.
    """
    
    def __init__(
        self,
        ollama_base_url: str = None,
        ollama_model: str = None
    ):
        """
        Initialize the Research Agent.
        
        Args:
            ollama_base_url: Base URL for Ollama API
            ollama_model: Name of the Ollama model to use
        """
        self.ollama_base_url = ollama_base_url or settings.OLLAMA_BASE_URL
        self.ollama_model = ollama_model or settings.OLLAMA_MODEL
        
        # Initialize tools
        self.product_catalog_tool = ProductCatalogRAGTool()
        self.web_search_tool = WebSearchTool()
        self.price_analysis_tool = PriceAnalysisTool()
        
        # Initialize LLM with Ollama
        self.llm = ChatOllama(
            base_url=self.ollama_base_url,
            model=self.ollama_model,
            temperature=0.1  # Low temperature for more deterministic responses
        )
        
        # Create LangChain tools
        self.tools = self._create_tools()
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _create_tools(self) -> List[BaseTool]:
        """Create LangChain tool wrappers for our custom tools."""
        
        # Product catalog search tool
        @tool("product_catalog_search", args_schema=ProductSearchInput)
        def product_catalog_search(
            query: str,
            category: Optional[str] = None,
            brand: Optional[str] = None,
            min_price: Optional[float] = None,
            max_price: Optional[float] = None,
            min_rating: Optional[float] = None,
            in_stock: Optional[bool] = None,
            limit: int = 5
        ) -> str:
            """
            Search the internal product catalog for products matching the query.
            Use this for finding products by description, features, category, brand, or specifications.
            Returns product details including price, stock, ratings, and margin information.
            """
            result = self.product_catalog_tool.search(
                query=query,
                category=category,
                brand=brand,
                min_price=min_price,
                max_price=max_price,
                min_rating=min_rating,
                in_stock=in_stock,
                limit=limit
            )
            return json.dumps(result, indent=2)
        
        # Web search tool
        @tool("web_search", args_schema=WebSearchInput)
        def web_search(query: str, limit: int = 5) -> str:
            """
            Search the web for market trends, competitor pricing, and external information.
            Use this for current market prices, competitor products, reviews, or trends
            that are not in the internal product catalog.
            """
            result = self.web_search_tool.search_sync(query=query, limit=limit)
            return json.dumps(result, indent=2)
        
        # Price analysis tool
        @tool("price_analysis", args_schema=PriceAnalysisInput)
        def price_analysis(
            analysis_type: str = "lowest_margins",
            category: Optional[str] = None,
            brand: Optional[str] = None,
            threshold: float = 40.0,
            limit: int = 10
        ) -> str:
            """
            Analyze product pricing and profit margins using deterministic calculations.
            Use this for:
            - Finding products with lowest/highest margins
            - Analyzing margins by category or brand
            - Finding products below a margin threshold
            All calculations use the formula: margin = ((price - cost) / price) × 100
            """
            result = self.price_analysis_tool.analyze(
                analysis_type=analysis_type,
                category=category,
                brand=brand,
                threshold=threshold,
                limit=limit
            )
            return json.dumps(result, indent=2)
        
        return [product_catalog_search, web_search, price_analysis]
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create tool node
        tool_node = ToolNode(self.tools)
        
        # Define the agent node
        def agent(state: AgentState) -> Dict[str, Any]:
            """Process the current state and decide next action."""
            messages = state["messages"]
            
            # If this is the first message, add system context
            if len(messages) == 1:
                system_message = SystemMessage(content="""You are an AI Product Research Assistant. Your job is to help users with product research by:

1. **Product Catalog Search** (product_catalog_search): Search our internal product catalog for product information, stock levels, prices, and ratings.

2. **Web Search** (web_search): Search the web for current market prices, competitor information, product reviews, and market trends.

3. **Price Analysis** (price_analysis): Analyze pricing and profit margins using deterministic calculations. This tool calculates margins using the formula: margin = ((price - cost) / price) × 100

**Guidelines:**
- For internal product queries (stock, our prices, our products), use product_catalog_search
- For external market data (competitor prices, market trends, reviews), use web_search  
- For margin analysis and pricing recommendations, use price_analysis
- You may use multiple tools if the query requires combined information
- Always explain your reasoning for which tools you're using
- Provide clear, actionable insights based on the data

**Important:** For price analysis, NEVER calculate margins yourself - always use the price_analysis tool which performs accurate deterministic calculations.""")
                messages = [system_message] + list(messages)
            
            # Call LLM with tools
            response = self.llm_with_tools.invoke(messages)
            
            return {"messages": [response]}
        
        # Define the conditional edge function
        def should_continue(state: AgentState) -> str:
            """Determine if we should continue to tools or end."""
            messages = state["messages"]
            last_message = messages[-1]
            
            # If the LLM made tool calls, continue to tool node
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            
            # Otherwise, end
            return END
        
        # Build the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", agent)
        workflow.add_node("tools", tool_node)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add edges
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END
            }
        )
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    async def aquery(self, query: str) -> Dict[str, Any]:
        """
        Process a query asynchronously.
        
        Args:
            query: The user's query
            
        Returns:
            Dictionary with response, tools used, reasoning, and confidence
        """
        import time
        start_time = time.time()
        
        # Initialize state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=query)],
            "tools_used": [],
            "reasoning": "",
            "final_answer": "",
            "confidence": 0.0
        }
        
        try:
            # Run the graph
            final_state = await asyncio.to_thread(
                lambda: self.graph.invoke(initial_state)
            )
            
            # Extract results
            messages = final_state["messages"]
            tools_used = set()
            
            # Collect tools used from messages
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tools_used.add(tc["name"])
                if isinstance(msg, ToolMessage):
                    tools_used.add(msg.name)
            
            # Get final response
            final_message = messages[-1]
            final_answer = final_message.content if hasattr(final_message, "content") else str(final_message)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return {
                "status": "success",
                "query": query,
                "answer": final_answer,
                "tools_used": list(tools_used),
                "reasoning": f"Used {len(tools_used)} tool(s) to answer the query: {', '.join(tools_used)}" if tools_used else "Answered directly without tool calls",
                "confidence": 0.85 if tools_used else 0.7,
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return {
                "status": "error",
                "query": query,
                "answer": f"I encountered an error while processing your query: {str(e)}",
                "tools_used": [],
                "reasoning": f"Error occurred: {str(e)}",
                "confidence": 0.0,
                "execution_time_ms": execution_time,
                "error": str(e)
            }
    
    def query(self, query: str) -> Dict[str, Any]:
        """
        Process a query synchronously.
        
        Args:
            query: The user's query
            
        Returns:
            Dictionary with response, tools used, reasoning, and confidence
        """
        return asyncio.run(self.aquery(query))


def create_agent(
    ollama_base_url: str = None,
    ollama_model: str = None
) -> ResearchAgent:
    """
    Factory function to create a ResearchAgent.
    
    Args:
        ollama_base_url: Base URL for Ollama API
        ollama_model: Name of the Ollama model to use
        
    Returns:
        Configured ResearchAgent instance
    """
    return ResearchAgent(
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model
    )


# For testing
if __name__ == "__main__":
    agent = create_agent()
    
    test_queries = [
        "What wireless headphones do we have in stock?",
        "What is the current market price for noise-cancelling headphones?",
        "Which products have the lowest profit margins?",
        "Should we adjust AudioMax headphones pricing vs competitors?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print("="*60)
        result = agent.query(query)
        print(f"Tools Used: {result['tools_used']}")
        print(f"Reasoning: {result['reasoning']}")
        print(f"Answer: {result['answer'][:500]}...")
