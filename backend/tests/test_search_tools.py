"""Tests for search_tools module"""

import pytest
from unittest.mock import Mock, patch
import json

from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults
from tests.fixtures.sample_data import (
    SAMPLE_SEARCH_RESULTS, EMPTY_SEARCH_RESULTS, ERROR_SEARCH_RESULTS
)


class TestCourseSearchTool:
    """Test cases for CourseSearchTool"""
    
    def test_get_tool_definition(self, course_search_tool):
        """Test that tool definition is correctly formatted"""
        definition = course_search_tool.get_tool_definition()
        
        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["required"] == ["query"]
        assert "query" in definition["input_schema"]["properties"]
        assert "course_name" in definition["input_schema"]["properties"]
        assert "lesson_number" in definition["input_schema"]["properties"]
    
    def test_execute_basic_query(self, course_search_tool, mock_vector_store):
        """Test basic query execution with results"""
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
        
        result = course_search_tool.execute("machine learning")
        
        assert "Machine learning is a subset" in result
        assert "[Introduction to Machine Learning - Lesson 1]" in result
        assert len(course_search_tool.last_sources) > 0
        
        # Verify VectorStore was called correctly
        mock_vector_store.search.assert_called_once_with(
            query="machine learning",
            course_name=None,
            lesson_number=None
        )
    
    def test_execute_with_course_filter(self, course_search_tool, mock_vector_store):
        """Test query execution with course name filter"""
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
        
        result = course_search_tool.execute("linear regression", course_name="ML")
        
        assert "Linear regression is used to model" in result
        
        # Verify VectorStore was called with course filter
        mock_vector_store.search.assert_called_once_with(
            query="linear regression",
            course_name="ML",
            lesson_number=None
        )
    
    def test_execute_with_lesson_filter(self, course_search_tool, mock_vector_store):
        """Test query execution with lesson number filter"""
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
        
        result = course_search_tool.execute("classification", lesson_number=2)
        
        mock_vector_store.search.assert_called_once_with(
            query="classification",
            course_name=None,
            lesson_number=2
        )
    
    def test_execute_with_both_filters(self, course_search_tool, mock_vector_store):
        """Test query execution with both course and lesson filters"""
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
        
        result = course_search_tool.execute("patterns", course_name="MCP", lesson_number=1)
        
        mock_vector_store.search.assert_called_once_with(
            query="patterns",
            course_name="MCP", 
            lesson_number=1
        )
    
    def test_execute_empty_results(self, course_search_tool, mock_vector_store):
        """Test handling of empty search results"""
        mock_vector_store.search.return_value = EMPTY_SEARCH_RESULTS
        
        result = course_search_tool.execute("nonexistent topic")
        
        assert result == "No relevant content found."
        assert len(course_search_tool.last_sources) == 0
    
    def test_execute_empty_results_with_filters(self, course_search_tool, mock_vector_store):
        """Test empty results message includes filter information"""
        mock_vector_store.search.return_value = EMPTY_SEARCH_RESULTS
        
        result = course_search_tool.execute("test", course_name="ML", lesson_number=5)
        
        assert "No relevant content found in course 'ML' in lesson 5." == result
    
    def test_execute_error_handling(self, course_search_tool, mock_vector_store):
        """Test handling of search errors"""
        mock_vector_store.search.return_value = ERROR_SEARCH_RESULTS
        
        result = course_search_tool.execute("test query")
        
        assert result == "Database connection failed"
        assert len(course_search_tool.last_sources) == 0
    
    def test_execute_empty_query(self, course_search_tool, mock_vector_store):
        """Test handling of empty query string"""
        mock_vector_store.search.return_value = EMPTY_SEARCH_RESULTS
        
        result = course_search_tool.execute("")
        
        mock_vector_store.search.assert_called_once_with(
            query="",
            course_name=None,
            lesson_number=None
        )
    
    def test_execute_special_characters(self, course_search_tool, mock_vector_store):
        """Test handling of special characters in query"""
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
        
        result = course_search_tool.execute("test @#$%^&*()")
        
        mock_vector_store.search.assert_called_once_with(
            query="test @#$%^&*()",
            course_name=None,
            lesson_number=None
        )
    
    def test_format_results_with_links(self, course_search_tool, mock_vector_store):
        """Test result formatting includes lesson links when available"""
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
        mock_vector_store.get_lesson_links.return_value = {1: "https://example.com/lesson-1"}
        
        result = course_search_tool.execute("machine learning")
        
        # Check that sources include links
        sources = course_search_tool.last_sources
        assert len(sources) > 0
        
        # Find source with lesson 1
        lesson_1_source = next((s for s in sources if "Lesson 1" in s["text"]), None)
        assert lesson_1_source is not None
        assert "link" in lesson_1_source
        assert lesson_1_source["link"] == "https://example.com/lesson-1"
    
    def test_format_results_without_links(self, course_search_tool, mock_vector_store):
        """Test result formatting when lesson links are not available"""
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
        mock_vector_store.get_lesson_links.return_value = {}
        
        result = course_search_tool.execute("machine learning")
        
        # Check that sources don't include links
        sources = course_search_tool.last_sources
        for source in sources:
            assert "link" not in source or source.get("link") is None
    
    def test_sources_reset_between_searches(self, course_search_tool, mock_vector_store):
        """Test that sources are properly managed between searches"""
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
        
        # First search
        course_search_tool.execute("first query")
        first_sources = course_search_tool.last_sources.copy()
        
        # Second search
        course_search_tool.execute("second query")
        second_sources = course_search_tool.last_sources
        
        # Sources should be updated, not accumulated
        assert len(second_sources) == len(first_sources)  # Same mock data
    
    def test_get_lesson_links_error_handling(self, course_search_tool, mock_vector_store):
        """Test handling of errors when getting lesson links"""
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
        mock_vector_store.get_lesson_links.side_effect = Exception("Link fetch failed")
        
        # Should not raise exception, just continue without links
        result = course_search_tool.execute("test")
        
        assert "Machine learning is a subset" in result  # Content should still be returned


class TestCourseOutlineTool:
    """Test cases for CourseOutlineTool"""
    
    def test_get_tool_definition(self, course_outline_tool):
        """Test that outline tool definition is correctly formatted"""
        definition = course_outline_tool.get_tool_definition()
        
        assert definition["name"] == "get_course_outline"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["required"] == ["course_name"]
        assert "course_name" in definition["input_schema"]["properties"]
    
    def test_execute_valid_course(self, course_outline_tool, mock_vector_store):
        """Test getting outline for existing course"""
        mock_vector_store._resolve_course_name.return_value = "Introduction to Machine Learning"
        
        result = course_outline_tool.execute("ML")
        
        assert "**Introduction to Machine Learning**" in result
        assert "**Instructor:** Dr. Jane Smith" in result
        assert "**Course Link:**" in result
        assert "Lesson 1: Linear Regression" in result
        
        # Verify course resolution was attempted
        mock_vector_store._resolve_course_name.assert_called_once_with("ML")
    
    def test_execute_nonexistent_course(self, course_outline_tool, mock_vector_store):
        """Test handling of non-existent course"""
        mock_vector_store._resolve_course_name.return_value = None
        
        result = course_outline_tool.execute("NonexistentCourse")
        
        assert result == "No course found matching 'NonexistentCourse'"
    
    def test_execute_course_without_metadata(self, course_outline_tool, mock_vector_store):
        """Test handling of course without metadata"""
        mock_vector_store._resolve_course_name.return_value = "Test Course"
        mock_vector_store.course_catalog.get.return_value = {'metadatas': []}
        
        result = course_outline_tool.execute("Test")
        
        assert result == "Course metadata not found for 'Test Course'"
    
    def test_execute_course_catalog_error(self, course_outline_tool, mock_vector_store):
        """Test handling of course catalog errors"""
        mock_vector_store._resolve_course_name.return_value = "Test Course"
        mock_vector_store.course_catalog.get.side_effect = Exception("Database error")
        
        result = course_outline_tool.execute("Test")
        
        assert "Error retrieving course outline: Database error" in result


class TestToolManager:
    """Test cases for ToolManager"""
    
    def test_register_tool(self, mock_vector_store):
        """Test tool registration"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        
        manager.register_tool(tool)
        
        assert "search_course_content" in manager.tools
        assert manager.tools["search_course_content"] == tool
    
    def test_register_tool_without_name(self, mock_vector_store):
        """Test registration of tool without name raises error"""
        manager = ToolManager()
        
        # Create a mock tool with invalid definition
        bad_tool = Mock()
        bad_tool.get_tool_definition.return_value = {"description": "test"}  # Missing name
        
        with pytest.raises(ValueError, match="Tool must have a 'name' in its definition"):
            manager.register_tool(bad_tool)
    
    def test_get_tool_definitions(self, tool_manager):
        """Test getting all tool definitions"""
        definitions = tool_manager.get_tool_definitions()
        
        assert len(definitions) == 2  # search and outline tools
        tool_names = [d["name"] for d in definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names
    
    def test_execute_tool_success(self, tool_manager, mock_vector_store):
        """Test successful tool execution"""
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
        
        result = tool_manager.execute_tool("search_course_content", query="test")
        
        assert "Machine learning is a subset" in result
    
    def test_execute_nonexistent_tool(self, tool_manager):
        """Test execution of non-existent tool"""
        result = tool_manager.execute_tool("nonexistent_tool", query="test")
        
        assert result == "Tool 'nonexistent_tool' not found"
    
    def test_get_last_sources(self, tool_manager, mock_vector_store):
        """Test getting sources from last search"""
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
        
        # Execute a search to generate sources
        tool_manager.execute_tool("search_course_content", query="test")
        
        sources = tool_manager.get_last_sources()
        assert len(sources) > 0
        assert "text" in sources[0]
    
    def test_get_last_sources_empty(self, tool_manager):
        """Test getting sources when no searches have been performed"""
        sources = tool_manager.get_last_sources()
        assert sources == []
    
    def test_reset_sources(self, tool_manager, mock_vector_store):
        """Test resetting sources after search"""
        mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
        
        # Execute search and verify sources exist
        tool_manager.execute_tool("search_course_content", query="test")
        assert len(tool_manager.get_last_sources()) > 0
        
        # Reset and verify sources are cleared
        tool_manager.reset_sources()
        assert tool_manager.get_last_sources() == []