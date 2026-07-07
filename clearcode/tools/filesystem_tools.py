import os
from langchain.tools import tool

from clearcode.observability.logger import get_logger

logger = get_logger(__name__)

_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@tool
def read_file(file_path: str) -> str:
    """Read and return the contents of a file."""
    logger.info(f"Tool called: read_file — path: {file_path}")
    if not file_path or not file_path.strip():
        return "Error: file path cannot be empty"
    if not os.path.exists(file_path):
        logger.warning(f"read_file: file not found: {file_path}")
        return f"Error: file not found: {file_path}"
    if not os.path.isfile(file_path):
        logger.warning(f"read_file: path is not a file: {file_path}")
        return f"Error: path is not a file: {file_path}"
    size = os.path.getsize(file_path)
    if size > _MAX_FILE_SIZE_BYTES:
        logger.warning(f"read_file: file too large ({size} bytes): {file_path}")
        return f"Error: file too large ({size} bytes). Max allowed is {_MAX_FILE_SIZE_BYTES} bytes"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.debug(f"read_file: read {size} bytes from {file_path}")
        return content
    except UnicodeDecodeError:
        logger.warning(f"read_file: not valid UTF-8: {file_path}")
        return f"Error: file is not valid UTF-8 text: {file_path}"
    except PermissionError:
        logger.warning(f"read_file: permission denied: {file_path}")
        return f"Error: permission denied: {file_path}"
    except Exception as e:
        logger.error(f"read_file: unexpected error reading {file_path}: {e}")
        return f"Error: {e}"


@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file, creating it and any parent directories if needed."""
    logger.info(f"Tool called: write_file — path: {file_path} ({len(content)} chars)")
    if not file_path or not file_path.strip():
        return "Error: file path cannot be empty"
    try:
        if os.path.dirname(file_path):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.debug(f"write_file: wrote {len(content)} chars to {file_path}")
        return f"Written to {file_path}"
    except PermissionError:
        logger.warning(f"write_file: permission denied: {file_path}")
        return f"Error: permission denied: {file_path}"
    except Exception as e:
        logger.error(f"write_file: unexpected error writing {file_path}: {e}")
        return f"Error: {e}"


@tool
def append_file(file_path: str, content: str) -> str:
    """Append content to an existing file."""
    logger.info(f"Tool called: append_file — path: {file_path} ({len(content)} chars)")
    if not file_path or not file_path.strip():
        return "Error: file path cannot be empty"
    if not os.path.exists(file_path):
        logger.warning(f"append_file: file not found: {file_path}")
        return f"Error: file not found: {file_path}"
    if not os.path.isfile(file_path):
        logger.warning(f"append_file: path is not a file: {file_path}")
        return f"Error: path is not a file: {file_path}"
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(content)
        logger.debug(f"append_file: appended {len(content)} chars to {file_path}")
        return f"Appended to {file_path}"
    except PermissionError:
        logger.warning(f"append_file: permission denied: {file_path}")
        return f"Error: permission denied: {file_path}"
    except Exception as e:
        logger.error(f"append_file: unexpected error appending to {file_path}: {e}")
        return f"Error: {e}"


@tool
def delete_file(file_path: str) -> str:
    """Delete a file."""
    logger.info(f"Tool called: delete_file — path: {file_path}")
    if not file_path or not file_path.strip():
        return "Error: file path cannot be empty"
    if not os.path.exists(file_path):
        logger.warning(f"delete_file: file not found: {file_path}")
        return f"Error: file not found: {file_path}"
    if not os.path.isfile(file_path):
        logger.warning(f"delete_file: path is not a file: {file_path}")
        return f"Error: path is not a file (use a directory tool for directories): {file_path}"
    try:
        os.remove(file_path)
        logger.debug(f"delete_file: deleted {file_path}")
        return f"Deleted {file_path}"
    except PermissionError:
        logger.warning(f"delete_file: permission denied: {file_path}")
        return f"Error: permission denied: {file_path}"
    except Exception as e:
        logger.error(f"delete_file: unexpected error deleting {file_path}: {e}")
        return f"Error: {e}"


@tool
def list_directory(directory: str) -> str:
    """List files and subdirectories inside a directory."""
    logger.info(f"Tool called: list_directory — path: {directory}")
    if not directory or not directory.strip():
        return "Error: directory cannot be empty"
    if not os.path.exists(directory):
        logger.warning(f"list_directory: directory not found: {directory}")
        return f"Error: directory not found: {directory}"
    if not os.path.isdir(directory):
        logger.warning(f"list_directory: path is not a directory: {directory}")
        return f"Error: path is not a directory: {directory}"
    try:
        entries = os.listdir(directory)
        logger.debug(f"list_directory: {len(entries)} entries in {directory}")
        return "\n".join(sorted(entries)) if entries else "(empty directory)"
    except PermissionError:
        logger.warning(f"list_directory: permission denied: {directory}")
        return f"Error: permission denied: {directory}"
    except Exception as e:
        logger.error(f"list_directory: unexpected error listing {directory}: {e}")
        return f"Error: {e}"


@tool
def file_exists(file_path: str) -> str:
    """Check whether a file or directory exists."""
    logger.info(f"Tool called: file_exists — path: {file_path}")
    if not file_path or not file_path.strip():
        return "Error: file path cannot be empty"
    exists = os.path.exists(file_path)
    logger.debug(f"file_exists: {file_path} -> {exists}")
    return str(exists)