import subprocess
import os
from langchain.tools import tool

from clearcode.observability.logger import get_logger

logger = get_logger(__name__)

_BLOCKED_COMMANDS = {"rm -rf /", "mkfs", "dd if=", ":(){:|:&};:"}
_TIMEOUT_SECONDS = 30


def _is_blocked(command: str) -> bool:
   return any(blocked in command for blocked in _BLOCKED_COMMANDS)


def _format_result(result: subprocess.CompletedProcess) -> str:
   parts = []
   if result.stdout:
       parts.append(result.stdout.rstrip())
   if result.stderr:
       parts.append(f"STDERR: {result.stderr.rstrip()}")
   if result.returncode != 0:
       parts.append(f"Exit code: {result.returncode}")
   return "\n".join(parts) if parts else "(no output)"


@tool
def run_command(command: str) -> str:
   """Run a shell command and return its output. Times out after 30 seconds."""
   logger.info(f"Tool called: run_command — command: {command}")
   if not command or not command.strip():
       return "Error: command cannot be empty"
   if _is_blocked(command):
       logger.warning(f"run_command: blocked command attempted: {command}")
       return "Error: command is not allowed for safety reasons"
   try:
       result = subprocess.run(
           command,
           shell=True,
           capture_output=True,
           text=True,
           timeout=_TIMEOUT_SECONDS,
       )
       logger.debug(f"run_command: exit code {result.returncode} for: {command}")
       return _format_result(result)
   except subprocess.TimeoutExpired:
       logger.warning(f"run_command: timed out after {_TIMEOUT_SECONDS}s: {command}")
       return f"Error: command timed out after {_TIMEOUT_SECONDS} seconds"
   except Exception as e:
       logger.error(f"run_command: unexpected error running '{command}': {e}")
       return f"Error: {e}"


@tool
def run_in_directory(command: str, directory: str) -> str:
   """Run a shell command inside a specific directory. Times out after 30 seconds."""
   logger.info(f"Tool called: run_in_directory — command: {command!r} in: {directory}")
   if not command or not command.strip():
       return "Error: command cannot be empty"
   if not directory or not directory.strip():
       return "Error: directory cannot be empty"
   if not os.path.exists(directory):
       logger.warning(f"run_in_directory: directory not found: {directory}")
       return f"Error: directory does not exist: {directory}"
   if not os.path.isdir(directory):
       logger.warning(f"run_in_directory: path is not a directory: {directory}")
       return f"Error: path is not a directory: {directory}"
   if _is_blocked(command):
       logger.warning(f"run_in_directory: blocked command attempted: {command}")
       return "Error: command is not allowed for safety reasons"
   try:
       result = subprocess.run(
           command,
           shell=True,
           capture_output=True,
           text=True,
           cwd=directory,
           timeout=_TIMEOUT_SECONDS,
       )
       logger.debug(f"run_in_directory: exit code {result.returncode} for: {command}")
       return _format_result(result)
   except subprocess.TimeoutExpired:
       logger.warning(f"run_in_directory: timed out after {_TIMEOUT_SECONDS}s: {command}")
       return f"Error: command timed out after {_TIMEOUT_SECONDS} seconds"
   except Exception as e:
       logger.error(f"run_in_directory: unexpected error running '{command}' in {directory}: {e}")
       return f"Error: {e}"
