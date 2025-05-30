import asyncio
import kopf
from logging import Logger
from collections import defaultdict
from typing import List, Dict
from kaspr.types.schemas.kasprapp_spec import (
    KasprAppSpecSchema,
)
from kaspr.types.models import KasprAppSpec
from kaspr.types.schemas import (
    KasprAgentSpecSchema,
    KasprWebViewSpecSchema,
    KasprTableSpecSchema,
)
from kaspr.resources import KasprApp, KasprAgent, KasprWebView, KasprTable
from kaspr.utils.helpers import utc_now

APP_KIND = "KasprApp"

AGENTS_UPDATED = "AgentsUpdated"
WEBVIEWS_UPDATED = "WebviewsUpdated"
TABLES_UPDATED = "TablesUpdated"

# Queue of requests to patch KasprApps
patch_request_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)


@kopf.on.resume(kind=APP_KIND)
@kopf.on.create(kind=APP_KIND)
def on_create(spec, name, namespace, logger, **kwargs):
    """Creates KasprApp resources."""
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    app.create()


@kopf.on.update(kind=APP_KIND, field="spec.image")
@kopf.on.update(kind=APP_KIND, field="spec.version")
def on_version_update(old, new, diff, spec, name, status, namespace, logger, **kwargs):
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    app.patch_version()


@kopf.on.update(kind=APP_KIND, field="spec.replicas")
def on_replicas_update(old, new, diff, spec, name, status, namespace, logger, **kwargs):
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    app.patch_replicas()


@kopf.on.update(kind=APP_KIND, field="spec.bootstrapServers")
@kopf.on.update(kind=APP_KIND, field="spec.tls")
@kopf.on.update(kind=APP_KIND, field="spec.authentication")
def on_kafka_credentials_update(
    old, new, diff, spec, name, status, namespace, logger, **kwargs
):
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    app.patch_kafka_credentials()


@kopf.on.update(kind=APP_KIND, field="spec.resources")
def on_resource_requirements_update(
    old, new, diff, spec, name, status, namespace, logger, **kwargs
):
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    app.patch_resource_requirements()


@kopf.on.update(kind=APP_KIND, field="spec.config.web_port")
def on_web_port_update(old, new, diff, spec, name, status, namespace, logger, **kwargs):
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    app.patch_web_port()


@kopf.on.update(kind=APP_KIND, field="spec.storage.deleteClaim")
def on_storage_delete_claim_update(
    old, new, diff, spec, name, status, namespace, logger, **kwargs
):
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    app.patch_storage_retention_policy()


@kopf.on.update(kind=APP_KIND, field="spec.storage.size")
def on_storage_size_update(
    old, new, diff, spec, name, status, namespace, logger, **kwargs
):
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    app.patch_storage_size()


@kopf.on.update(kind=APP_KIND, field="spec.template.serviceAccount")
def on_template_service_account_updated(
    old, new, diff, spec, name, status, namespace, logger, **kwargs
):
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    app.patch_template_service_account()


@kopf.on.update(kind=APP_KIND, field="spec.template.pod")
def on_template_pod_updated(
    old, new, diff, spec, name, status, namespace, logger, **kwargs
):
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    app.patch_template_pod()


@kopf.on.update(kind=APP_KIND, field="spec.template.service")
def on_template_service_updated(
    old, new, diff, spec, name, status, namespace, logger, **kwargs
):
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    app.patch_template_service()


@kopf.on.update(kind=APP_KIND, field="spec.config.topic_partitions")
def immutable_config_updated_00(**kwargs):
    raise kopf.PermanentError(
        "Field 'spec.config.topic_partitions' can't change after creation."
    )


@kopf.on.update(kind=APP_KIND, field="spec.config")
def general_config_update(spec, name, namespace, **kwargs):
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    app.patch_settings()
    # app_resources = KasprApp.default().search(namespace, apps=[name])
    # if app_resources and app_resources.get("items"):
    #     current = app_resources["items"][0]
    #     # TODO: Patch settings if desired generation # > current generation #


# @kopf.on.validate(kind=APP_KIND, field="spec.storage.deleteClaim")
# def say_hello(warnings: list[str], **_):
#     warnings.append("Verified with the operator's hook.")

# @kopf.on.validate(kind=APP_KIND)
# def validate_storage_class_change(spec, old, **kwargs):
#     if 'storage' in spec and 'storage' in old:
#         if spec['storage'].get('class') != old['storage'].get('class'):
#             raise kopf.AdmissionError("Changing the storage.class field is not allowed.")


@kopf.timer(APP_KIND, interval=1)
async def patch_resource(name, patch, **kwargs):
    """Update KasprApp status.

    Example usage:
    ```
        # Request to patch annotations
        await patch_request_queues[resource_name].put(
            {
                "field": "metadata.annotations",
                "value": {"kaspr.io/last-applied-agents-hash": "xyz"},
            }
        )
    ```

    Update multiple fields in one pass:
    ```
        # Request to patch annotations
        await patch_request_queues[resource_name].put(
            [
                {
                    "field": "metadata.annotations",
                    "value": {
                        "kaspr.io/last-applied-agents-hash": "xyz"
                    },
                },
                {
                    "field": "status",
                    "value": {
                        "agents": [{"name": "agent-1", "status": "running"}],
                    },
                },
            ]
        )
    ```
    """
    queue = patch_request_queues[name]

    def set_patch(request):
        fields = request["field"].split(".")
        _patch = patch
        for field in fields:
            _patch = getattr(_patch, field)
        _patch.update(request["value"])

    while not queue.empty():
        request = queue.get_nowait()
        if isinstance(request, list):
            for req in request:
                set_patch(req)
        else:
            set_patch(request)


@kopf.daemon(kind=APP_KIND, initial_delay=5.0)
async def monitor_related_resources(
    stopped,
    name,
    body,
    spec,
    meta,
    labels,
    annotations,
    status,
    namespace,
    patch,
    logger: Logger,
    **kwargs,
):
    """Monitor app's agents, webviews, and tables.

    On every iteration, the handler:
    1. Finds all agents, webviews, etc. related to the app.
    2. Determines if the app needs to be patched with updates to any resource.
    3. (Maybe) Patches the app with updated resources.
    4. Update app annotations & status with changes.
    """

    while not stopped:
        try:
            spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
            app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
            agents: List[KasprAgent] = []
            webviews: List[KasprWebView] = []
            tables: List[KasprTable] = []
            agent_resources = KasprAgent.default().search(namespace, apps=[name])
            webview_resources = KasprWebView.default().search(namespace, apps=[name])
            table_resources = KasprTable.default().search(namespace, apps=[name])
            for agent in agent_resources.get("items", []) if agent_resources else []:
                agents.append(
                    KasprAgent.from_spec(
                        agent["metadata"]["name"],
                        KasprAgent.KIND,
                        namespace,
                        KasprAgentSpecSchema().load(agent["spec"]),
                        dict(agent["metadata"]["labels"]),
                    )
                )
            for webview in (
                webview_resources.get("items", []) if webview_resources else []
            ):
                webviews.append(
                    KasprWebView.from_spec(
                        webview["metadata"]["name"],
                        KasprWebView.KIND,
                        namespace,
                        KasprWebViewSpecSchema().load(webview["spec"]),
                        dict(webview["metadata"]["labels"]),
                    )
                )
            for table in table_resources.get("items", []) if table_resources else []:
                tables.append(
                    KasprTable.from_spec(
                        table["metadata"]["name"],
                        KasprTable.KIND,
                        namespace,
                        KasprTableSpecSchema().load(table["spec"]),
                        dict(table["metadata"]["labels"]),
                    )
                )
            app.with_agents(agents)
            app.with_webviews(webviews)
            app.with_tables(tables)
            current_agents_hash, desired_agents_hash = (
                annotations.get("kaspr.io/last-applied-agents-hash"),
                app.agents_hash,
            )
            current_webviews_hash, desired_webviews_hash = (
                annotations.get("kaspr.io/last-applied-webviews-hash"),
                app.webviews_hash,
            )
            current_tables_hash, desired_tables_hash = (
                annotations.get("kaspr.io/last-applied-tables-hash"),
                app.tables_hash,
            )
            app.patch_volume_mounted_resources()
            # TODO: Update latest applied generation # in status
            # patch_requests = [
            #     {
            #         "field": "metadata.labels",
            #         "value": {app.KASPR_APP_NAME_LABEL: name},
            #     }
            # ]
            # if current_agents_hash != desired_agents_hash:
            #     patch_requests.extend(
            #         [
            #             {
            #                 "field": "metadata.annotations",
            #                 "value": {
            #                     "kaspr.io/last-applied-agents-hash": desired_agents_hash
            #                 },
            #             },
            #             {
            #                 "field": "status",
            #                 "value": {
            #                     "version": str(app.version),
            #                     "agents": {
            #                         "registered": app.agents_status(),
            #                         "lastTransitionTime": utc_now().isoformat(),
            #                         "hash": app.agents_hash,
            #                     },
            #                 },
            #             },
            #         ]
            #     )
            #     kopf.event(
            #         body,
            #         type="Normal",
            #         reason=AGENTS_UPDATED,
            #         message=f"Agents were updated for `{name}` in `{namespace or 'default'}` namespace.",
            #     )

            # if current_webviews_hash != desired_webviews_hash:
            #     patch_requests.extend(
            #         [
            #             {
            #                 "field": "metadata.annotations",
            #                 "value": {
            #                     "kaspr.io/last-applied-webviews-hash": desired_webviews_hash
            #                 },
            #             },
            #             {
            #                 "field": "status",
            #                 "value": {
            #                     "version": str(app.version),
            #                     "webviews": {
            #                         "registered": app.webviews_status(),
            #                         "lastTransitionTime": utc_now().isoformat(),
            #                         "hash": app.webviews_hash,
            #                     },
            #                 },
            #             },
            #         ]
            #     )
            #     kopf.event(
            #         body,
            #         type="Normal",
            #         reason=WEBVIEWS_UPDATED,
            #         message=f"Webviews were updated for `{name}` in `{namespace or 'default'}` namespace.",
            #     )

            # if current_tables_hash != desired_tables_hash:
            #     patch_requests.extend(
            #         [
            #             {
            #                 "field": "metadata.annotations",
            #                 "value": {
            #                     "kaspr.io/last-applied-tables-hash": desired_tables_hash
            #                 },
            #             },
            #             {
            #                 "field": "status",
            #                 "value": {
            #                     "version": str(app.version),
            #                     "tables": {
            #                         "registered": app.tables_status(),
            #                         "lastTransitionTime": utc_now().isoformat(),
            #                         "hash": app.tables_hash,
            #                     },
            #                 },
            #             },
            #         ]
            #     )
            #     kopf.event(
            #         body,
            #         type="Normal",
            #         reason=TABLES_UPDATED,
            #         message=f"Tables were updated for `{name}` in `{namespace or 'default'}` namespace.",
            #     )

            # await patch_request_queues[name].put(patch_requests)
            await asyncio.sleep(10)

        except asyncio.CancelledError:
            logger.info("Monitoring stopped.")
            break
        except Exception as e:
            logger.error("Unexpected error during monitoring: {e}")
            logger.exception(e)


@kopf.timer(APP_KIND, initial_delay=5.0, interval=30.0, backoff=10.0)
async def reconcile(name, spec, namespace, logger: Logger, **kwargs):
    """Reconcile KasprApp resources."""
    spec_model: KasprAppSpec = KasprAppSpecSchema().load(spec)
    app = KasprApp.from_spec(name, APP_KIND, namespace, spec_model)
    try:
        logger.debug(f"Reconciling {APP_KIND}/{name} in {namespace} namespace.")
        app.synchronize()
        logger.debug(f"Reconciled {APP_KIND}/{name} in {namespace} namespace.")
    except Exception as e:
        logger.error(f"Unexpected error during reconcilation: {e}")
        logger.exception(e)
