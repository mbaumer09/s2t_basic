from typing import Dict, Optional
import torch
import whisper


class ModelManager:
    """Manager for Whisper model lifecycle and optimization."""
    
    # Model sizes and their approximate memory requirements
    # VRAM usage includes model weights + inference overhead
    MODEL_SPECS = {
        'tiny': {'params': 39e6, 'vram_mb': 2000, 'cpu_ram_mb': 150},
        'base': {'params': 74e6, 'vram_mb': 3000, 'cpu_ram_mb': 290},
        'small': {'params': 244e6, 'vram_mb': 5000, 'cpu_ram_mb': 970},
        'medium': {'params': 769e6, 'vram_mb': 8000, 'cpu_ram_mb': 3060},
        'large': {'params': 1550e6, 'vram_mb': 14000, 'cpu_ram_mb': 6170},
    }
    
    def __init__(self):
        """Initialize the model manager."""
        self.loaded_models: Dict[str, whisper.Whisper] = {}
        self.device_info = self._get_device_info()
    
    def _get_device_info(self) -> dict:
        """Get information about available compute devices."""
        info = {
            'cuda_available': torch.cuda.is_available(),
            'cuda_device_count': 0,
            'cuda_devices': [],
            'recommended_device': 'cpu'
        }
        
        if torch.cuda.is_available():
            info['cuda_device_count'] = torch.cuda.device_count()
            
            for i in range(torch.cuda.device_count()):
                device_props = torch.cuda.get_device_properties(i)
                info['cuda_devices'].append({
                    'index': i,
                    'name': device_props.name,
                    'total_memory_mb': device_props.total_memory / 1024 / 1024,
                    'compute_capability': f"{device_props.major}.{device_props.minor}"
                })
            
            # Recommend CUDA if available with sufficient memory
            if info['cuda_devices'] and info['cuda_devices'][0]['total_memory_mb'] > 2000:
                info['recommended_device'] = 'cuda'
        
        return info
    
    def get_recommended_model_size(self, device: Optional[str] = None) -> str:
        """Get recommended model size based on available resources.
        
        Args:
            device: Target device (cpu/cuda), None for auto-detect
            
        Returns:
            Recommended model size string
        """
        if device is None:
            device = self.device_info['recommended_device']
        
        if device == 'cuda' and self.device_info['cuda_available']:
            # Get available VRAM
            available_vram = self.device_info['cuda_devices'][0]['total_memory_mb']
            
            # Leave some headroom (70% of available VRAM)
            usable_vram = available_vram * 0.7
            
            # Find largest model that fits
            for size in ['large', 'medium', 'small', 'base', 'tiny']:
                if self.MODEL_SPECS[size]['vram_mb'] <= usable_vram:
                    return size
        
        # For CPU, default to base model (good balance)
        return 'base'
    
    def can_load_model(self, model_size: str, device: str) -> tuple[bool, str]:
        """Check if a model can be loaded on the specified device.
        
        Args:
            model_size: Size of the model to check
            device: Target device (cpu/cuda)
            
        Returns:
            Tuple of (can_load, reason_if_not)
        """
        if model_size not in self.MODEL_SPECS:
            return False, f"Unknown model size: {model_size}"
        
        specs = self.MODEL_SPECS[model_size]
        
        if device == 'cuda':
            if not self.device_info['cuda_available']:
                return False, "CUDA is not available"
            
            available_vram = self.device_info['cuda_devices'][0]['total_memory_mb']
            required_vram = specs['vram_mb']
            
            if required_vram > available_vram:
                return False, f"Insufficient VRAM: {required_vram}MB required, {available_vram}MB available"
        
        return True, "Model can be loaded"
    
    def optimize_model_for_device(self, model: whisper.Whisper, device: str) -> whisper.Whisper:
        """Apply device-specific optimizations to the model.
        
        Args:
            model: The Whisper model to optimize
            device: Target device (cpu/cuda)
            
        Returns:
            Optimized model
        """
        if device == 'cuda':
            # Enable mixed precision for faster inference
            model = model.half()
            
            # Enable cudnn benchmarking for optimal performance
            torch.backends.cudnn.benchmark = True
        
        elif device == 'cpu':
            # Ensure full precision on CPU
            model = model.float()
            
            # Set number of threads for CPU inference
            torch.set_num_threads(torch.get_num_threads())
        
        return model
    
    def estimate_transcription_speed(self, model_size: str, device: str, audio_duration: float) -> float:
        """Estimate transcription time for given audio duration.
        
        Args:
            model_size: Size of the model
            device: Device being used
            audio_duration: Duration of audio in seconds
            
        Returns:
            Estimated transcription time in seconds
        """
        # Rough estimates based on typical performance
        # These are conservative estimates
        speed_factors = {
            'tiny': {'cuda': 0.05, 'cpu': 0.2},
            'base': {'cuda': 0.08, 'cpu': 0.4},
            'small': {'cuda': 0.15, 'cpu': 1.0},
            'medium': {'cuda': 0.3, 'cpu': 2.5},
            'large': {'cuda': 0.5, 'cpu': 5.0},
        }
        
        if model_size in speed_factors and device in speed_factors[model_size]:
            factor = speed_factors[model_size][device]
            return audio_duration * factor
        
        # Default conservative estimate
        return audio_duration * 1.0
    
    def get_device_recommendation(self) -> dict:
        """Get comprehensive device recommendation.
        
        Returns:
            Dictionary with device recommendation and reasoning
        """
        recommendation = {
            'device': self.device_info['recommended_device'],
            'model_size': self.get_recommended_model_size(),
            'reasoning': []
        }
        
        if self.device_info['cuda_available']:
            vram = self.device_info['cuda_devices'][0]['total_memory_mb']
            recommendation['reasoning'].append(
                f"CUDA GPU detected: {self.device_info['cuda_devices'][0]['name']} "
                f"with {vram:.0f}MB VRAM"
            )
            
            if recommendation['device'] == 'cuda':
                recommendation['reasoning'].append(
                    f"Recommended model '{recommendation['model_size']}' will use approximately "
                    f"{self.MODEL_SPECS[recommendation['model_size']]['vram_mb']}MB VRAM"
                )
        else:
            recommendation['reasoning'].append(
                "No CUDA GPU detected, using CPU for inference"
            )
            recommendation['reasoning'].append(
                f"Model '{recommendation['model_size']}' selected for optimal CPU performance"
            )
        
        return recommendation