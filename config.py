import json

CONFIG_FILE = "config.json"


def load_config():
    """Load configuration from JSON file."""
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)


def save_config(data):
    """Save updated configuration to JSON file."""
    with open(CONFIG_FILE, "w") as file:
        json.dump(data, file, indent=4)


def get_config():
    """Get the current configuration from JSON file."""
    return load_config()


def get_config_value(key):
    """Get the value of a specific key from the JSON config file."""
    config_data = load_config()
    if key in config_data:
        return config_data[key]
    else:
        return {"error": f"Key '{key}' not found"}


def update_config_value(key, value):
    """Update the value of a specific key in the JSON config file."""
    config_data = load_config()

    config_data[key] = value
    save_config(config_data)

    return {"message": f"Updated {key}!", key: config_data[key]}
