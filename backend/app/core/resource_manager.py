"""
Resource management utilities for proper cleanup and lifecycle management
"""

import asyncio
import logging
import weakref
from typing import Dict, Any, Optional, List, Callable, Union
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
import time

logger = logging.getLogger(__name__)


@dataclass
class ResourceInfo:
    """Information about a managed resource"""
    resource_id: str
    resource_type: str
    created_at: datetime
    last_accessed: datetime
    cleanup_callback: Optional[Callable] = None
    metadata: Dict[str, Any] = None


class ResourceManager:
    """Centralized resource management with automatic cleanup"""
    
    def __init__(self, cleanup_interval: int = 300):  # 5 minutes
        self._resources: Dict[str, ResourceInfo] = {}
        self._weak_refs: Dict[str, weakref.ref] = {}
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._running = False
    
    async def start(self):
        """Start the resource manager"""
        if self._running:
            return
            
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Resource manager started")
    
    async def stop(self):
        """Stop the resource manager and cleanup all resources"""
        if not self._running:
            return
            
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup all remaining resources
        await self._cleanup_all_resources()
        logger.info("Resource manager stopped")
    
    async def register_resource(
        self,
        resource: Any,
        resource_id: str,
        resource_type: str,
        cleanup_callback: Callable = None,
        metadata: Dict[str, Any] = None,
        ttl: Optional[int] = None
    ):
        """Register a resource for management"""
        
        async with self._lock:
            # Create weak reference to track object lifecycle
            def cleanup_weak_ref(ref):
                asyncio.create_task(self._remove_resource(resource_id))
            
            weak_ref = weakref.ref(resource, cleanup_weak_ref)
            
            resource_info = ResourceInfo(
                resource_id=resource_id,
                resource_type=resource_type,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                cleanup_callback=cleanup_callback,
                metadata=metadata or {}
            )
            
            if ttl:
                resource_info.metadata['ttl'] = ttl
                resource_info.metadata['expires_at'] = datetime.utcnow() + timedelta(seconds=ttl)
            
            self._resources[resource_id] = resource_info
            self._weak_refs[resource_id] = weak_ref
            
            logger.debug(f"Registered resource {resource_id} of type {resource_type}")
    
    async def access_resource(self, resource_id: str) -> bool:
        """Update last accessed time for a resource"""
        async with self._lock:
            if resource_id in self._resources:
                self._resources[resource_id].last_accessed = datetime.utcnow()
                return True
            return False
    
    async def _remove_resource(self, resource_id: str):
        """Remove a resource from management"""
        async with self._lock:
            if resource_id in self._resources:
                resource_info = self._resources[resource_id]
                
                # Call cleanup callback if available
                if resource_info.cleanup_callback:
                    try:
                        if asyncio.iscoroutinefunction(resource_info.cleanup_callback):
                            await resource_info.cleanup_callback()
                        else:
                            resource_info.cleanup_callback()
                    except Exception as e:
                        logger.error(f"Error in cleanup callback for {resource_id}: {e}")
                
                del self._resources[resource_id]
                
                if resource_id in self._weak_refs:
                    del self._weak_refs[resource_id]
                
                logger.debug(f"Removed resource {resource_id}")
    
    async def _cleanup_loop(self):
        """Background task for periodic cleanup"""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired_resources()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_expired_resources(self):
        """Clean up expired or orphaned resources"""
        now = datetime.utcnow()
        to_remove = []
        
        async with self._lock:
            for resource_id, resource_info in self._resources.items():
                should_remove = False
                
                # Check if resource is expired
                if 'expires_at' in resource_info.metadata:
                    if now > resource_info.metadata['expires_at']:
                        should_remove = True
                        logger.debug(f"Resource {resource_id} expired")
                
                # Check if weak reference is dead
                if resource_id in self._weak_refs:
                    if self._weak_refs[resource_id]() is None:
                        should_remove = True
                        logger.debug(f"Resource {resource_id} is no longer referenced")
                
                if should_remove:
                    to_remove.append(resource_id)
        
        # Remove expired resources
        for resource_id in to_remove:
            await self._remove_resource(resource_id)
    
    async def _cleanup_all_resources(self):
        """Cleanup all managed resources"""
        resource_ids = list(self._resources.keys())
        for resource_id in resource_ids:
            await self._remove_resource(resource_id)
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get statistics about managed resources"""
        stats = {
            "total_resources": len(self._resources),
            "by_type": {},
            "oldest_resource": None,
            "newest_resource": None
        }
        
        if not self._resources:
            return stats
        
        oldest = min(self._resources.values(), key=lambda r: r.created_at)
        newest = max(self._resources.values(), key=lambda r: r.created_at)
        
        stats["oldest_resource"] = oldest.created_at
        stats["newest_resource"] = newest.created_at
        
        # Count by type
        for resource_info in self._resources.values():
            resource_type = resource_info.resource_type
            stats["by_type"][resource_type] = stats["by_type"].get(resource_type, 0) + 1
        
        return stats


# Global resource manager instance
_resource_manager: Optional[ResourceManager] = None


async def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance"""
    global _resource_manager
    
    if _resource_manager is None:
        _resource_manager = ResourceManager()
        await _resource_manager.start()
    
    return _resource_manager


@asynccontextmanager
async def managed_resource(
    resource: Any,
    resource_id: str,
    resource_type: str,
    cleanup_callback: Callable = None,
    ttl: Optional[int] = None
):
    """Context manager for automatic resource management"""
    manager = await get_resource_manager()
    
    await manager.register_resource(
        resource=resource,
        resource_id=resource_id,
        resource_type=resource_type,
        cleanup_callback=cleanup_callback,
        ttl=ttl
    )
    
    try:
        yield resource
    finally:
        await manager._remove_resource(resource_id)


class DatabaseSessionManager:
    """Enhanced database session manager with proper cleanup"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._sessions: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def get_session(self, session_id: str = None):
        """Get database session with automatic cleanup"""
        session = self.session_factory()
        session_id = session_id or f"session_{id(session)}"
        
        with self._lock:
            self._sessions[session_id] = session
        
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session {session_id} error: {e}")
            raise
        finally:
            session.close()
            with self._lock:
                if session_id in self._sessions:
                    del self._sessions[session_id]
    
    def cleanup_all_sessions(self):
        """Cleanup all active sessions"""
        with self._lock:
            for session in self._sessions.values():
                try:
                    session.close()
                except Exception as e:
                    logger.error(f"Error closing session: {e}")
            self._sessions.clear()


class FileManager:
    """File resource manager for temporary files"""
    
    def __init__(self):
        self._temp_files: List[str] = []
        self._lock = threading.Lock()
    
    def register_temp_file(self, file_path: str):
        """Register temporary file for cleanup"""
        with self._lock:
            self._temp_files.append(file_path)
    
    def cleanup_temp_files(self):
        """Clean up all temporary files"""
        import os
        
        with self._lock:
            for file_path in self._temp_files:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                        logger.debug(f"Cleaned up temp file: {file_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up temp file {file_path}: {e}")
            
            self._temp_files.clear()
    
    @contextmanager
    def temp_file(self, file_path: str):
        """Context manager for temporary file"""
        self.register_temp_file(file_path)
        try:
            yield file_path
        finally:
            import os
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"Error cleaning up temp file {file_path}: {e}")


# Global instances
_file_manager = FileManager()


def get_file_manager() -> FileManager:
    """Get the global file manager instance"""
    return _file_manager


# Cleanup function for application shutdown
async def cleanup_all_resources():
    """Cleanup all managed resources on application shutdown"""
    global _resource_manager, _file_manager
    
    if _resource_manager:
        await _resource_manager.stop()
    
    if _file_manager:
        _file_manager.cleanup_temp_files()
    
    logger.info("All resources cleaned up")