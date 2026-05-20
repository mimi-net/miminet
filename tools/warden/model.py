def build_model_uri(folder_id: str, model_name: str) -> str:
    if model_name.startswith("gpt://"):
        return model_name
    return f"gpt://{folder_id}/{model_name}"
