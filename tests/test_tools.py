"""Tests for Parakeet tools."""

import os
from pathlib import Path

import pytest

from parakeet.core.tools import (
    read_file_tool,
    list_files_tool,
    edit_file_tool,
    search_code_tool,
    sqlite_tool,
    run_bash_tool,
    run_python_tool,
    is_sqlite_write_query,
    resolve_abs_path,
    TOOLS,
    TOOL_REGISTRY,
    DANGEROUS_TOOLS,
    CONDITIONAL_TOOLS,
)


class TestResolveAbsPath:
    """Tests for resolve_abs_path helper."""

    def test_absolute_path_unchanged(self):
        path = resolve_abs_path("/tmp/test")
        assert path == Path("/tmp/test")

    def test_relative_path_resolved(self):
        path = resolve_abs_path("test.txt")
        assert path.is_absolute()
        assert path.name == "test.txt"

    def test_home_expansion(self):
        path = resolve_abs_path("~/test.txt")
        assert path.is_absolute()
        assert str(path).startswith(str(Path.home()))


class TestReadFileTool:
    """Tests for read_file_tool."""

    def test_read_existing_file(self, temp_file):
        file_path = temp_file("test.txt", "Hello, World!")
        result = read_file_tool(str(file_path))
        assert result["content"] == "Hello, World!"
        assert result["path"] == str(file_path)

    def test_read_file_with_unicode(self, temp_file):
        content = "Héllo, 世界! 🎉"
        file_path = temp_file("unicode.txt", content)
        result = read_file_tool(str(file_path))
        assert result["content"] == content

    def test_read_nonexistent_file(self, temp_dir):
        with pytest.raises(FileNotFoundError):
            read_file_tool(str(temp_dir / "nonexistent.txt"))


class TestListFilesTool:
    """Tests for list_files_tool."""

    def test_list_empty_directory(self, temp_dir):
        result = list_files_tool(str(temp_dir))
        assert result["files"] == []

    def test_list_directory_with_files(self, temp_file):
        temp_file("file1.txt", "content1")
        temp_file("file2.py", "content2")
        temp_dir = temp_file("file1.txt", "").parent

        result = list_files_tool(str(temp_dir))
        files = {f["filename"] for f in result["files"]}
        assert "file1.txt" in files
        assert "file2.py" in files

    def test_list_directory_with_subdirs(self, temp_file, temp_dir):
        temp_file("file.txt", "content")
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        result = list_files_tool(str(temp_dir))
        items = {(f["filename"], f["type"]) for f in result["files"]}
        assert ("file.txt", "file") in items
        assert ("subdir", "dir") in items


class TestEditFileTool:
    """Tests for edit_file_tool."""

    def test_create_new_file(self, temp_dir):
        file_path = temp_dir / "new_file.txt"
        result = edit_file_tool(str(file_path), "", "New content")

        assert result["action"] == "created_file"
        assert file_path.read_text() == "New content"

    def test_create_file_in_nested_directory(self, temp_dir):
        file_path = temp_dir / "nested" / "dir" / "file.txt"
        result = edit_file_tool(str(file_path), "", "Nested content")

        assert result["action"] == "created_file"
        assert file_path.read_text() == "Nested content"

    def test_edit_existing_file(self, temp_file):
        file_path = temp_file("test.txt", "Hello, World!")
        result = edit_file_tool(str(file_path), "World", "Python")

        assert result["action"] == "edited"
        assert file_path.read_text() == "Hello, Python!"

    def test_edit_file_string_not_found(self, temp_file):
        file_path = temp_file("test.txt", "Hello, World!")
        result = edit_file_tool(str(file_path), "NotFound", "Replacement")

        assert result["action"] == "old_str not found"
        assert file_path.read_text() == "Hello, World!"

    def test_edit_replaces_only_first_occurrence(self, temp_file):
        file_path = temp_file("test.txt", "foo foo foo")
        result = edit_file_tool(str(file_path), "foo", "bar")

        assert result["action"] == "edited"
        assert file_path.read_text() == "bar foo foo"


class TestSearchCodeTool:
    """Tests for search_code_tool."""

    def test_search_finds_pattern(self, temp_file, temp_dir):
        temp_file("test.py", "def hello():\n    print('Hello')\n")
        temp_file("other.py", "def world():\n    pass\n")

        result = search_code_tool("def hello", str(temp_dir))

        assert not result.get("error")
        assert len(result["matches"]) == 1
        assert result["matches"][0]["file"] == "test.py"
        assert result["matches"][0]["line"] == 1

    def test_search_with_file_pattern(self, temp_file, temp_dir):
        temp_file("test.py", "# TODO: fix this\n")
        temp_file("test.txt", "# TODO: fix that\n")

        result = search_code_tool("TODO", str(temp_dir), file_pattern="*.py")

        assert len(result["matches"]) == 1
        assert result["matches"][0]["file"] == "test.py"

    def test_search_case_insensitive(self, temp_file, temp_dir):
        temp_file("test.txt", "Hello World\n")

        result = search_code_tool("hello", str(temp_dir))

        assert len(result["matches"]) == 1

    def test_search_invalid_regex(self, temp_dir):
        result = search_code_tool("[invalid(", str(temp_dir))
        assert "error" in result
        assert "Invalid regex" in result["error"]

    def test_search_no_matches(self, temp_file, temp_dir):
        temp_file("test.txt", "Hello World\n")

        result = search_code_tool("NotFound", str(temp_dir))

        assert result["matches"] == []
        assert result["truncated"] is False

    def test_search_ignores_git_directory(self, temp_file, temp_dir):
        temp_file(".git/config", "pattern_to_find\n")
        temp_file("src/main.py", "other content\n")

        result = search_code_tool("pattern_to_find", str(temp_dir))

        assert len(result["matches"]) == 0

    def test_search_truncates_long_lines(self, temp_file, temp_dir):
        long_line = "x" * 300
        temp_file("test.txt", f"pattern {long_line}\n")

        result = search_code_tool("pattern", str(temp_dir))

        assert len(result["matches"]) == 1
        assert len(result["matches"][0]["content"]) <= 200


class TestSqliteTool:
    """Tests for sqlite_tool."""

    def test_select_query(self, temp_db):
        result = sqlite_tool(str(temp_db), "SELECT * FROM users")

        assert "columns" in result
        assert result["columns"] == ["id", "name", "email"]
        assert result["row_count"] == 2
        assert result["rows"][0]["name"] == "Alice"

    def test_select_with_where(self, temp_db):
        result = sqlite_tool(str(temp_db), "SELECT name FROM users WHERE id = 1")

        assert result["row_count"] == 1
        assert result["rows"][0]["name"] == "Alice"

    def test_pragma_table_info(self, temp_db):
        result = sqlite_tool(str(temp_db), "PRAGMA table_info(users)")

        assert "columns" in result
        columns = [row["name"] for row in result["rows"]]
        assert "id" in columns
        assert "name" in columns
        assert "email" in columns

    def test_parameterized_query(self, temp_db):
        result = sqlite_tool(
            str(temp_db),
            "SELECT * FROM users WHERE name = ?",
            params=["Bob"]
        )

        assert result["row_count"] == 1
        assert result["rows"][0]["email"] == "bob@example.com"

    def test_insert_query(self, temp_db):
        result = sqlite_tool(
            str(temp_db),
            "INSERT INTO users (id, name, email) VALUES (3, 'Charlie', 'charlie@example.com')"
        )

        assert result["rows_affected"] == 1
        assert result["last_rowid"] == 3

    def test_update_query(self, temp_db):
        result = sqlite_tool(
            str(temp_db),
            "UPDATE users SET email = 'newalice@example.com' WHERE id = 1"
        )

        assert result["rows_affected"] == 1

    def test_delete_query(self, temp_db):
        result = sqlite_tool(str(temp_db), "DELETE FROM users WHERE id = 2")

        assert result["rows_affected"] == 1

    def test_database_not_found(self, temp_dir):
        result = sqlite_tool(str(temp_dir / "nonexistent.db"), "SELECT 1")

        assert "error" in result
        assert "not found" in result["error"]

    def test_invalid_sql(self, temp_db):
        result = sqlite_tool(str(temp_db), "INVALID SQL QUERY")

        assert "error" in result
        assert "SQLite error" in result["error"]

    def test_table_not_found(self, temp_db):
        result = sqlite_tool(str(temp_db), "SELECT * FROM nonexistent")

        assert "error" in result


class TestIsSqliteWriteQuery:
    """Tests for is_sqlite_write_query helper."""

    @pytest.mark.parametrize("query", [
        "SELECT * FROM users",
        "  select name from users",
        "PRAGMA table_info(users)",
        "pragma database_list",
    ])
    def test_read_queries(self, query):
        assert is_sqlite_write_query(query) is False

    @pytest.mark.parametrize("query", [
        "INSERT INTO users VALUES (1)",
        "  insert into users values (1)",
        "UPDATE users SET name = 'test'",
        "DELETE FROM users WHERE id = 1",
        "DROP TABLE users",
        "CREATE TABLE test (id INT)",
        "ALTER TABLE users ADD column",
        "REPLACE INTO users VALUES (1)",
        "TRUNCATE TABLE users",
    ])
    def test_write_queries(self, query):
        assert is_sqlite_write_query(query) is True


class TestRunBashTool:
    """Tests for run_bash_tool."""

    def test_simple_command(self):
        result = run_bash_tool("echo 'Hello'")

        assert result["return_code"] == 0
        assert "Hello" in result["stdout"]

    def test_command_with_error(self):
        result = run_bash_tool("ls /nonexistent_directory_12345")

        assert result["return_code"] != 0
        assert result["stderr"] != ""

    def test_command_output(self):
        result = run_bash_tool("echo -n 'test'")

        assert result["stdout"] == "test"

    def test_environment_variables(self):
        result = run_bash_tool("echo $HOME")

        assert result["return_code"] == 0
        assert result["stdout"].strip() != ""


class TestRunPythonTool:
    """Tests for run_python_tool."""

    def test_simple_code(self):
        result = run_python_tool("print('Hello from Python')")

        assert result["return_code"] == 0
        assert "Hello from Python" in result["stdout"]

    def test_code_with_imports(self):
        result = run_python_tool("import sys; print(sys.version_info.major)")

        assert result["return_code"] == 0
        assert result["stdout"].strip() in ["3", "4"]

    def test_code_with_error(self):
        result = run_python_tool("raise ValueError('test error')")

        assert result["return_code"] != 0
        assert "ValueError" in result["stderr"]

    def test_multiline_code(self):
        code = """
def add(a, b):
    return a + b

result = add(2, 3)
print(f'Result: {result}')
"""
        result = run_python_tool(code)

        assert result["return_code"] == 0
        assert "Result: 5" in result["stdout"]

    def test_syntax_error(self):
        result = run_python_tool("def broken(")

        assert result["return_code"] != 0
        assert "SyntaxError" in result["stderr"]


class TestToolRegistry:
    """Tests for tool registration."""

    def test_all_tools_registered(self):
        for tool in TOOLS:
            assert tool.__name__ in TOOL_REGISTRY
            assert TOOL_REGISTRY[tool.__name__] == tool

    def test_dangerous_tools_in_registry(self):
        for tool_name in DANGEROUS_TOOLS:
            assert tool_name in TOOL_REGISTRY

    def test_conditional_tools_in_registry(self):
        for tool_name in CONDITIONAL_TOOLS:
            assert tool_name in TOOL_REGISTRY

    def test_tool_count(self):
        assert len(TOOLS) == len(TOOL_REGISTRY)
        assert len(TOOLS) == 15  # file ops (4) + sqlite + env (2) + exec (2) + bio (6)
