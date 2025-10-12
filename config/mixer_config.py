"""
Mixer-specific configuration and protocol definitions.
"""
from typing import Dict, Any, List


# Mixer protocol configurations
MIXER_CONFIGS: Dict[str, Dict[str, Any]] = {
    "Qu 5/6/7": {
        "mute_protocol": "nrpn",
        "scene_protocol": "bank_select",
        "softkey_protocol": "cc",  # Using Note On/Off messages
        "nrpn_params": {
            "msb": 0x00,
            "mute_sequence": [99, 98, 6, 38]  # CC sequence for NRPN mute
        },
        "softkey_cc_params": {
            "base_note": 48,  # Note 48-59 (0x30-0x3B) for soft keys 1-12
            "max_keys": 12
        },
        "softkey_nrpn_params": {
            "msb": 0x01,  # Soft key parameter group (alternative protocol)
            "sequence": [99, 98, 6, 38]
        },
        "bank_select": {
            "msb": 0,
            "lsb": 0
        }
    },
    # Placeholder for future mixers
    # "Qu 16": {
    #     "mute_protocol": "nrpn",
    #     "scene_protocol": "bank_select",
    #     ...
    # },
    # "SQ 시리즈": {
    #     "mute_protocol": "cc",
    #     "scene_protocol": "program_change",
    #     ...
    # }
}


def get_mixer_config(mixer_name: str) -> Dict[str, Any]:
    """Get configuration for a specific mixer."""
    return MIXER_CONFIGS.get(mixer_name, {})


def get_supported_mixers() -> List[str]:
    """Get list of supported mixer names."""
    return list(MIXER_CONFIGS.keys())


def is_mixer_supported(mixer_name: str) -> bool:
    """Check if mixer is supported."""
    return mixer_name in MIXER_CONFIGS
