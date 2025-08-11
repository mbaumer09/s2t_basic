import inspect
from typing import Dict, Type, Any, Callable, Optional, TypeVar, get_type_hints
from enum import Enum


T = TypeVar('T')


class Scope(Enum):
    """Dependency scope enumeration."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"


class Container:
    """Dependency injection container for managing application dependencies."""
    
    def __init__(self):
        """Initialize the container."""
        self._registrations: Dict[Type, Dict[str, Any]] = {}
        self._singletons: Dict[Type, Any] = {}
    
    def register(
        self,
        interface: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None,
        scope: Scope = Scope.SINGLETON
    ) -> None:
        """Register a dependency in the container.
        
        Args:
            interface: The interface or base class to register
            implementation: The concrete implementation class
            factory: A factory function that creates instances
            instance: A pre-created instance
            scope: The lifetime scope of the dependency
            
        Raises:
            ValueError: If registration is invalid
        """
        if sum([implementation is not None, factory is not None, instance is not None]) != 1:
            raise ValueError("Exactly one of implementation, factory, or instance must be provided")
        
        registration = {
            'scope': scope,
            'implementation': implementation,
            'factory': factory,
            'instance': instance
        }
        
        # If instance is provided, store it as singleton
        if instance is not None:
            self._singletons[interface] = instance
            registration['scope'] = Scope.SINGLETON
        
        self._registrations[interface] = registration
    
    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register a singleton dependency.
        
        Args:
            interface: The interface to register
            implementation: The implementation class
        """
        self.register(interface, implementation=implementation, scope=Scope.SINGLETON)
    
    def register_transient(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register a transient dependency.
        
        Args:
            interface: The interface to register
            implementation: The implementation class
        """
        self.register(interface, implementation=implementation, scope=Scope.TRANSIENT)
    
    def register_factory(
        self,
        interface: Type[T],
        factory: Callable[[], T],
        scope: Scope = Scope.SINGLETON
    ) -> None:
        """Register a factory function.
        
        Args:
            interface: The interface to register
            factory: Factory function that creates instances
            scope: The lifetime scope
        """
        self.register(interface, factory=factory, scope=scope)
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register a pre-created instance.
        
        Args:
            interface: The interface to register
            instance: The instance to register
        """
        self.register(interface, instance=instance)
    
    def resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency from the container.
        
        Args:
            interface: The interface to resolve
            
        Returns:
            An instance of the requested type
            
        Raises:
            ValueError: If the interface is not registered
        """
        if interface not in self._registrations:
            raise ValueError(f"No registration found for {interface.__name__}")
        
        registration = self._registrations[interface]
        scope = registration['scope']
        
        # Check for existing singleton
        if scope == Scope.SINGLETON and interface in self._singletons:
            return self._singletons[interface]
        
        # Create new instance
        instance = None
        
        if registration['instance'] is not None:
            instance = registration['instance']
        elif registration['factory'] is not None:
            instance = registration['factory']()
        elif registration['implementation'] is not None:
            instance = self._create_instance(registration['implementation'])
        
        # Store singleton
        if scope == Scope.SINGLETON:
            self._singletons[interface] = instance
        
        return instance
    
    def _create_instance(self, cls: Type[T]) -> T:
        """Create an instance of a class with automatic dependency injection.
        
        Args:
            cls: The class to instantiate
            
        Returns:
            An instance of the class
        """
        # Get constructor signature
        sig = inspect.signature(cls.__init__)
        params = {}
        
        # Get type hints
        type_hints = get_type_hints(cls.__init__)
        
        # Resolve each parameter
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            
            # Try to get type from type hints
            if name in type_hints:
                param_type = type_hints[name]
            elif param.annotation != param.empty:
                param_type = param.annotation
            else:
                continue
            
            # Try to resolve the parameter
            try:
                params[name] = self.resolve(param_type)
            except ValueError:
                # If can't resolve and has default, skip
                if param.default == param.empty:
                    raise ValueError(f"Cannot resolve parameter '{name}' of type {param_type} for {cls.__name__}")
        
        return cls(**params)
    
    def has_registration(self, interface: Type) -> bool:
        """Check if an interface is registered.
        
        Args:
            interface: The interface to check
            
        Returns:
            True if registered, False otherwise
        """
        return interface in self._registrations
    
    def clear(self) -> None:
        """Clear all registrations and singletons."""
        self._registrations.clear()
        self._singletons.clear()
    
    def create_child_container(self) -> 'Container':
        """Create a child container that inherits registrations.
        
        Returns:
            A new container with copied registrations
        """
        child = Container()
        child._registrations = self._registrations.copy()
        # Don't copy singletons - let child create its own
        return child