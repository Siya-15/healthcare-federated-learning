import random


def weighted_choice(items, weights):

    return random.choices(
        population=items,
        weights=weights,
        k=1
    )[0]