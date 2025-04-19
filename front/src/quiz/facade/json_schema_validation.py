from jsonschema import validate, ValidationError


def validate_requirements(requirements):
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "network_config": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {
                                "ip_private": {"type": "boolean"},
                                "points": {"type": "integer", "minimum": 1},
                            },
                            "required": ["ip_private", "points"],
                            "additionalProperties": False,
                        },
                        {
                            "type": "object",
                            "properties": {
                                "vlan_id_above": {"type": "integer", "minimum": 1},
                                "points": {"type": "integer", "minimum": 1},
                            },
                            "required": ["vlan_id_above", "points"],
                            "additionalProperties": False,
                        },
                    ]
                }
            },
            "patternProperties": {
                "^(host|router|server)_\\d+$": {
                    "type": "object",
                    "anyOf": [
                        {"required": ["cmd"]},
                        {"required": ["ip_check"]},
                        {"required": ["mask_check"]},
                        {"required": ["equal_vlan_id"]},
                        {"required": ["no_equal_vlan_id"]},
                        {"required": ["default_gw"]},
                        {"required": ["ip_equal"]},
                    ],
                    "properties": {
                        "cmd": {
                            "type": "object",
                            "properties": {
                                "echo-request": {"type": "string"},
                                "direction": {
                                    "type": "string",
                                    "enum": ["one-way", "two-way"],
                                },
                                "different_paths": {
                                    "type": "object",
                                    "properties": {
                                        "points": {"type": "integer", "minimum": 1}
                                    },
                                    "required": ["points"],
                                    "additionalProperties": False,
                                },
                                "points": {"type": "integer", "minimum": 1},
                                "path": {
                                    "type": "object",
                                    "properties": {
                                        "required_path": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "minItems": 1,
                                        },
                                        "points": {"type": "integer", "minimum": 1},
                                    },
                                    "required": ["required_path", "points"],
                                    "additionalProperties": False,
                                },
                            },
                            "required": ["echo-request", "points"],
                            "additionalProperties": False,
                        },
                        "ip_check": {
                            "type": "object",
                            "properties": {
                                "to": {"type": "string"},
                                "points": {"type": "integer", "minimum": 1},
                            },
                            "required": ["to", "points"],
                            "additionalProperties": False,
                        },
                        "mask_check": {
                            "type": "object",
                            "properties": {
                                "to": {"type": "string"},
                                "subnet_mask": {"type": "integer", "minimum": 1},
                                "points": {"type": "integer", "minimum": 1},
                            },
                            "required": ["to", "points", "subnet_mask"],
                            "additionalProperties": False,
                        },
                        "equal_vlan_id": {
                            "type": "object",
                            "properties": {
                                "targets": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "minItems": 1,
                                },
                                "points": {"type": "integer", "minimum": 1},
                            },
                            "required": ["targets", "points"],
                            "additionalProperties": False,
                        },
                        "no_equal_vlan_id": {
                            "type": "object",
                            "properties": {
                                "targets": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "minItems": 1,
                                },
                                "points": {"type": "integer", "minimum": 1},
                            },
                            "required": ["targets", "points"],
                            "additionalProperties": False,
                        },
                        "default_gw": {
                            "type": "object",
                            "properties": {"points": {"type": "integer", "minimum": 1}},
                            "required": ["points"],
                            "additionalProperties": False,
                        },
                        "ip_equal": {
                            "type": "object",
                            "properties": {
                                "to": {"type": "string"},
                                "expected_ip": {"type": "string", "format": "ipv4"},
                                "points": {"type": "integer", "minimum": 1},
                            },
                            "required": ["to", "expected_ip", "points"],
                            "additionalProperties": False,
                        },
                    },
                    "additionalProperties": False,
                }
            },
            "additionalProperties": False,
        },
    }

    try:
        validate(instance=requirements, schema=schema)
        return True
    except ValidationError as e:
        return f"Ошибка валидации: {e.message}"
