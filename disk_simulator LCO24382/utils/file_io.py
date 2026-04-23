import json

def save_state(disk, filename="disk_state.json"):
    """
    Save the current disk state to a JSON file.
    """
    state = {
        "size": disk.size,
        "blocks": disk.blocks,
        "files": disk.files
    }
    with open(filename, "w") as f:
        json.dump(state, f, indent=4)

def load_state(disk, filename="disk_state.json"):
    """
    Load disk state from a JSON file into the given disk object.
    """
    try:
        with open(filename, "r") as f:
            state = json.load(f)
        disk.size = state["size"]
        disk.blocks = state["blocks"]
        disk.files = state["files"]
    except FileNotFoundError:
        print("No saved state found.")
