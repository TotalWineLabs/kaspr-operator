from marshmallow import fields, pre_load, post_dump
from kaspr.utils.helpers import camel_to_snake
from kaspr.types.base import BaseSchema
from kaspr.types.models import PodTemplate, AdditionalVolume
from kaspr.types.schemas.resource_template import ResourceTemplateSchema


class AdditionalVolumeSchema(BaseSchema):
    __model__ = AdditionalVolume
    name = fields.Str(required=True)
    secret = fields.Dict(
        keys=fields.String(),
        values=fields.String(),
        allow_none=True,
        load_default=dict,
        data_key="secret",
    )
    config_map = fields.Dict(
        keys=fields.String(),
        values=fields.String(),
        allow_none=True,
        load_default=dict,
        data_key="configMap",
    )
    empty_dir = fields.Dict(
        keys=fields.String(),
        values=fields.String(),
        allow_none=True,
        load_default=dict,
        data_key="emptyDir",
    )
    persistent_volume_claim = fields.Dict(
        keys=fields.String(),
        values=fields.String(),
        allow_none=True,
        load_default=dict,
        data_key="persistentVolumeClaim",
    )
    csi = fields.Dict(
        keys=fields.String(),
        values=fields.String(),
        allow_none=True,
        load_default=dict,
        data_key="csi",
    )


class PodTemplateSchema(ResourceTemplateSchema):
    __model__ = PodTemplate

    image_pull_secrets = fields.List(
        fields.Dict(keys=fields.String(), values=fields.String(), allow_none=False),
        data_key="imagePullSecrets",
        allow_none=True,
        load_default=list,
    )
    security_context = fields.Dict(
        keys=fields.String(),
        values=fields.String(),
        data_key="securityContext",
        allow_none=True,
        load_default=None
    )
    termination_grace_period_seconds = fields.Int(
        data_key="terminationGracePeriodSeconds", allow_none=True, load_default=None
    )
    affinity = fields.Dict(
        keys=fields.String(),
        values=fields.String(),
        data_key="affinity",
        allow_none=True,
        load_default=None
    )
    tolerations = fields.List(
        fields.Dict(keys=fields.String(), values=fields.String(), allow_none=False),
        data_key="tolerations",
        allow_none=True,
        load_default=list,
    )
    topology_spread_constraints = fields.List(
        fields.Dict(keys=fields.String(), values=fields.String(), allow_none=False),
        data_key="topologySpreadConstraints",
        allow_none=True,
        load_default=list,
    )
    priority_class_name = fields.Str(
        data_key="priorityClassName",
        allow_none=True,
        load_default=None,
    )
    scheduler_name = fields.Str(
        data_key="schedulerName",
        allow_none=True,
        load_default=None,
    )
    host_aliases = fields.List(
        fields.Dict(keys=fields.String(), values=fields.String(), allow_none=False),
        data_key="hostAliases",
        allow_none=True,
        load_default=list,
    )
    enable_service_links = fields.Bool(
        data_key="enableServiceLinks",
        allow_none=True,
        load_default=None,
    )
    volumes = fields.List(
        fields.Nested(AdditionalVolumeSchema()),
        data_key="volumes",
        allow_none=True,
        load_default=list,
    )

    @pre_load
    def make(self, data, **kwargs):
        if "metadata" not in data:
            data["metadata"] = {}
        return data
    
    @post_dump
    def camel_to_snake_dump(self, data, **kwargs):
        """Convert data keys from camelCase to snake_case."""
        return camel_to_snake(data)    
