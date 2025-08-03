"""
Security utilities for safe subprocess execution and input validation
"""

import asyncio
import logging
import os
import re
import shlex
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
import tempfile

logger = logging.getLogger(__name__)


class SecureSubprocessExecutor:
    """Secure subprocess execution with input validation and sanitization"""
    
    # Allowed executables and their validation patterns
    ALLOWED_EXECUTABLES = {
        "ffmpeg": r"^ffmpeg$",
        "python": r"^python3?$",
        "scrapy": r"^scrapy$"
    }
    
    # Safe FFmpeg argument patterns
    SAFE_FFMPEG_ARGS = {
        "-i", "-map", "-c:v", "-c:a", "-preset", "-crf", "-b:a", "-r", "-s",
        "-filter_complex", "-af", "-vf", "-t", "-ss", "-to", "-y", "-f",
        "-movflags", "-pix_fmt", "-profile:v", "-level", "-maxrate", "-bufsize"
    }
    
    @classmethod
    def validate_executable(cls, executable: str) -> bool:
        """Validate that executable is allowed"""
        executable_name = os.path.basename(executable)
        
        for allowed_name, pattern in cls.ALLOWED_EXECUTABLES.items():
            if re.match(pattern, executable_name):
                return True
        
        return False
    
    @classmethod
    def sanitize_path(cls, path: Union[str, Path]) -> str:
        """Sanitize file paths to prevent directory traversal"""
        path = str(path)
        
        # Remove any directory traversal attempts
        path = path.replace("../", "").replace("..\\", "")
        
        # Ensure path is absolute or in temp directory
        if not os.path.isabs(path):
            # If relative, prepend temp directory
            path = os.path.join(tempfile.gettempdir(), path)
        
        # Normalize the path
        path = os.path.normpath(path)
        
        return path
    
    @classmethod
    def validate_ffmpeg_args(cls, args: List[str]) -> List[str]:
        """Validate and sanitize FFmpeg arguments"""
        sanitized_args = []
        
        for i, arg in enumerate(args):
            # Skip empty arguments
            if not arg:
                continue
                
            # If it's a flag, validate it's allowed
            if arg.startswith("-"):
                if arg not in cls.SAFE_FFMPEG_ARGS:
                    logger.warning(f"Potentially unsafe FFmpeg argument: {arg}")
                    continue
                sanitized_args.append(arg)
            
            # If it's a value, sanitize it
            else:
                # Check if it looks like a file path
                if "/" in arg or "\\" in arg or arg.endswith(('.mp4', '.avi', '.mov', '.wav', '.mp3')):
                    sanitized_path = cls.sanitize_path(arg)
                    sanitized_args.append(sanitized_path)
                # Check if it's a numeric value
                elif re.match(r'^[\d\.\:x-]+$', arg):
                    sanitized_args.append(arg)
                # Check if it's a known safe value
                elif arg in ["libx264", "aac", "medium", "fast", "slow", "ultrafast", "veryslow"]:
                    sanitized_args.append(arg)
                else:
                    # For other values, escape them
                    sanitized_args.append(shlex.quote(arg))
        
        return sanitized_args
    
    @classmethod
    async def execute_safe(
        cls,
        executable: str,
        args: List[str],
        timeout: Optional[int] = 300,
        cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Safely execute subprocess with validation and timeout
        
        Args:
            executable: The executable to run
            args: List of arguments
            timeout: Timeout in seconds
            cwd: Working directory
            
        Returns:
            Dict with returncode, stdout, stderr
            
        Raises:
            ValueError: If executable or arguments are invalid
            RuntimeError: If subprocess execution fails
        """
        
        # Validate executable
        if not cls.validate_executable(executable):
            raise ValueError(f"Executable '{executable}' is not allowed")
        
        # Sanitize arguments based on executable type
        if "ffmpeg" in executable:
            sanitized_args = cls.validate_ffmpeg_args(args)
        else:
            # For other executables, use basic sanitization
            sanitized_args = [shlex.quote(str(arg)) for arg in args if arg]
        
        # Prepare command
        cmd = [executable] + sanitized_args
        
        logger.info(f"Executing secure subprocess: {' '.join(cmd[:5])}...")  # Log first 5 args only
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise RuntimeError(f"Process timed out after {timeout} seconds")
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "success": process.returncode == 0
            }
            
        except Exception as e:
            logger.error(f"Subprocess execution failed: {e}")
            raise RuntimeError(f"Subprocess execution failed: {e}")


class InputValidator:
    """Input validation utilities"""
    
    # Safe filename pattern (alphanumeric, hyphens, underscores, dots)
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
    
    # URL validation pattern
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    @classmethod
    def validate_filename(cls, filename: str) -> bool:
        """Validate filename for safety"""
        if not filename or len(filename) > 255:
            return False
        
        return bool(cls.SAFE_FILENAME_PATTERN.match(filename))
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """Validate URL format"""
        if not url or len(url) > 2048:
            return False
        
        return bool(cls.URL_PATTERN.match(url))
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            value = str(value)
        
        # Remove null bytes and control characters
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
        
        # Limit length
        value = value[:max_length]
        
        return value.strip()
    
    @classmethod
    def validate_integer(cls, value: Any, min_val: int = None, max_val: int = None) -> int:
        """Validate and convert integer value"""
        try:
            int_val = int(value)
            
            if min_val is not None and int_val < min_val:
                raise ValueError(f"Value {int_val} is below minimum {min_val}")
            
            if max_val is not None and int_val > max_val:
                raise ValueError(f"Value {int_val} is above maximum {max_val}")
            
            return int_val
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid integer value: {value}") from e
    
    @classmethod
    def validate_float(cls, value: Any, min_val: float = None, max_val: float = None) -> float:
        """Validate and convert float value"""
        try:
            float_val = float(value)
            
            if min_val is not None and float_val < min_val:
                raise ValueError(f"Value {float_val} is below minimum {min_val}")
            
            if max_val is not None and float_val > max_val:
                raise ValueError(f"Value {float_val} is above maximum {max_val}")
            
            return float_val
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid float value: {value}") from e


# Context manager for safe temporary files
class SafeTempFile:
    """Safe temporary file management"""
    
    def __init__(self, suffix: str = "", prefix: str = "viralos_", mode: str = "w"):
        self.suffix = suffix
        self.prefix = prefix
        self.mode = mode
        self.file = None
        self.path = None
    
    def __enter__(self):
        self.file = tempfile.NamedTemporaryFile(
            mode=self.mode,
            suffix=self.suffix,
            prefix=self.prefix,
            delete=False
        )
        self.path = self.file.name
        return self.file
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
        
        # Clean up the temporary file
        if self.path and os.path.exists(self.path):
            try:
                os.unlink(self.path)
            except OSError:
                logger.warning(f"Failed to clean up temporary file: {self.path}")