import kopf
import logging
import kaspr.handlers.kasprapp as kasprapp
import kaspr.handlers.kaspragent as kaspragent
import kaspr.handlers.kasprwebview as kasprwebview

# Configure Kopf settings
@kopf.on.startup()
def configure_settings(settings: kopf.OperatorSettings, **kwargs):
    # Limit the number of concurrent workers to prevent flooding the API
    settings.batching.worker_limit = 2
    
    # Disable posting events to the Kubernetes API for logging > Warning
    settings.posting.enabled = True
    settings.posting.level = logging.WARNING

__all__ = [
    "kasprapp",
    "kaspragent",
    "kasprwebview",
]