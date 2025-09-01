"""Tests for ai_generator module"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json

from ai_generator import AIGenerator
from tests.fixtures.sample_data import (
    SAMPLE_TOOL_DEFINITIONS, EXPECTED_OPENAI_TOOLS,
    SAMPLE_OPENAI_RESPONSE_NO_TOOLS, SAMPLE_OPENAI_RESPONSE_WITH_TOOLS, 
    SAMPLE_OPENAI_FINAL_RESPONSE,
    create_openai_response_no_tools, create_openai_response_with_tools, create_openai_final_response
)


class TestAIGenerator:
    """Test cases for AIGenerator"""
    
    def test_init(self):
        """Test AIGenerator initialization"""
        with patch('ai_generator.AzureOpenAI') as mock_openai:
            generator = AIGenerator(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                deployment="test-deployment",
                model="gpt-4",
                api_version="2024-12-01-preview"
            )
            
            # Verify Azure OpenAI client was created correctly
            mock_openai.assert_called_once_with(
                api_version="2024-12-01-preview",
                azure_endpoint="https://test.openai.azure.com/",
                api_key="test-key"
            )
            
            assert generator.deployment == "test-deployment"
            assert generator.model == "gpt-4"
            assert generator.base_params["model"] == "test-deployment"
            assert generator.base_params["temperature"] == 0
            assert generator.base_params["max_tokens"] == 800
    
    def test_generate_response_no_tools(self, ai_generator):
        """Test response generation without tools"""
        ai_generator.client.chat.completions.create.return_value = create_openai_response_no_tools()
        
        response = ai_generator.generate_response("What is machine learning?")
        
        assert response == "This is a direct response without using tools."
        
        # Verify API was called with correct parameters
        call_args = ai_generator.client.chat.completions.create.call_args
        assert call_args[1]["model"] == "test-deployment"
        assert call_args[1]["temperature"] == 0
        assert call_args[1]["max_tokens"] == 800
        assert len(call_args[1]["messages"]) == 2
        assert call_args[1]["messages"][0]["role"] == "system"
        assert call_args[1]["messages"][1]["role"] == "user"
        assert call_args[1]["messages"][1]["content"] == "What is machine learning?"
        assert "tools" not in call_args[1]
    
    def test_generate_response_with_conversation_history(self, ai_generator):
        """Test response generation with conversation history"""
        ai_generator.client.chat.completions.create.return_value = create_openai_response_no_tools()
        
        history = "Previous conversation context"
        response = ai_generator.generate_response("Follow-up question", conversation_history=history)
        
        # Verify history was included in system message
        call_args = ai_generator.client.chat.completions.create.call_args
        system_message = call_args[1]["messages"][0]["content"]
        assert "Previous conversation context" in system_message
    
    def test_convert_tools_to_openai_format(self, ai_generator, sample_tool_definitions, expected_openai_tools):
        """Test conversion of Anthropic tool format to OpenAI format"""
        converted_tools = ai_generator._convert_tools_to_openai_format(sample_tool_definitions)
        
        assert converted_tools == expected_openai_tools
        assert converted_tools[0]["type"] == "function"
        assert converted_tools[0]["function"]["name"] == "search_course_content"
        assert converted_tools[0]["function"]["parameters"] == sample_tool_definitions[0]["input_schema"]
    
    def test_generate_response_with_tools_no_tool_calls(self, ai_generator, sample_tool_definitions):
        """Test response generation with tools available but not used"""
        ai_generator.client.chat.completions.create.return_value = create_openai_response_no_tools()
        
        response = ai_generator.generate_response(
            "What is machine learning?",
            tools=sample_tool_definitions
        )
        
        assert response == "This is a direct response without using tools."
        
        # Verify tools were passed to API
        call_args = ai_generator.client.chat.completions.create.call_args
        assert "tools" in call_args[1]
        assert call_args[1]["tool_choice"] == "auto"
        assert len(call_args[1]["tools"]) == 1
        assert call_args[1]["tools"][0]["type"] == "function"
    
    def test_generate_response_with_tool_calls(self, ai_generator, sample_tool_definitions, tool_manager):
        """Test response generation that triggers tool calls"""
        # Mock the initial response with tool calls
        initial_response = create_openai_response_with_tools()
        
        # Mock the final response after tool execution
        final_response = create_openai_final_response()
        
        # Configure client to return initial response, then final response
        ai_generator.client.chat.completions.create.side_effect = [initial_response, final_response]
        
        # Mock tool execution result
        tool_manager.execute_tool.return_value = "Search results about machine learning"
        
        response = ai_generator.generate_response(
            "Tell me about machine learning",
            tools=sample_tool_definitions,
            tool_manager=tool_manager
        )
        
        assert response == "Based on the search results, machine learning is a subset of AI that uses algorithms to learn patterns."
        
        # Verify tool was executed
        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="machine learning",
            course_name="Introduction to Machine Learning"
        )
        
        # Verify two API calls were made
        assert ai_generator.client.chat.completions.create.call_count == 2
    
    def test_handle_tool_execution_single_tool(self, ai_generator, tool_manager):
        """Test handling of tool execution with single tool call"""
        # Create mock tool call
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "search_course_content"
        mock_tool_call.function.arguments = '{"query": "test"}'
        
        initial_response = Mock()
        initial_response.choices = [Mock()]
        initial_response.choices[0].message.content = None
        initial_response.choices[0].message.tool_calls = [mock_tool_call]
        
        base_params = {
            "messages": [
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "User query"}
            ]
        }
        
        # Mock tool execution result
        tool_manager.execute_tool.return_value = "Tool execution result"
        
        # Mock final response
        final_response = create_openai_final_response()
        ai_generator.client.chat.completions.create.return_value = final_response
        
        result = ai_generator._handle_tool_execution(initial_response, base_params, tool_manager)
        
        assert result == "Based on the search results, machine learning is a subset of AI that uses algorithms to learn patterns."
        
        # Verify tool was executed with correct parameters
        tool_manager.execute_tool.assert_called_once_with("search_course_content", query="test")
        
        # Verify final API call included tool result message
        final_call_args = ai_generator.client.chat.completions.create.call_args
        messages = final_call_args[1]["messages"]
        
        # Should have system, user, assistant (tool call), and tool result messages
        assert len(messages) == 4
        assert messages[2]["role"] == "assistant"
        assert messages[2]["tool_calls"] == [mock_tool_call]
        assert messages[3]["role"] == "tool"
        assert messages[3]["tool_call_id"] == "call_123"
        assert messages[3]["content"] == "Tool execution result"
    
    def test_handle_tool_execution_multiple_tools(self, ai_generator, tool_manager):
        """Test handling of multiple tool calls in one response"""
        # Create mock tool calls
        mock_tool_call_1 = Mock()
        mock_tool_call_1.id = "call_123"
        mock_tool_call_1.type = "function"
        mock_tool_call_1.function.name = "search_course_content"
        mock_tool_call_1.function.arguments = '{"query": "test1"}'
        
        mock_tool_call_2 = Mock()
        mock_tool_call_2.id = "call_456"
        mock_tool_call_2.type = "function"
        mock_tool_call_2.function.name = "get_course_outline"
        mock_tool_call_2.function.arguments = '{"course_name": "ML"}'
        
        initial_response = Mock()
        initial_response.choices = [Mock()]
        initial_response.choices[0].message.content = None
        initial_response.choices[0].message.tool_calls = [mock_tool_call_1, mock_tool_call_2]
        
        base_params = {
            "messages": [
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "User query"}
            ]
        }
        
        # Mock tool execution results
        tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]
        
        # Mock final response
        final_response = create_openai_final_response()
        ai_generator.client.chat.completions.create.return_value = final_response
        
        result = ai_generator._handle_tool_execution(initial_response, base_params, tool_manager)
        
        # Verify both tools were executed
        assert tool_manager.execute_tool.call_count == 2
        tool_manager.execute_tool.assert_any_call("search_course_content", query="test1")
        tool_manager.execute_tool.assert_any_call("get_course_outline", course_name="ML")
        
        # Verify final API call included both tool result messages
        final_call_args = ai_generator.client.chat.completions.create.call_args
        messages = final_call_args[1]["messages"]
        
        # Should have system, user, assistant (tool calls), tool result 1, tool result 2
        assert len(messages) == 5
        assert messages[3]["role"] == "tool"
        assert messages[3]["tool_call_id"] == "call_123"
        assert messages[3]["content"] == "Result 1"
        assert messages[4]["role"] == "tool"
        assert messages[4]["tool_call_id"] == "call_456"
        assert messages[4]["content"] == "Result 2"
    
    def test_handle_tool_execution_json_parsing_error(self, ai_generator, tool_manager):
        """Test handling of JSON parsing errors in tool arguments"""
        # Create mock tool call with invalid JSON
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "search_course_content"
        mock_tool_call.function.arguments = '{"query": invalid json}'  # Invalid JSON
        
        initial_response = Mock()
        initial_response.choices = [Mock()]
        initial_response.choices[0].message.content = None
        initial_response.choices[0].message.tool_calls = [mock_tool_call]
        
        base_params = {"messages": []}
        
        # Should raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            ai_generator._handle_tool_execution(initial_response, base_params, tool_manager)
    
    def test_handle_tool_execution_tool_not_function_type(self, ai_generator, tool_manager):
        """Test handling of non-function type tool calls"""
        # Create mock tool call that's not a function
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "other_type"  # Not "function"
        
        initial_response = Mock()
        initial_response.choices = [Mock()]
        initial_response.choices[0].message.content = None
        initial_response.choices[0].message.tool_calls = [mock_tool_call]
        
        base_params = {"messages": []}
        
        # Mock final response
        final_response = create_openai_final_response()
        ai_generator.client.chat.completions.create.return_value = final_response
        
        result = ai_generator._handle_tool_execution(initial_response, base_params, tool_manager)
        
        # Tool should not be executed for non-function types
        tool_manager.execute_tool.assert_not_called()
        
        # But final response should still be returned
        assert result == "Based on the search results, machine learning is a subset of AI that uses algorithms to learn patterns."
    
    def test_generate_response_api_error(self, ai_generator):
        """Test handling of Azure OpenAI API errors"""
        # Mock API error
        ai_generator.client.chat.completions.create.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            ai_generator.generate_response("test query")
    
    def test_generate_response_tool_execution_error(self, ai_generator, sample_tool_definitions, tool_manager):
        """Test handling of tool execution errors"""
        # Mock tool call response
        initial_response = Mock(**SAMPLE_OPENAI_RESPONSE_WITH_TOOLS)
        
        # Configure client to return tool call response
        ai_generator.client.chat.completions.create.side_effect = [initial_response]
        
        # Mock tool execution error
        tool_manager.execute_tool.side_effect = Exception("Tool execution failed")
        
        # Should raise the tool execution error
        with pytest.raises(Exception, match="Tool execution failed"):
            ai_generator.generate_response(
                "test query",
                tools=sample_tool_definitions,
                tool_manager=tool_manager
            )
    
    def test_system_prompt_content(self, ai_generator):
        """Test that system prompt contains expected content"""
        ai_generator.client.chat.completions.create.return_value = create_openai_response_no_tools()
        
        ai_generator.generate_response("test query")
        
        call_args = ai_generator.client.chat.completions.create.call_args
        system_message = call_args[1]["messages"][0]["content"]
        
        # Verify key parts of system prompt are present
        assert "AI assistant specialized in course materials" in system_message
        assert "Content Search Tool" in system_message
        assert "Course Outline Tool" in system_message
        assert "Brief, Concise and focused" in system_message
    
    def test_base_params_configuration(self, ai_generator):
        """Test that base parameters are correctly configured"""
        expected_params = {
            "model": "test-deployment",
            "temperature": 0,
            "max_tokens": 800
        }
        
        assert ai_generator.base_params == expected_params