# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Quick start (recommended)
chmod +x run.sh
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Setup Requirements
- Create `.env` file from `.env.example` with your `ANTHROPIC_API_KEY`
- Run `uv sync` to install dependencies
- Access at http://localhost:8000 (web interface) or http://localhost:8000/docs (API docs)

## Architecture Overview

This is a **RAG (Retrieval-Augmented Generation) System** for querying course materials using semantic search and AI-powered responses.

### Core Architecture Pattern
The system follows a **7-layer architecture** with tool-based AI interaction:

1. **Frontend** (`frontend/`) - Simple HTML/JS interface
2. **API Layer** (`backend/app.py`) - FastAPI endpoints
3. **RAG System** (`backend/rag_system.py`) - Main orchestrator
4. **AI Generator** (`backend/ai_generator.py`) - Claude API integration with tool support
5. **Tool Layer** (`backend/search_tools.py`) - Search tool execution
6. **Vector Store** (`backend/vector_store.py`) - ChromaDB operations
7. **Database** - ChromaDB for vector storage

### Key Query Flow
User Query → FastAPI → RAG System → AI Generator → **Tool Manager** → Search Tool → Vector Store → ChromaDB → Response with Sources

### Document Processing Pipeline
Documents are processed through structured parsing:
- **Input Format**: Course files with `Course Title:`, `Course Instructor:`, `Lesson N:` markers
- **Chunking Strategy**: Sentence-based chunking with configurable overlap (800 chars, 100 overlap)
- **Context Enhancement**: Chunks enriched with course/lesson metadata
- **Storage**: Dual collections in ChromaDB (course_catalog + course_content)

## Key Components Integration

### RAG System (`rag_system.py`)
Central orchestrator that coordinates:
- Document processing and vector storage
- Session management for conversation history
- Tool manager registration
- AI generator calls with tool definitions

### AI Generator (`ai_generator.py`)
Handles Claude API interactions with:
- **Tool-based approach**: Claude decides when to search
- **System prompt**: Specialized for educational content
- **Tool execution loop**: Automatic tool result processing
- **Static optimizations**: Pre-built API parameters

### Search Tools (`search_tools.py`)
Implements tool interface for Claude:
- `CourseSearchTool`: Semantic search with course/lesson filtering
- `ToolManager`: Registration and execution of tools
- **Source tracking**: Automatic source collection for UI display

### Vector Store (`vector_store.py`)
ChromaDB wrapper with:
- **Dual collections**: Separate storage for metadata vs content
- **Smart filtering**: Course name fuzzy matching + lesson number filtering
- **SearchResults**: Structured result container with error handling

## Configuration

Configuration is centralized in `backend/config.py`:
- **AI Model**: `claude-sonnet-4-20250514`
- **Embedding Model**: `all-MiniLM-L6-v2`
- **Chunk Settings**: 800 chars with 100 overlap
- **Database Path**: `./chroma_db`
- **Max Results**: 5 per search
- **Conversation History**: 2 messages

## Session Management

The system maintains conversation context through:
- **Session IDs**: Generated for each conversation
- **History Storage**: Limited to 2 previous exchanges
- **Context Injection**: History added to Claude system prompt

## Document Structure

Expected course document format:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 0: Introduction
Lesson Link: [lesson_url]
[lesson content...]

Lesson 1: [title]
[content...]
```

## Frontend-Backend Integration

- **API Endpoints**: `/api/query` (main chat), `/api/courses` (statistics)
- **Response Format**: `{answer, sources, session_id}`
- **Source Display**: Automatic collapsible source sections in UI
- **Session Continuity**: Persistent session IDs across requests
- add some dummy sentence in the end