"""Shared fixtures for RAG system tests"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add the backend directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.fixtures.sample_data import (
    SAMPLE_COURSE_1, SAMPLE_COURSE_2, SAMPLE_CHUNKS, 
    SAMPLE_SEARCH_RESULTS, EMPTY_SEARCH_RESULTS, ERROR_SEARCH_RESULTS,
    SAMPLE_OPENAI_RESPONSE_NO_TOOLS, SAMPLE_OPENAI_RESPONSE_WITH_TOOLS, SAMPLE_OPENAI_FINAL_RESPONSE,
    SAMPLE_TOOL_DEFINITIONS, EXPECTED_OPENAI_TOOLS,
    create_openai_response_no_tools, create_openai_response_with_tools, create_openai_final_response
)
from models import Course, Lesson, CourseChunk
from vector_store import SearchResults, VectorStore
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from ai_generator import AIGenerator
from config import Config

@pytest.fixture
def sample_course_1():
    """Sample course for testing"""
    return SAMPLE_COURSE_1

@pytest.fixture
def sample_course_2():
    """Another sample course for testing"""
    return SAMPLE_COURSE_2

@pytest.fixture
def sample_chunks():
    """Sample course chunks for testing"""
    return SAMPLE_CHUNKS

@pytest.fixture
def sample_search_results():
    """Sample search results with data"""
    return SAMPLE_SEARCH_RESULTS

@pytest.fixture 
def empty_search_results():
    """Empty search results"""
    return EMPTY_SEARCH_RESULTS

@pytest.fixture
def error_search_results():
    """Error search results"""
    return ERROR_SEARCH_RESULTS

@pytest.fixture
def mock_vector_store():
    """Mock VectorStore for testing"""
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = SAMPLE_SEARCH_RESULTS
    mock_store.get_lesson_links.return_value = {1: "https://example.com/lesson-1", 2: "https://example.com/lesson-2"}
    mock_store._resolve_course_name.return_value = "Introduction to Machine Learning"
    mock_store.course_catalog = Mock()
    mock_store.course_catalog.get.return_value = {
        'metadatas': [{
            'title': 'Introduction to Machine Learning',
            'instructor': 'Dr. Jane Smith',
            'course_link': 'https://example.com/ml-course',
            'lessons_json': '[{"lesson_number": 1, "lesson_title": "Linear Regression", "lesson_link": "https://example.com/lesson-1"}]',
            'lesson_count': 1
        }]
    }
    return mock_store

@pytest.fixture
def course_search_tool(mock_vector_store):
    """CourseSearchTool with mocked VectorStore"""
    return CourseSearchTool(mock_vector_store)

@pytest.fixture
def course_outline_tool(mock_vector_store):
    """CourseOutlineTool with mocked VectorStore"""
    return CourseOutlineTool(mock_vector_store)

@pytest.fixture
def tool_manager(course_search_tool, course_outline_tool):
    """ToolManager with registered tools"""
    manager = ToolManager()
    manager.register_tool(course_search_tool)
    manager.register_tool(course_outline_tool)
    return manager

@pytest.fixture
def mock_azure_openai_client():
    """Mock Azure OpenAI client"""
    mock_client = Mock()
    # Use the properly structured response
    mock_client.chat.completions.create.return_value = create_openai_response_no_tools()
    return mock_client

@pytest.fixture
def ai_generator(mock_azure_openai_client):
    """AIGenerator with mocked Azure OpenAI client"""
    with patch('ai_generator.AzureOpenAI') as mock_openai:
        mock_openai.return_value = mock_azure_openai_client
        generator = AIGenerator(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            deployment="test-deployment",
            model="gpt-4",
            api_version="2024-12-01-preview"
        )
        generator.client = mock_azure_openai_client
        return generator

@pytest.fixture
def test_config():
    """Test configuration"""
    config = Config()
    config.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com/"
    config.AZURE_OPENAI_API_KEY = "test-key"
    config.AZURE_OPENAI_DEPLOYMENT = "test-deployment"
    config.AZURE_OPENAI_MODEL = "gpt-4"
    config.AZURE_OPENAI_API_VERSION = "2024-12-01-preview"
    config.CHROMA_PATH = ":memory:"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.MAX_RESULTS = 5
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_HISTORY = 2
    return config

@pytest.fixture
def sample_openai_responses():
    """Sample OpenAI API responses for mocking"""
    return {
        "no_tools": SAMPLE_OPENAI_RESPONSE_NO_TOOLS,
        "with_tools": SAMPLE_OPENAI_RESPONSE_WITH_TOOLS,
        "final_response": SAMPLE_OPENAI_FINAL_RESPONSE
    }

@pytest.fixture
def sample_tool_definitions():
    """Sample tool definitions"""
    return SAMPLE_TOOL_DEFINITIONS

@pytest.fixture
def expected_openai_tools():
    """Expected OpenAI tool format after conversion"""
    return EXPECTED_OPENAI_TOOLS