import asyncio
import kopf
import logging
from benedict import benedict
from kaspr.types.schemas import KasprAgentSpecSchema
from kaspr.types.models import KasprAgentSpec
from kaspr.resources import KasprAgent, KasprApp

KIND = "KasprAgent"
APP_NOT_FOUND = "AppNotFound"
APP_FOUND = "AppFound"

# Queue of requests to update KasprAgent status
status_updates_queue = asyncio.Queue()

class TimerLogFilter(logging.Filter):
    def filter(self, record):
        """Timer logs are noisy so we filter them out."""
        return "Timer " not in record.getMessage()
kopf_logger = logging.getLogger('kopf.objects')
kopf_logger.addFilter(TimerLogFilter())


@kopf.on.resume(kind=KIND)
@kopf.on.create(kind=KIND)
@kopf.on.update(kind=KIND)
def reconciliation(
    body, spec, name, namespace, logger, labels, patch, annotations, **kwargs
):
    """Reconcile KasprAgent resources."""
    spec_model: KasprAgentSpec = KasprAgentSpecSchema().load(spec)
    agent = KasprAgent.from_spec(name, KIND, namespace, spec_model, dict(labels))

    # Warn if the agent's app does not exists.
    app = KasprApp.default().fetch(agent.app_name, namespace)
    if app is None:
        kopf.warn(
            body,
            reason=APP_NOT_FOUND,
            message=f"KasprApp `{agent.app_name}` does not exist in `{namespace or 'default'}` namespace.",
        )

    agent.create()
    # fetch the agent's app and update it's status.
    patch.status.update(
        {
            "app": {
                "name": agent.app_name,
                "status": APP_FOUND if app else APP_NOT_FOUND,
            },
            "configMap": agent.config_map_name,
            "hash": agent.config_hash,
        }
    )


@kopf.timer(KIND, interval=1)
async def update_status(patch, **kwargs):
    """Update KasprAgent status."""
    while not status_updates_queue.empty():
        patch.status.update(status_updates_queue.get_nowait())


@kopf.daemon(
    kind=KIND, cancellation_backoff=2.0, cancellation_timeout=5.0, initial_delay=5.0
)
async def monitor_agent(
    stopped, name, body, spec, meta, labels, status, namespace, patch, logger, **kwargs
):
    """Monitor agent resources for status updates."""
    try:
        while not stopped:
            _status = benedict(status, keyattr_dynamic=True)
            _status_updates = benedict(keyattr_dynamic=True)
            spec_model: KasprAgentSpec = KasprAgentSpecSchema().load(spec)
            agent = KasprAgent.from_spec(
                name, KIND, namespace, spec_model, dict(labels)
            )
            # Warn if the agent's app does not exists.
            app = KasprApp.default().fetch(agent.app_name, namespace)
            if app is None and _status.app.status == APP_FOUND:
                kopf.warn(
                    body,
                    reason=APP_NOT_FOUND,
                    message=f"KasprApp `{agent.app_name}` does not exist in `{namespace or 'default'}` namespace.",
                )
                _status_updates.app.status = APP_NOT_FOUND
            elif app and _status.app.status == APP_NOT_FOUND:
                kopf.event(
                    body,
                    type="Normal",
                    reason=APP_FOUND,
                    message=f"KasprApp `{agent.app_name}` found in `{namespace or 'default'}` namespace.",
                )
                _status_updates.app.status = APP_FOUND

            if _status_updates:
                await status_updates_queue.put(_status_updates)

            await asyncio.sleep(10)
    except asyncio.CancelledError:
        print("We are done. Bye.")


# @kopf.on.validate(kind=KIND)
# def includes_valid_app(spec, **_):
#     raise kopf.AdmissionError("Missing required label `kaspr.io/app`", code=429)

# @kopf.on.delete(kind=KIND)
# def on_delete(name, namespace, logger, **kwargs):
#     """Delete KasprAgent resources."""
#     agent = KasprAgent(name, KIND, namespace)
#     agent.delete()

# @kopf.daemon(KIND, cancellation_timeout=5.0)
# async def monitor_kex(**kwargs):
#     try:
#         while True:
#             print("Monitoring KEX")
#             await asyncio.sleep(10)
#     except asyncio.CancelledError:
#         print("We are done. Bye.")
