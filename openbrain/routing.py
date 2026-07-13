from openbrain.utils import estimate_difficulty


def pick_model(question_text: str, cfg) -> str:
    if not cfg.routing_enabled:
        return cfg.easy_model
    difficulty = estimate_difficulty(
        question_text, cfg.routing_word_threshold, cfg.routing_keyword_boost
    )
    return cfg.hard_model if difficulty == "hard" else cfg.easy_model
