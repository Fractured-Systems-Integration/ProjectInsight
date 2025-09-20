def export_to_file(filepath, text_data):
    try:
        with open(filepath, 'w') as f:
            f.write(text_data)
    except Exception as e:
        raise IOError(f"Failed to save file: {e}")
