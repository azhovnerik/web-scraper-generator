"""
AI Agent for Web Scraping Analysis
Uses Thought-Action-Observation cycle to find articles on websites
"""

import os
import re
from typing import List, Dict, TypedDict, Annotated
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode


# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """State for the agent"""
    messages: List
    found_articles: set
    iterations: int
    max_iterations: int
    max_articles: int
    no_new_articles_count: int
    base_url: str
    verbose: bool


# ============================================================================
# TOOLS FOR THE AGENT
# ============================================================================

@tool
def fetch_html(url: str) -> str:
    """
    Fetches HTML content from a URL.

    Args:
        url: The URL to fetch

    Returns:
        HTML content as string (truncated to 50000 chars) or error message
    """
    try:
        response = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        html = response.text

        # Truncate for LLM context
        if len(html) > 50000:
            html = html[:50000] + "\n... (truncated)"

        return f"SUCCESS: Fetched {len(response.text)} chars from {url}\n\nHTML Preview (first 50k chars):\n{html}"
    except Exception as e:
        return f"ERROR: Failed to fetch {url}: {str(e)}"


@tool
def test_css_selector(html_content: str, selector: str) -> str:
    """
    Tests a CSS selector on HTML content.

    Args:
        html_content: HTML content to test (can be partial or full HTML)
        selector: CSS selector to test

    Returns:
        Results showing what the selector matched
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        elements = soup.select(selector)

        if not elements:
            return f"SELECTOR MATCHED: 0 elements"

        results = [f"SELECTOR MATCHED: {len(elements)} elements\n"]

        for i, elem in enumerate(elements[:10], 1):  # Show first 10
            text = elem.get_text(strip=True)[:100]
            href = elem.get('href', '')
            results.append(f"{i}. Tag: {elem.name}, Text: {text}, Href: {href}")

        if len(elements) > 10:
            results.append(f"... and {len(elements) - 10} more")

        return "\n".join(results)
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def find_url_patterns(urls: List[str]) -> str:
    """
    Analyzes a list of URLs to find common patterns.

    Args:
        urls: List of URLs to analyze

    Returns:
        Analysis of URL patterns
    """
    if not urls:
        return "No URLs provided"

    # Extract paths
    paths = [urlparse(url).path for url in urls]

    # Find common segments
    path_segments = {}
    for path in paths:
        segments = [s for s in path.split('/') if s]
        for seg in segments:
            path_segments[seg] = path_segments.get(seg, 0) + 1

    # Sort by frequency
    common_segments = sorted(path_segments.items(), key=lambda x: x[1], reverse=True)

    results = [
        f"ANALYZED {len(urls)} URLs",
        f"\nCommon path segments:",
    ]

    for segment, count in common_segments[:10]:
        percentage = (count / len(urls)) * 100
        results.append(f"  - /{segment}/: {count} times ({percentage:.1f}%)")

    # Find pattern
    if common_segments:
        most_common = common_segments[0][0]
        results.append(f"\nMost likely article pattern: /{most_common}/...")

    return "\n".join(results)


@tool
def parse_html_structure(html_content: str) -> str:
    """
    Analyzes HTML structure to find article-related elements.

    Args:
        html_content: HTML content to analyze

    Returns:
        Structural analysis of the HTML
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        results = ["HTML STRUCTURE ANALYSIS:\n"]

        # Find article containers
        article_tags = soup.find_all(['article', 'div', 'section'], limit=20)
        results.append(f"Found {len(article_tags)} potential article containers")

        # Find links
        links = soup.find_all('a', href=True)
        results.append(f"Found {len(links)} total links")

        # Analyze link patterns (include both singular and plural forms)
        blog_keywords = ['blog', 'blogs', 'article', 'articles', 'post', 'posts', 'news', 'review', 'reviews', 'story', 'stories', 'insight', 'insights']
        blog_links = [a for a in links if any(kw in a.get('href', '').lower() for kw in blog_keywords)]
        results.append(f"Found {len(blog_links)} links with blog-related keywords")

        # Sample some blog links
        if blog_links:
            results.append("\nSample blog-related links:")
            for link in blog_links[:10]:
                href = link.get('href', '')
                text = link.get_text(strip=True)[:50]
                results.append(f"  - {href} ('{text}')")

        # Check for common classes/ids
        common_classes = {}
        for elem in soup.find_all(class_=True):
            for cls in elem.get('class', []):
                if any(kw in cls.lower() for kw in blog_keywords):
                    common_classes[cls] = common_classes.get(cls, 0) + 1

        if common_classes:
            results.append("\nCommon article-related classes:")
            for cls, count in sorted(common_classes.items(), key=lambda x: x[1], reverse=True)[:5]:
                results.append(f"  - .{cls}: {count} elements")

        return "\n".join(results)
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def check_js_rendered_site(html_content: str) -> str:
    """
    Checks if a website is JavaScript-rendered (SPA) with minimal static HTML.
    This tool helps detect sites that require a JavaScript-capable scraper (Selenium/Playwright).

    Args:
        html_content: HTML content to analyze

    Returns:
        Analysis indicating if the site is JS-heavy and whether scraping is feasible
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style tags for content analysis
        for tag in soup(['script', 'style', 'noscript']):
            tag.decompose()

        # Get visible text content
        visible_text = soup.get_text(strip=True)
        text_length = len(visible_text)

        # Count elements
        body = soup.find('body')
        if not body:
            return "⚠️ WARNING: No <body> tag found - unusual HTML structure"

        # Check for SPA indicators
        spa_indicators = []

        # 1. Check for common SPA root divs
        if body.find('div', id='root') or body.find('div', id='app') or body.find('div', id='__next'):
            spa_indicators.append("Found SPA root div (#root, #app, or #__next)")

        # 2. Check for minimal content
        if text_length < 500:
            spa_indicators.append(f"Very minimal text content ({text_length} chars)")

        # 3. Check for React/Vue/Angular indicators
        html_str = str(soup)
        if 'react' in html_str.lower() or 'data-reactroot' in html_str.lower():
            spa_indicators.append("React framework detected")
        if 'vue' in html_str.lower() or 'data-v-' in html_str.lower():
            spa_indicators.append("Vue framework detected")
        if 'ng-app' in html_str.lower() or 'angular' in html_str.lower():
            spa_indicators.append("Angular framework detected")

        # 4. Check script-to-content ratio
        original_soup = BeautifulSoup(html_content, 'html.parser')
        script_tags = original_soup.find_all('script')
        script_count = len(script_tags)
        links_count = len(original_soup.find_all('a', href=True))

        if script_count > 10 and links_count < 20:
            spa_indicators.append(f"High script count ({script_count}) vs low link count ({links_count})")

        # 5. Check for empty body with just one root div
        body_children = [child for child in body.children if child.name is not None]
        if len(body_children) <= 2 and text_length < 1000:
            spa_indicators.append(f"Nearly empty body with {len(body_children)} main elements")

        # Determine verdict
        is_js_heavy = len(spa_indicators) >= 3

        results = ["🔍 JAVASCRIPT RENDERING CHECK:\n"]
        results.append(f"Text content: {text_length} characters")
        results.append(f"Links found: {links_count}")
        results.append(f"Script tags: {script_count}")
        results.append(f"Body structure: {len(body_children)} main elements")

        if spa_indicators:
            results.append("\n⚠️ SPA/JS-Rendering Indicators:")
            for indicator in spa_indicators:
                results.append(f"  - {indicator}")

        if is_js_heavy:
            results.append("\n❌ VERDICT: This appears to be a JavaScript-rendered site (SPA)")
            results.append("⚠️ Standard scraping (requests library) will NOT work")
            results.append("✅ RECOMMENDATION: Use Selenium or Playwright for this site")
            results.append("\nYou should ABORT the search and inform the user that this site requires JS-capable scraping.")
        else:
            results.append("\n✅ VERDICT: Site has sufficient static HTML content")
            results.append("✅ Standard scraping should work - proceed with article search")

        return "\n".join(results)
    except Exception as e:
        return f"ERROR: {str(e)}"


# ============================================================================
# AGENT LOGIC
# ============================================================================

def create_agent(
    base_url: str,
    max_iterations: int = 10,
    verbose: bool = True
):
    """
    Creates an AI agent for finding articles on a website.

    Args:
        base_url: The base URL of the website to analyze
        max_iterations: Maximum number of iterations (default: 10)
        verbose: Whether to print detailed logs (default: True)

    Returns:
        Compiled LangGraph agent
    """

    # Initialize OpenAI chat model via OpenRouter
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment")

    llm = ChatOpenAI(
        model="anthropic/claude-3.5-sonnet",
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.1
    )

    # Bind tools to LLM
    tools = [fetch_html, test_css_selector, find_url_patterns, parse_html_structure, check_js_rendered_site]
    llm_with_tools = llm.bind_tools(tools)

    # System prompt for the agent
    system_prompt = f"""You are an expert web scraping analyst. Your task is to find article/blog post URLs on the website: {base_url}

GOAL: Find approximately 20-30 article URLs (enough to identify patterns for scraper generation).
You don't need to find ALL articles on the site - just a representative sample.

Use a systematic Thought-Action-Observation approach:

**THOUGHT**: Analyze what you know so far and decide what to do next
**ACTION**: Use tools to gather more information
**OBSERVATION**: Analyze the results

TOOLS AVAILABLE:
1. fetch_html(url) - Fetch HTML from any page
2. test_css_selector(html, selector) - Test CSS selectors
3. find_url_patterns(urls) - Analyze URL patterns
4. parse_html_structure(html) - Analyze HTML structure
5. check_js_rendered_site(html) - Check if site is JavaScript-rendered (SPA)

STRATEGY:
1. Start by fetching the homepage
2. **IMMEDIATELY use the check_js_rendered_site() tool to test if site is JS-rendered**
   - Pass the HTML content from step 1 to this tool
   - Wait for the tool's verdict before making any decisions
   - ONLY if the tool explicitly says "This appears to be a JavaScript-rendered site (SPA)", then ABORT and respond with: "JS_RENDERED_SITE: This site requires Selenium/Playwright"
   - If the tool says "Site has sufficient static HTML content", then proceed normally
   - Do NOT make assumptions about JS-rendering without using this tool
3. If site has static HTML (verified by tool), proceed with article search:
   - Look for blog/articles/news pages
   - Fetch those pages to find article links
   - Check pagination (page/2/, page/3/, etc.) - but only 2-3 pages is enough
   - Verify found URLs match article patterns
   - Stop when you have 20-30 articles (sufficient sample)

IMPORTANT:
- **ALWAYS check for JS-rendering on the first iteration** - this saves tokens
- Focus on finding INDIVIDUAL article URLs, not category/tag pages
- Check both homepage and any blog listing pages
- Look for pagination but don't need to exhaust it (2-3 pages is sufficient)
- URLs should be unique and point to actual articles
- Quality over quantity: 20-30 good examples is perfect

When you have found enough articles (20-30), respond with:
FINAL_ANSWER: [list of article URLs]

If the site is JS-rendered, respond with:
JS_RENDERED_SITE: This site requires Selenium/Playwright
"""

    def should_continue(state: AgentState) -> str:
        """Determine if agent should continue or stop"""
        messages = state["messages"]
        last_message = messages[-1] if messages else None

        # Check if we found enough articles (early stopping)
        if len(state["found_articles"]) >= state["max_articles"]:
            if state["verbose"]:
                print(f"\n✅ Found enough articles ({len(state['found_articles'])}/{state['max_articles']})\n")
            return "end"

        # Check if we hit max iterations
        if state["iterations"] >= state["max_iterations"]:
            if state["verbose"]:
                print(f"\n🛑 Max iterations ({state['max_iterations']}) reached\n")
            return "end"

        # Check if agent says it's done
        if isinstance(last_message, AIMessage):
            content = last_message.content if isinstance(last_message.content, str) else ""
            # Only detect JS-rendered site if it's a definitive statement (starts the line)
            if content.strip().startswith("JS_RENDERED_SITE:"):
                if state["verbose"]:
                    print("\n⚠️ JS-RENDERED SITE DETECTED - Aborting\n")
                return "end"
            # Check for completion
            if "final_answer" in content.lower() or "found all" in content.lower():
                if state["verbose"]:
                    print("\n✅ Agent indicates it's done\n")
                return "end"

        # Check tool calls
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "continue"

        # Check if no new articles for multiple iterations
        if state["no_new_articles_count"] >= 3:
            if state["verbose"]:
                print("\n🛑 No new articles found for 3 iterations\n")
                return "end"

        return "end"

    def call_model(state: AgentState) -> AgentState:
        """Call the LLM with current state"""
        messages = state["messages"]
        iteration = state["iterations"] + 1

        if state["verbose"]:
            print(f"\n{'='*80}")
            print(f"🤖 ITERATION {iteration}/{state['max_iterations']}")
            print(f"{'='*80}\n")

        # Add system message if first iteration
        if not messages:
            messages = [SystemMessage(content=system_prompt)]
            messages.append(HumanMessage(content=f"Find all article URLs on {state['base_url']}. Start by fetching the homepage."))

        response = llm_with_tools.invoke(messages)

        # Print thought process
        if state["verbose"] and isinstance(response.content, str):
            print(f"💭 THOUGHT:\n{response.content}\n")

        # Print actions
        if state["verbose"] and response.tool_calls:
            print(f"🔧 ACTIONS:")
            for tool_call in response.tool_calls:
                print(f"  - {tool_call['name']}({tool_call['args']})")
            print()

        return {
            **state,
            "messages": messages + [response],
            "iterations": iteration
        }

    def call_tools(state: AgentState) -> AgentState:
        """Execute tool calls and update state"""
        messages = state["messages"]
        last_message = messages[-1]

        # Execute tools
        tool_node = ToolNode(tools)
        tool_results = tool_node.invoke({"messages": [last_message]})

        # Print observations
        if state["verbose"]:
            print(f"👁️  OBSERVATIONS:")
            for msg in tool_results["messages"]:
                if hasattr(msg, 'content'):
                    content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
                    print(f"{content}\n")

        # Extract URLs from observations
        new_articles = set()
        for msg in tool_results["messages"]:
            if hasattr(msg, 'content'):
                content = msg.content

                # If content contains HTML, parse it to extract article links
                if '<html' in content.lower() or '<!doctype' in content.lower():
                    try:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(content, 'html.parser')

                        # Find all links
                        for link in soup.find_all('a', href=True):
                            href = link.get('href', '')
                            # Filter for article URLs (include both singular and plural forms)
                            if any(pattern in href.lower() for pattern in ['/blog/', '/blogs/', '/article/', '/articles/', '/post/', '/posts/', '/news/', '/review/', '/reviews/', '/story/', '/stories/', '/insight/', '/insights/']):
                                # Exclude listing/category/tag/pagination/industry pages
                                if not any(skip in href.lower() for skip in ['/category/', '/categories/', '/tag/', '/tags/', '/page/', '/author/', '/authors/', '/feed', '/industries/']):
                                    # Exclude resource files
                                    if not href.endswith(('.css', '.js', '.png', '.jpg', '.gif', '.webp', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.mp4', '.mp3', '.pdf', '.zip', '.xml', '.json')):
                                        # Exclude resource path patterns
                                        if not any(pattern in href.lower() for pattern in ['/_hu', '/images/', '/assets/', '/static/', '/media/', '/css/', '/js/']):
                                            # Must have path segments (not just /blog/)
                                            if href.count('/') >= 2 and not href.endswith(('/blog/', '/blogs/', '/article/', '/articles/', '/post/', '/posts/', '/news/', '/review/', '/reviews/', '/story/', '/stories/', '/insight/', '/insights/')):
                                                full_url = urljoin(state['base_url'], href)
                                                new_articles.add(full_url)
                    except:
                        pass

                # Also look for URLs in plain text output (from parse_html_structure, etc.)
                urls = re.findall(r'(?:https?://[\w\-./]+|/[\w\-./]+)', content)
                for url in urls:
                    # Filter for article URLs (include both singular and plural forms)
                    if any(pattern in url.lower() for pattern in ['/blog/', '/blogs/', '/article/', '/articles/', '/post/', '/posts/', '/news/', '/review/', '/reviews/', '/story/', '/stories/', '/insight/', '/insights/']):
                        # Exclude listing/category/tag/pagination/industry pages
                        if not any(skip in url.lower() for skip in ['/category/', '/categories/', '/tag/', '/tags/', '/page/', '/author/', '/authors/', '/feed', '/industries/']):
                            # Exclude resource files
                            if not url.endswith(('.css', '.js', '.png', '.jpg', '.gif', '.webp', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.mp4', '.mp3', '.pdf', '.zip', '.xml', '.json')):
                                # Exclude resource path patterns
                                if not any(pattern in url.lower() for pattern in ['/_hu', '/images/', '/assets/', '/static/', '/media/', '/css/', '/js/']):
                                    # Must have path segments
                                    if url.count('/') >= 2 and not url.endswith(('/blog/', '/blogs/', '/article/', '/articles/', '/post/', '/posts/', '/news/', '/review/', '/reviews/', '/story/', '/stories/', '/insight/', '/insights/')):
                                        full_url = urljoin(state['base_url'], url)
                                        new_articles.add(full_url)

        # Update found articles
        old_count = len(state["found_articles"])
        updated_articles = state["found_articles"] | new_articles
        new_count = len(updated_articles)

        # Track if we found new articles
        no_new_count = state["no_new_articles_count"]
        if new_count > old_count:
            no_new_count = 0
            if state["verbose"]:
                print(f"✨ Found {new_count - old_count} new articles! Total: {new_count}\n")
        else:
            no_new_count += 1
            if state["verbose"]:
                print(f"⚠️  No new articles this iteration. Strike {no_new_count}/3\n")

        return {
            **state,
            "messages": messages + tool_results["messages"],
            "found_articles": updated_articles,
            "no_new_articles_count": no_new_count
        }

    # Build graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", call_tools)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "tools",
            "end": END
        }
    )
    workflow.add_edge("tools", "agent")

    # Compile graph with increased recursion limit
    # Each iteration = 2 steps (agent + tools)
    # max_iterations=15 → needs ~30 steps
    # Set recursion_limit=50 for safety margin
    return workflow.compile()


def run_agent(
    base_url: str,
    max_iterations: int = 15,
    max_articles: int = 30,
    verbose: bool = True
) -> List[str]:
    """
    Runs the AI agent to find articles.

    Args:
        base_url: The base URL to analyze
        max_iterations: Maximum iterations (default: 15, provides buffer for complex sites)
        max_articles: Maximum articles to find (default: 30, sufficient for selector generation)
        verbose: Print detailed logs (default: True)

    Returns:
        List of found article URLs (up to max_articles)

    Note:
        With max_articles=30, the agent typically stops in 4-7 iterations via early stopping.
        max_iterations=15 provides safety margin for complex site structures.
    """
    print(f"\n🚀 Starting AI Agent for {base_url}")
    print(f"Max iterations: {max_iterations}, Max articles: {max_articles}")
    print(f"{'='*80}\n")

    # Create and run agent
    agent = create_agent(base_url, max_iterations, verbose)

    initial_state = {
        "messages": [],
        "found_articles": set(),
        "iterations": 0,
        "max_iterations": max_iterations,
        "max_articles": max_articles,
        "no_new_articles_count": 0,
        "base_url": base_url,
        "verbose": verbose
    }

    # Invoke with increased recursion limit
    # max_iterations=15 → ~30 graph steps needed (agent + tools per iteration)
    final_state = agent.invoke(
        initial_state,
        config={"recursion_limit": 50}  # Sufficient for max_iterations=15 with safety margin
    )

    # Check if agent detected a JS-rendered site
    messages = final_state.get("messages", [])
    for msg in messages:
        if isinstance(msg, AIMessage):
            content = str(msg.content) if hasattr(msg, 'content') else ""
            if content.strip().startswith("JS_RENDERED_SITE:"):
                # Calculate token usage even for JS-rendered sites
                total_input_tokens = 0
                total_output_tokens = 0
                for m in messages:
                    if hasattr(m, 'usage_metadata') and m.usage_metadata:
                        total_input_tokens += m.usage_metadata.get('input_tokens', 0)
                        total_output_tokens += m.usage_metadata.get('output_tokens', 0)
                    elif hasattr(m, 'response_metadata') and m.response_metadata:
                        usage = m.response_metadata.get('usage', {})
                        total_input_tokens += usage.get('prompt_tokens', 0)
                        total_output_tokens += usage.get('completion_tokens', 0)

                total_tokens = total_input_tokens + total_output_tokens

                print(f"\n{'='*80}")
                print(f"⚠️ JS-RENDERED SITE DETECTED")
                print(f"{'='*80}")
                print(f"❌ This site uses JavaScript to render content (SPA/Single Page Application)")
                print(f"⚠️ Standard scraping (requests library) will NOT work on this site")
                print(f"✅ RECOMMENDATION: Use Selenium or Playwright to scrape this site")
                print(f"\nToken usage saved by early detection: ~{(max_iterations - final_state['iterations']) * 1500:,} tokens")
                if total_tokens > 0:
                    print(f"Tokens used: {total_tokens:,} (input: {total_input_tokens:,}, output: {total_output_tokens:,})")
                print(f"{'='*80}\n")

                raise ValueError("JS_RENDERED_SITE: This site requires Selenium or Playwright. "
                               "Standard requests-based scraping will not work on JavaScript-rendered sites.")

    articles = sorted(list(final_state["found_articles"]))

    # Calculate token usage from messages
    total_input_tokens = 0
    total_output_tokens = 0

    for msg in final_state["messages"]:
        if hasattr(msg, 'usage_metadata') and msg.usage_metadata:
            total_input_tokens += msg.usage_metadata.get('input_tokens', 0)
            total_output_tokens += msg.usage_metadata.get('output_tokens', 0)
        elif hasattr(msg, 'response_metadata') and msg.response_metadata:
            usage = msg.response_metadata.get('usage', {})
            total_input_tokens += usage.get('prompt_tokens', 0)
            total_output_tokens += usage.get('completion_tokens', 0)

    total_tokens = total_input_tokens + total_output_tokens

    print(f"\n{'='*80}")
    print(f"🎉 AGENT FINISHED - Article Finding")
    print(f"{'='*80}")
    print(f"Total iterations: {final_state['iterations']}")
    print(f"Found articles: {len(articles)}")
    if total_tokens > 0:
        print(f"Tokens used: {total_tokens:,} (input: {total_input_tokens:,}, output: {total_output_tokens:,})")
    print(f"{'='*80}\n")

    return articles


def generate_selectors_with_agent(
    base_url: str,
    article_urls: List[str],
    homepage_html: str,
    blog_page_html: str = None,
    max_iterations: int = 8,
    verbose: bool = True
) -> Dict:
    """
    Uses AI agent to generate CSS selectors for scraping.

    Args:
        base_url: The base URL of the website
        article_urls: List of article URLs found in phase 1
        homepage_html: HTML of the homepage
        blog_page_html: HTML of blog listing page (if exists)
        max_iterations: Maximum iterations (default: 8)
        verbose: Print detailed logs (default: True)

    Returns:
        Dict with generated selectors
    """
    print(f"\n🚀 Starting AI Agent - Selector Generation")
    print(f"Max iterations: {max_iterations}")
    print(f"{'='*80}\n")

    # Initialize OpenAI chat model via OpenRouter
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment")

    llm = ChatOpenAI(
        model="anthropic/claude-3.5-sonnet",
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.1
    )

    # Bind tools
    tools = [fetch_html, test_css_selector, parse_html_structure]
    llm_with_tools = llm.bind_tools(tools)

    # System prompt for selector generation
    sample_urls = article_urls[:3] if len(article_urls) > 3 else article_urls

    system_prompt = f"""You are an expert CSS selector engineer. Your task is to generate precise CSS selectors for scraping articles from: {base_url}

I have found {len(article_urls)} article URLs. Here are some examples:
{chr(10).join(f"  - {url}" for url in sample_urls)}

Your goal is to generate these CSS selectors:
1. **article_links_selector** - Selector to find article links on listing pages
2. **title_selector** - Selector to extract article title from article page
3. **content_selector** - Selector to extract article content from article page
4. **date_selector** - Selector to extract publication date (check meta tags too)
5. **author_selector** - Selector to extract author name (check meta tags too)

Use a systematic Thought-Action-Observation approach:

**THOUGHT**: Analyze what you've learned and decide what to test next
**ACTION**: Use tools to test selectors and fetch HTML
**OBSERVATION**: Analyze results and refine approach

TOOLS AVAILABLE:
1. fetch_html(url) - Fetch HTML from article pages to analyze structure
2. test_css_selector(html, selector) - Test if a selector works correctly
3. parse_html_structure(html) - Analyze HTML structure for patterns

STRATEGY:
1. Fetch 2-3 sample articles to analyze their structure
2. Look for common patterns in article titles, content, dates, authors
3. Generate candidate selectors
4. Test selectors on multiple articles to ensure they work
5. Refine selectors based on test results

IMPORTANT:
- Selectors must work across ALL articles, not just one
- Prefer simpler selectors when possible (article h1 vs div.container > div > h1)
- For dates/authors, check <meta> tags first (property="article:published_time", etc.)
- Test each selector on at least 2 different articles before confirming

When you have validated all selectors, respond with:
FINAL_SELECTORS:
article_links_selector: <selector>
title_selector: <selector>
content_selector: <selector>
date_selector: <selector>
author_selector: <selector>
"""

    class SelectorState(TypedDict):
        messages: List
        iterations: int
        max_iterations: int
        selectors: Dict
        base_url: str
        article_urls: List[str]
        verbose: bool

    def should_continue_selectors(state: SelectorState) -> str:
        messages = state["messages"]
        last_message = messages[-1] if messages else None

        if state["iterations"] >= state["max_iterations"]:
            if state["verbose"]:
                print(f"\n🛑 Max iterations ({state['max_iterations']}) reached\n")
            return "end"

        if isinstance(last_message, AIMessage):
            content = last_message.content.lower() if isinstance(last_message.content, str) else ""
            if "final_selectors" in content:
                if state["verbose"]:
                    print("\n✅ Agent has generated selectors\n")
                return "end"

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "continue"

        return "end"

    def call_model_selectors(state: SelectorState) -> SelectorState:
        messages = state["messages"]
        iteration = state["iterations"] + 1

        if state["verbose"]:
            print(f"\n{'='*80}")
            print(f"🤖 ITERATION {iteration}/{state['max_iterations']}")
            print(f"{'='*80}\n")

        if not messages:
            messages = [SystemMessage(content=system_prompt)]
            messages.append(HumanMessage(content=f"Generate CSS selectors for scraping {state['base_url']}. Start by fetching 2-3 sample articles to analyze their structure."))

        response = llm_with_tools.invoke(messages)

        if state["verbose"] and isinstance(response.content, str):
            print(f"💭 THOUGHT:\n{response.content}\n")

        if state["verbose"] and response.tool_calls:
            print(f"🔧 ACTIONS:")
            for tool_call in response.tool_calls:
                print(f"  - {tool_call['name']}({list(tool_call['args'].keys())})")
            print()

        return {
            **state,
            "messages": messages + [response],
            "iterations": iteration
        }

    def call_tools_selectors(state: SelectorState) -> SelectorState:
        messages = state["messages"]
        last_message = messages[-1]

        tool_node = ToolNode(tools)
        tool_results = tool_node.invoke({"messages": [last_message]})

        if state["verbose"]:
            print(f"👁️  OBSERVATIONS:")
            for msg in tool_results["messages"]:
                if hasattr(msg, 'content'):
                    content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
                    print(f"{content}\n")

        return {
            **state,
            "messages": messages + tool_results["messages"]
        }

    # Build selector generation graph
    workflow = StateGraph(SelectorState)
    workflow.add_node("agent", call_model_selectors)
    workflow.add_node("tools", call_tools_selectors)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue_selectors,
        {"continue": "tools", "end": END}
    )
    workflow.add_edge("tools", "agent")

    agent = workflow.compile()

    initial_state = {
        "messages": [],
        "iterations": 0,
        "max_iterations": max_iterations,
        "selectors": {},
        "base_url": base_url,
        "article_urls": article_urls,
        "verbose": verbose
    }

    # Invoke with increased recursion limit for selector generation
    final_state = agent.invoke(
        initial_state,
        config={"recursion_limit": 50}
    )

    # Extract selectors from final message
    selectors = _extract_selectors_from_messages(final_state["messages"])

    print(f"\n{'='*80}")
    print(f"🎉 AGENT FINISHED - Selector Generation")
    print(f"{'='*80}")
    print(f"Total iterations: {final_state['iterations']}")
    print(f"Generated selectors: {len(selectors)}")
    print(f"{'='*80}\n")

    return selectors


def _extract_selectors_from_messages(messages: List) -> Dict:
    """Extract selectors from agent messages"""
    selectors = {}

    # Look for FINAL_SELECTORS in the last messages
    for message in reversed(messages):
        if isinstance(message, AIMessage) and isinstance(message.content, str):
            content = message.content
            if "FINAL_SELECTORS" in content or "final_selectors" in content.lower():
                # Parse selectors from content
                lines = content.split('\n')
                for line in lines:
                    if ':' in line:
                        for key in ['article_links_selector', 'title_selector', 'content_selector',
                                   'date_selector', 'author_selector']:
                            if key in line.lower():
                                # Extract selector value
                                parts = line.split(':', 1)
                                if len(parts) == 2:
                                    selector = parts[1].strip().strip('`').strip()
                                    if selector and selector != '<selector>':
                                        selectors[key] = selector
                break

    return selectors


# For testing
if __name__ == "__main__":
    # Test the agent
    articles = run_agent("http://localhost:8888", max_iterations=10)

    print("Found articles:")
    for i, url in enumerate(articles, 1):
        print(f"{i}. {url}")
