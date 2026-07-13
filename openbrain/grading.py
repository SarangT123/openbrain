def grade_answer(model_answer, correct_answer) -> bool:
    try:
        return int(model_answer) == int(correct_answer)
    except (TypeError, ValueError):
        return False
