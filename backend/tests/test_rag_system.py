"""Tests for rag_system module - Integration tests for the complete RAG pipeline"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import uuid

from rag_system import RAGSystem
from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool
from vector_store import SearchResults
from tests.fixtures.sample_data import (
    SAMPLE_COURSE_1, SAMPLE_CHUNKS, SAMPLE_SEARCH_RESULTS, EMPTY_SEARCH_RESULTS,
    SAMPLE_OPENAI_RESPONSE_WITH_TOOLS, SAMPLE_OPENAI_FINAL_RESPONSE
)


class TestRAGSystem:
    """Integration tests for the complete RAG system"""
    
    @pytest.fixture
    def mock_rag_system(self, test_config):
        """Create RAG system with mocked dependencies"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_vector_store, \
             patch('rag_system.AIGenerator') as mock_ai_generator, \
             patch('rag_system.SessionManager') as mock_session_manager:
            
            # Configure mocks
            mock_vector_store.return_value.search.return_value = SAMPLE_SEARCH_RESULTS
            mock_vector_store.return_value.get_lesson_links.return_value = {1: "https://example.com/lesson-1"}
            mock_vector_store.return_value._resolve_course_name.return_value = "Introduction to Machine Learning"
            
            mock_ai_generator.return_value.generate_response.return_value = "AI response based on search results"
            
            mock_session_manager.return_value.get_conversation_history.return_value = None
            mock_session_manager.return_value.add_exchange.return_value = None
            
            rag_system = RAGSystem(test_config)
            
            # Store mocks for access in tests
            rag_system._mock_vector_store = mock_vector_store.return_value
            rag_system._mock_ai_generator = mock_ai_generator.return_value
            rag_system._mock_session_manager = mock_session_manager.return_value
            
            return rag_system
    
    def test_rag_system_initialization(self, test_config):
        """Test RAG system initializes all components correctly"""
        with patch('rag_system.DocumentProcessor') as mock_doc_processor, \
             patch('rag_system.VectorStore') as mock_vector_store, \
             patch('rag_system.AIGenerator') as mock_ai_generator, \
             patch('rag_system.SessionManager') as mock_session_manager:
            
            rag_system = RAGSystem(test_config)
            
            # Verify all components were initialized
            mock_doc_processor.assert_called_once_with(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
            mock_vector_store.assert_called_once_with(test_config.CHROMA_PATH, test_config.EMBEDDING_MODEL, test_config.MAX_RESULTS)
            mock_ai_generator.assert_called_once()
            mock_session_manager.assert_called_once_with(test_config.MAX_HISTORY)
            
            # Verify tools were registered
            assert isinstance(rag_system.tool_manager, ToolManager)
            assert len(rag_system.tool_manager.tools) == 2
            assert "search_course_content" in rag_system.tool_manager.tools
            assert "get_course_outline" in rag_system.tool_manager.tools
    
    def test_query_without_session(self, mock_rag_system):
        """Test query processing without session management"""
        response, sources = mock_rag_system.query("What is machine learning?")
        
        assert response == "AI response based on search results"
        assert sources == []  # Sources were reset after query
        
        # Verify AI generator was called with correct parameters
        mock_rag_system._mock_ai_generator.generate_response.assert_called_once()
        call_args = mock_rag_system._mock_ai_generator.generate_response.call_args
        
        assert "Answer this question about course materials: What is machine learning?" in call_args[1]["query"]
        assert call_args[1]["conversation_history"] is None
        assert call_args[1]["tools"] is not None
        assert call_args[1]["tool_manager"] is not None
        
        # Verify session manager was not used
        mock_rag_system._mock_session_manager.get_conversation_history.assert_not_called()
        mock_rag_system._mock_session_manager.add_exchange.assert_not_called()
    
    def test_query_with_session(self, mock_rag_system):
        """Test query processing with session management"""
        session_id = str(uuid.uuid4())
        mock_rag_system._mock_session_manager.get_conversation_history.return_value = "Previous: What is AI?\nResponse: AI is artificial intelligence."
        
        response, sources = mock_rag_system.query("What about machine learning?", session_id=session_id)
        
        assert response == "AI response based on search results"
        
        # Verify session history was retrieved
        mock_rag_system._mock_session_manager.get_conversation_history.assert_called_once_with(session_id)
        
        # Verify conversation history was passed to AI
        call_args = mock_rag_system._mock_ai_generator.generate_response.call_args
        assert call_args[1]["conversation_history"] == "Previous: What is AI?\nResponse: AI is artificial intelligence."
        
        # Verify exchange was added to session
        mock_rag_system._mock_session_manager.add_exchange.assert_called_once_with(
            session_id, 
            "What about machine learning?", 
            "AI response based on search results"
        )
    
    def test_query_tool_integration(self, mock_rag_system):
        """Test that query correctly integrates with tool system"""
        # Configure tool manager to track sources
        mock_sources = [{"text": "Introduction to ML - Lesson 1", "link": "https://example.com/lesson-1"}]
        mock_rag_system.tool_manager.get_last_sources = Mock(return_value=mock_sources)
        mock_rag_system.tool_manager.reset_sources = Mock()
        
        response, sources = mock_rag_system.query("Explain linear regression")
        
        # Verify sources were retrieved and returned
        assert sources == mock_sources
        
        # Verify sources were reset after retrieval
        mock_rag_system.tool_manager.get_last_sources.assert_called_once()
        mock_rag_system.tool_manager.reset_sources.assert_called_once()
        
        # Verify tool definitions were passed to AI generator
        call_args = mock_rag_system._mock_ai_generator.generate_response.call_args
        assert call_args[1]["tools"] is not None
        assert call_args[1]["tool_manager"] is not None
    
    def test_add_course_document_success(self, mock_rag_system):
        """Test successful course document addition"""
        with patch.object(mock_rag_system.document_processor, 'process_course_document') as mock_process:
            mock_process.return_value = (SAMPLE_COURSE_1, SAMPLE_CHUNKS)
            
            course, chunk_count = mock_rag_system.add_course_document("/path/to/course.txt")
            
            assert course == SAMPLE_COURSE_1
            assert chunk_count == len(SAMPLE_CHUNKS)
            
            # Verify document was processed
            mock_process.assert_called_once_with("/path/to/course.txt")
            
            # Verify data was added to vector store
            mock_rag_system._mock_vector_store.add_course_metadata.assert_called_once_with(SAMPLE_COURSE_1)
            mock_rag_system._mock_vector_store.add_course_content.assert_called_once_with(SAMPLE_CHUNKS)
    
    def test_add_course_document_error(self, mock_rag_system):
        """Test handling of course document processing errors"""
        with patch.object(mock_rag_system.document_processor, 'process_course_document') as mock_process:
            mock_process.side_effect = Exception("Processing failed")
            
            course, chunk_count = mock_rag_system.add_course_document("/path/to/bad_course.txt")
            
            assert course is None
            assert chunk_count == 0
            
            # Verify vector store methods were not called
            mock_rag_system._mock_vector_store.add_course_metadata.assert_not_called()
            mock_rag_system._mock_vector_store.add_course_content.assert_not_called()
    
    def test_add_course_folder_clear_existing(self, mock_rag_system):
        """Test adding course folder with clear existing data option"""
        with patch('os.path.exists') as mock_exists, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.isfile') as mock_isfile, \
             patch.object(mock_rag_system.document_processor, 'process_course_document') as mock_process:
            
            mock_exists.return_value = True
            mock_listdir.return_value = ["course1.txt", "course2.pdf"]
            mock_isfile.return_value = True
            mock_process.return_value = (SAMPLE_COURSE_1, SAMPLE_CHUNKS)
            mock_rag_system._mock_vector_store.get_existing_course_titles.return_value = []
            
            courses_added, chunks_added = mock_rag_system.add_course_folder(
                "/path/to/courses", 
                clear_existing=True
            )
            
            assert courses_added == 2
            assert chunks_added == len(SAMPLE_CHUNKS) * 2
            
            # Verify clear_all_data was called
            mock_rag_system._mock_vector_store.clear_all_data.assert_called_once()
    
    def test_add_course_folder_skip_existing(self, mock_rag_system):
        """Test adding course folder skips existing courses"""
        with patch('os.path.exists') as mock_exists, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.isfile') as mock_isfile, \
             patch.object(mock_rag_system.document_processor, 'process_course_document') as mock_process:
            
            mock_exists.return_value = True
            mock_listdir.return_value = ["course1.txt"]
            mock_isfile.return_value = True
            mock_process.return_value = (SAMPLE_COURSE_1, SAMPLE_CHUNKS)
            
            # Mock course already exists
            mock_rag_system._mock_vector_store.get_existing_course_titles.return_value = [SAMPLE_COURSE_1.title]
            
            courses_added, chunks_added = mock_rag_system.add_course_folder("/path/to/courses")
            
            assert courses_added == 0
            assert chunks_added == 0
            
            # Verify course was processed but not added
            mock_process.assert_called_once()
            mock_rag_system._mock_vector_store.add_course_metadata.assert_not_called()
            mock_rag_system._mock_vector_store.add_course_content.assert_not_called()
    
    def test_add_course_folder_nonexistent_path(self, mock_rag_system):
        """Test adding course folder with nonexistent path"""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            courses_added, chunks_added = mock_rag_system.add_course_folder("/nonexistent/path")
            
            assert courses_added == 0
            assert chunks_added == 0
    
    def test_get_course_analytics(self, mock_rag_system):
        """Test getting course analytics"""
        mock_rag_system._mock_vector_store.get_course_count.return_value = 3
        mock_rag_system._mock_vector_store.get_existing_course_titles.return_value = [
            "Course 1", "Course 2", "Course 3"
        ]
        
        analytics = mock_rag_system.get_course_analytics()
        
        assert analytics["total_courses"] == 3
        assert analytics["course_titles"] == ["Course 1", "Course 2", "Course 3"]
        
        mock_rag_system._mock_vector_store.get_course_count.assert_called_once()
        mock_rag_system._mock_vector_store.get_existing_course_titles.assert_called_once()
    
    def test_end_to_end_query_with_tool_execution(self, test_config):
        """End-to-end test simulating real tool execution during query"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_vector_store_class, \
             patch('rag_system.SessionManager') as mock_session_manager, \
             patch('ai_generator.AzureOpenAI') as mock_openai:
            
            # Set up vector store mock
            mock_vector_store = mock_vector_store_class.return_value
            mock_vector_store.search.return_value = SAMPLE_SEARCH_RESULTS
            mock_vector_store.get_lesson_links.return_value = {1: "https://example.com/lesson-1"}
            
            # Set up Azure OpenAI mock for tool calling flow
            mock_client = mock_openai.return_value
            
            # First call returns tool_calls, second call returns final response
            initial_response = Mock()
            initial_response.choices = [Mock()]
            initial_response.choices[0].finish_reason = "tool_calls"
            initial_response.choices[0].message.content = None
            initial_response.choices[0].message.tool_calls = [Mock()]
            initial_response.choices[0].message.tool_calls[0].id = "call_123"
            initial_response.choices[0].message.tool_calls[0].type = "function"
            initial_response.choices[0].message.tool_calls[0].function.name = "search_course_content"
            initial_response.choices[0].message.tool_calls[0].function.arguments = '{"query": "machine learning"}'
            
            final_response = Mock()
            final_response.choices = [Mock()]
            final_response.choices[0].finish_reason = "stop"
            final_response.choices[0].message.content = "Machine learning is a subset of AI that learns from data using algorithms and statistical models."
            
            mock_client.chat.completions.create.side_effect = [initial_response, final_response]
            
            # Initialize RAG system
            rag_system = RAGSystem(test_config)
            
            # Execute query
            response, sources = rag_system.query("What is machine learning?")
            
            # Verify response
            assert "Machine learning is a subset of AI" in response
            
            # Verify tool was executed (sources should be populated and then reset)
            # Since sources are reset after query, we verify the search was called
            mock_vector_store.search.assert_called_with(
                query="machine learning",
                course_name=None,
                lesson_number=None
            )
            
            # Verify OpenAI was called twice (initial + final response)
            assert mock_client.chat.completions.create.call_count == 2
    
    def test_query_prompt_formatting(self, mock_rag_system):
        """Test that query is properly formatted in prompt"""
        user_query = "Explain neural networks"
        
        mock_rag_system.query(user_query)
        
        call_args = mock_rag_system._mock_ai_generator.generate_response.call_args
        prompt = call_args[1]["query"]
        
        assert f"Answer this question about course materials: {user_query}" == prompt
    
    def test_tool_manager_registration(self, mock_rag_system):
        """Test that tools are properly registered with tool manager"""
        tool_definitions = mock_rag_system.tool_manager.get_tool_definitions()
        
        assert len(tool_definitions) == 2
        tool_names = [tool["name"] for tool in tool_definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names
        
        # Verify tools can be executed
        assert "search_course_content" in mock_rag_system.tool_manager.tools
        assert "get_course_outline" in mock_rag_system.tool_manager.tools
        assert isinstance(mock_rag_system.tool_manager.tools["search_course_content"], CourseSearchTool)
        assert isinstance(mock_rag_system.tool_manager.tools["get_course_outline"], CourseOutlineTool)