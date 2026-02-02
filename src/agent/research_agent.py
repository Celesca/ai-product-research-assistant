from typing import Dict, Any, List, Optional, TypedDict, Annotated, Sequence
from typing_extensions import TypedDict
import operator
import json
import asyncio
import logging

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool, BaseTool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import settings
from src.models.schemas import ProductSearchInput, WebSearchInput, PriceAnalysisInput
from src.agent.tools.product_catalog_rag import ProductCatalogRAGTool
from src.agent.tools.web_search import WebSearchTool
from src.agent.tools.price_analysis import PriceAnalysisTool

# Configure logging for agent thinking visibility
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)


# Define the agent state
class AgentState(TypedDict):
    """State maintained across the agent's execution."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    tools_used: List[str]
    reasoning: str
    final_answer: str
    confidence: float


# Tool input schemas are now imported from src.models.schemas


class ResearchAgent:   
    def __init__(
        self,
        ollama_base_url: str = None,
        ollama_model: str = None
    ):

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
            """Search our INTERNAL product catalog database for products we sell.

USE THIS TOOL WHEN the user asks about:
- Products WE have/sell/stock ("What headphones do we have?")
- Our inventory or stock levels ("Is X in stock?")
- Our product details, prices, ratings ("Show me our electronics under $100")
- Products by brand/category in OUR catalog ("AudioMax products", "our fitness equipment")
- Finding specific products WE carry ("Do we sell wireless earbuds?")

DO NOT USE when user asks about:
- Competitor prices or market prices (use web_search)
- External reviews or market trends (use web_search)
- Profit margins or margin analysis (use price_analysis)

Returns: Product details including name, price, cost, stock quantity, ratings, and category."""
            logger.info(f"🔍 [TOOL] product_catalog_search executing...")
            logger.info(f"   └─ Query: '{query}' | Filters: category={category}, brand={brand}")
            
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
            
            # Log result summary
            if result.get("status") == "success":
                logger.info(f"   ✓ Found {result.get('total_results', 0)} products")
            else:
                logger.warning(f"   ⚠ Tool returned: {result.get('status')}")
            
            return json.dumps(result, indent=2)
        
        # Web search tool
        @tool("web_search", args_schema=WebSearchInput)
        def web_search(query: str, limit: int = 5) -> str:
            """Search the EXTERNAL web for market information, competitors, and trends.

USE THIS TOOL WHEN the user asks about:
- Market prices or competitor prices ("What's the market price for X?")
- External product reviews ("Latest reviews for Sony WH-1000XM5")
- Market trends ("Trending products in fitness")
- Competitor information ("What are competitors charging?")
- Industry news or external data not in our catalog
- Price comparisons with the market ("How do our prices compare?")

DO NOT USE when user asks about:
- Our own products/inventory (use product_catalog_search)
- Our profit margins (use price_analysis)
- Products we sell or have in stock (use product_catalog_search)

Returns: Web search results with titles, URLs, content snippets, and AI-generated summary."""
            logger.info(f"🌐 [TOOL] web_search executing...")
            logger.info(f"   └─ Query: '{query}' | Limit: {limit}")
            
            result = self.web_search_tool.search_sync(query=query, limit=limit)
            
            # Log result summary
            if result.get("status") == "success":
                logger.info(f"   ✓ Found {len(result.get('results', []))} web results")
            else:
                logger.warning(f"   ⚠ Tool returned: {result.get('status')}")
            
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
            """Analyze profit margins and pricing for products in our catalog.

USE THIS TOOL WHEN the user asks about:
- Profit margins ("Which products have lowest margins?", "What's the margin on X?")
- Margin analysis by category/brand ("Average margin for Electronics")
- Products below/above margin thresholds ("Products with margins below 40%")
- Pricing recommendations based on margins
- Profitability analysis ("Most/least profitable products")
- Cost vs price analysis

ANALYSIS TYPES available:
- "lowest_margins": Find products with lowest profit margins
- "highest_margins": Find products with highest profit margins  
- "below_threshold": Find products with margins below threshold (default 40%)
- "above_threshold": Find products with margins above threshold
- "category_summary": Get margin statistics for a category
- "brand_summary": Get margin statistics for a brand

DO NOT USE when user asks about:
- Finding products by features (use product_catalog_search)
- Market/competitor prices (use web_search)
- Stock levels or ratings (use product_catalog_search)

Returns: Margin calculations using formula: margin = ((price - cost) / price) × 100"""
            logger.info(f"📊 [TOOL] price_analysis executing...")
            logger.info(f"   └─ Type: {analysis_type} | Category: {category} | Brand: {brand}")
            
            result = self.price_analysis_tool.analyze(
                analysis_type=analysis_type,
                category=category,
                brand=brand,
                threshold=threshold,
                limit=limit
            )
            
            # Log result summary
            if result.get("status") == "success":
                logger.info(f"   ✓ Analyzed {result.get('total_products_analyzed', 0)} products")
            else:
                logger.warning(f"   ⚠ Tool returned: {result.get('status')}")
            
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
            
            # Log incoming query
            if len(messages) == 1:
                logger.info("=" * 60)
                logger.info("🧠 AGENT THINKING STARTED")
                logger.info(f"📝 User Query: {messages[0].content}")
                logger.info("=" * 60)
            
            # If this is the first message, add system context (Few-shot prompt)
            if len(messages) == 1:
                system_message = SystemMessage(content="""You are an AI Product Research Assistant for an e-commerce company. You help users research products, analyze pricing, and understand market trends.

## YOUR TOOLS

### 1. product_catalog_search
Search OUR internal product database. Use for:
- "What [products] do we have/sell/stock?" → Search our catalog
- "Show me our [category] products" → Search with category filter
- "Do we carry [brand]?" → Search with brand filter
- "Products under $X" → Search with price filter
- "What's in stock?" → Search with in_stock=true

### 2. web_search  
Search the EXTERNAL web. Use for:
- "What's the market price for X?" → External pricing
- "Competitor prices for X" → Market research
- "Latest reviews for [product]" → External reviews
- "Trending products in [category]" → Market trends
- "How do our prices compare?" → Needs web_search for market data

### 3. price_analysis
Analyze profit MARGINS. Use for:
- "Which products have lowest/highest margins?" → margin analysis
- "Products with margins below X%" → threshold analysis
- "Average margin for [category/brand]" → summary analysis
- "Most/least profitable products" → margin ranking
- "Should we adjust pricing?" → needs margin data

## ROUTING DECISION TREE

```
Is the query about MARGINS/PROFITABILITY/COST analysis?
  YES → price_analysis
  NO ↓

Is the query about EXTERNAL market/competitors/trends/reviews?
  YES → web_search
  NO ↓

Is the query about OUR products/inventory/catalog?
  YES → product_catalog_search
  NO ↓

Need MULTIPLE perspectives (our prices vs market)?
  YES → Use multiple tools
```

## MULTI-TOOL QUERIES
Some queries need multiple tools:
- "Should we lower AudioMax prices vs competitors?" 
  → product_catalog_search (our prices) + web_search (competitor prices)
- "Which of our low-margin products have good market demand?"
  → price_analysis (margins) + web_search (market demand)

## RESPONSE FORMAT
After getting tool results:
1. Provide a BRIEF summary (2-3 sentences max)
2. Highlight key insights and actionable findings
3. Do NOT list every product - structured data is returned separately
4. Be specific with numbers and facts from the tool results

## IMPORTANT
- NEVER calculate margins yourself - always use price_analysis tool
- For margin questions, set appropriate analysis_type parameter
- Use filters (category, brand, price range) when the user specifies them""")
                messages = [system_message] + list(messages)
                logger.info("📋 System prompt injected")
            
            # Call LLM with tools
            logger.info("🤖 Calling LLM...")
            response = self.llm_with_tools.invoke(messages)
            
            # Log LLM response
            if hasattr(response, "tool_calls") and response.tool_calls:
                logger.info(f"🔧 LLM decided to use {len(response.tool_calls)} tool(s):")
                for tc in response.tool_calls:
                    logger.info(f"   └─ Tool: {tc['name']}")
                    logger.info(f"      Args: {json.dumps(tc['args'], indent=2)}")
            else:
                # Final answer
                answer_preview = response.content[:200] + "..." if len(response.content) > 200 else response.content
                logger.info(f"💬 LLM Final Answer: {answer_preview}")
            
            return {"messages": [response]}
        
        # Define the conditional edge function
        def should_continue(state: AgentState) -> str:
            """Determine if we should continue to tools or end."""
            messages = state["messages"]
            last_message = messages[-1]
            
            # If the LLM made tool calls, continue to tool node
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                logger.info("➡️  Decision: Continue to TOOLS")
                return "tools"
            
            # Otherwise, end
            logger.info("✅ Decision: END (final answer ready)")
            logger.info("=" * 60)
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
    
    async def aquery(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Process a query asynchronously.
        
        Args:
            query: The user's query
            conversation_history: Optional list of previous messages in format [{"role": "user"|"assistant", "content": "..."}]
            
        Returns:
            Dictionary with structured response including products, sources, and confidence
        """
        import time
        start_time = time.time()
        
        # Build message list with conversation history
        messages = []
        
        # Add previous conversation messages if provided
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
            logger.info(f"📜 Loaded {len(conversation_history)} previous messages for context")
        
        # Add current query
        messages.append(HumanMessage(content=query))
        
        # Initialize state
        initial_state: AgentState = {
            "messages": messages,
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
            products = []
            sources = []
            confidence_scores = []
            
            # Collect tools used and extract structured data from tool messages
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tools_used.add(tc["name"])
                
                if isinstance(msg, ToolMessage):
                    tools_used.add(msg.name)
                    
                    # Parse tool result content
                    try:
                        tool_result = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                        
                        # Extract products from product_catalog_search
                        if msg.name == "product_catalog_search" and tool_result.get("status") == "success":
                            for p in tool_result.get("products", []):
                                products.append({
                                    "product_id": p.get("product_id", ""),
                                    "product_name": p.get("product_name", ""),
                                    "brand": p.get("brand", ""),
                                    "category": p.get("category", ""),
                                    "current_price": p.get("current_price", 0),
                                    "cost": p.get("cost"),
                                    "stock_quantity": p.get("stock_quantity"),
                                    "average_rating": p.get("average_rating"),
                                    "margin_percentage": p.get("margin_percentage"),
                                    "relevance_score": p.get("score")
                                })
                            if tool_result.get("confidence"):
                                confidence_scores.append(tool_result["confidence"])
                        
                        # Extract sources from web_search
                        elif msg.name == "web_search" and tool_result.get("status") == "success":
                            for r in tool_result.get("results", []):
                                sources.append({
                                    "title": r.get("title", ""),
                                    "url": r.get("url"),
                                    "content": r.get("content"),
                                    "source_type": "web",
                                    "relevance_score": r.get("score")
                                })
                            # Add answer as a source if available
                            if tool_result.get("answer"):
                                sources.insert(0, {
                                    "title": f"Web Search Summary: {query}",
                                    "url": None,
                                    "content": tool_result["answer"],
                                    "source_type": "web_summary",
                                    "relevance_score": 1.0
                                })
                        
                        # Extract products from price_analysis
                        elif msg.name == "price_analysis" and tool_result.get("status") == "success":
                            for p in tool_result.get("products", []):
                                # Check if product already exists
                                existing_ids = {prod["product_id"] for prod in products}
                                if p.get("product_id") not in existing_ids:
                                    products.append({
                                        "product_id": p.get("product_id", ""),
                                        "product_name": p.get("product_name", ""),
                                        "brand": p.get("brand", ""),
                                        "category": p.get("category", ""),
                                        "current_price": p.get("current_price", 0),
                                        "cost": p.get("cost"),
                                        "stock_quantity": None,
                                        "average_rating": None,
                                        "margin_percentage": p.get("margin_percentage"),
                                        "relevance_score": None
                                    })
                            # Add analysis summary as source
                            sources.append({
                                "title": f"Price Analysis: {tool_result.get('analysis_type', 'margins')}",
                                "url": None,
                                "content": f"Analyzed {tool_result.get('total_products_analyzed', 0)} products",
                                "source_type": "analysis",
                                "relevance_score": 1.0
                            })
                    except (json.JSONDecodeError, TypeError):
                        # If parsing fails, continue without structured data
                        pass
            
            # Get final response from LLM
            final_message = messages[-1]
            final_answer = final_message.content if hasattr(final_message, "content") else str(final_message)
            
            # Calculate overall confidence
            if confidence_scores:
                overall_confidence = sum(confidence_scores) / len(confidence_scores)
            elif products:
                # Calculate from product relevance scores
                product_scores = [p.get("relevance_score", 0.8) for p in products if p.get("relevance_score")]
                overall_confidence = sum(product_scores) / len(product_scores) if product_scores else 0.85
            elif tools_used:
                overall_confidence = 0.75
            else:
                overall_confidence = 0.6
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return {
                "status": "success",
                "query": query,
                "answer": final_answer,
                "products": products,
                "sources": sources,
                "confidence": round(overall_confidence, 2),
                "tools_used": list(tools_used),
                "reasoning": f"Used {len(tools_used)} tool(s) to answer the query: {', '.join(tools_used)}" if tools_used else "Answered directly without tool calls",
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return {
                "status": "error",
                "query": query,
                "answer": f"I encountered an error while processing your query: {str(e)}",
                "products": [],
                "sources": [],
                "confidence": 0.0,
                "tools_used": [],
                "reasoning": f"Error occurred: {str(e)}",
                "execution_time_ms": execution_time,
                "error": str(e)
            }
    
    def query(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Process a query synchronously.
        
        Args:
            query: The user's query
            conversation_history: Optional list of previous messages for context
            
        Returns:
            Dictionary with response, tools used, reasoning, and confidence
        """
        return asyncio.run(self.aquery(query, conversation_history=conversation_history))


def create_agent(
    ollama_base_url: str = None,
    ollama_model: str = None
) -> ResearchAgent:
    return ResearchAgent(
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model
    )