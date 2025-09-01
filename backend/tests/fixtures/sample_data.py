"""Sample test data for RAG system tests"""

from models import Course, Lesson, CourseChunk
from vector_store import SearchResults

# Sample courses for testing
SAMPLE_COURSE_1 = Course(
    title="Introduction to Machine Learning",
    course_link="https://example.com/ml-course",
    instructor="Dr. Jane Smith",
    lessons=[
        Lesson(lesson_number=0, title="Course Overview", lesson_link="https://example.com/ml-lesson-0"),
        Lesson(lesson_number=1, title="Linear Regression", lesson_link="https://example.com/ml-lesson-1"),
        Lesson(lesson_number=2, title="Classification", lesson_link="https://example.com/ml-lesson-2"),
    ]
)

SAMPLE_COURSE_2 = Course(
    title="Advanced MCP Integration",
    course_link="https://example.com/mcp-course",
    instructor="Dr. Bob Johnson",
    lessons=[
        Lesson(lesson_number=1, title="MCP Basics", lesson_link="https://example.com/mcp-lesson-1"),
        Lesson(lesson_number=2, title="Advanced MCP Patterns", lesson_link="https://example.com/mcp-lesson-2"),
    ]
)

# Sample course chunks for testing
SAMPLE_CHUNKS = [
    CourseChunk(
        content="Machine learning is a subset of artificial intelligence that uses algorithms to learn patterns from data.",
        course_title="Introduction to Machine Learning",
        lesson_number=1,
        chunk_index=0
    ),
    CourseChunk(
        content="Linear regression is used to model the relationship between a dependent variable and independent variables.",
        course_title="Introduction to Machine Learning", 
        lesson_number=1,
        chunk_index=1
    ),
    CourseChunk(
        content="MCP (Model Context Protocol) allows seamless integration between AI models and external tools.",
        course_title="Advanced MCP Integration",
        lesson_number=1,
        chunk_index=0
    ),
]

# Sample search results for mocking
SAMPLE_SEARCH_RESULTS = SearchResults(
    documents=[chunk.content for chunk in SAMPLE_CHUNKS],
    metadata=[
        {
            "course_title": chunk.course_title,
            "lesson_number": chunk.lesson_number,
            "chunk_index": chunk.chunk_index
        } for chunk in SAMPLE_CHUNKS
    ],
    distances=[0.1, 0.2, 0.3]
)

EMPTY_SEARCH_RESULTS = SearchResults(
    documents=[],
    metadata=[],
    distances=[]
)

ERROR_SEARCH_RESULTS = SearchResults.empty("Database connection failed")

# Sample OpenAI API responses for mocking - these need to be Mock objects with proper structure
from unittest.mock import Mock

def create_openai_response_no_tools():
    """Create properly structured mock OpenAI response without tools"""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message = Mock()
    response.choices[0].message.content = "This is a direct response without using tools."
    response.choices[0].finish_reason = "stop"
    return response

def create_openai_response_with_tools():
    """Create properly structured mock OpenAI response with tool calls"""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message = Mock()
    response.choices[0].message.content = None
    response.choices[0].finish_reason = "tool_calls"
    
    # Create tool call mock
    tool_call = Mock()
    tool_call.id = "call_123"
    tool_call.type = "function"
    tool_call.function = Mock()
    tool_call.function.name = "search_course_content"
    tool_call.function.arguments = '{"query": "machine learning", "course_name": "Introduction to Machine Learning"}'
    
    response.choices[0].message.tool_calls = [tool_call]
    return response

def create_openai_final_response():
    """Create properly structured mock OpenAI final response"""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message = Mock()
    response.choices[0].message.content = "Based on the search results, machine learning is a subset of AI that uses algorithms to learn patterns."
    response.choices[0].finish_reason = "stop"
    return response

# Keep the old format for backward compatibility in some tests
SAMPLE_OPENAI_RESPONSE_NO_TOOLS = {
    "choices": [
        {
            "message": {"content": "This is a direct response without using tools."},
            "finish_reason": "stop"
        }
    ]
}

SAMPLE_OPENAI_RESPONSE_WITH_TOOLS = {
    "choices": [
        {
            "message": {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "search_course_content",
                            "arguments": '{"query": "machine learning", "course_name": "Introduction to Machine Learning"}'
                        }
                    }
                ]
            },
            "finish_reason": "tool_calls"
        }
    ]
}

SAMPLE_OPENAI_FINAL_RESPONSE = {
    "choices": [
        {
            "message": {"content": "Based on the search results, machine learning is a subset of AI that uses algorithms to learn patterns."},
            "finish_reason": "stop"
        }
    ]
}

# Tool definitions for testing
SAMPLE_TOOL_DEFINITIONS = [
    {
        "name": "search_course_content",
        "description": "Search course materials with smart course name matching and lesson filtering",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for in the course content"},
                "course_name": {"type": "string", "description": "Course title (partial matches work)"},
                "lesson_number": {"type": "integer", "description": "Specific lesson number"}
            },
            "required": ["query"]
        }
    }
]

# Expected OpenAI format after conversion
EXPECTED_OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_course_content",
            "description": "Search course materials with smart course name matching and lesson filtering",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in the course content"},
                    "course_name": {"type": "string", "description": "Course title (partial matches work)"},
                    "lesson_number": {"type": "integer", "description": "Specific lesson number"}
                },
                "required": ["query"]
            }
        }
    }
]