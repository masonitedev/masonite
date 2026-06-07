from sqids import Sqids


def _decode(hash_class, value):
    """Decode a hash and verify it by re-encoding.

    Unlike hashids, Sqids decoding alone is not canonical — any string made
    of alphabet characters decodes to *some* numbers — so the round-trip
    check is what tells real hashes apart from arbitrary input.
    """
    if not isinstance(value, str) or not value:
        return ()
    numbers = hash_class.decode(value)
    if numbers and hash_class.encode(numbers) == value:
        return tuple(numbers)
    return ()


def hashid(*values, decode=False, min_length=7):
    hash_class = Sqids(min_length=min_length)
    if isinstance(values[0], dict) and decode:
        new_dict = {}
        for key, value in values[0].items():
            if hasattr(value, "value"):
                value = value.value

            decoded = _decode(hash_class, value)
            if decoded:
                value = decoded

            if isinstance(value, tuple):
                value = value[0]
            new_dict.update({key: value})
        return new_dict

    if not decode:
        if isinstance(values[0], dict):
            new_dic = {}
            for key, value in values[0].items():
                if hasattr(value, "value"):
                    value = value.value
                if str(value).isdigit():
                    new_dic.update({key: hash_class.encode([int(value)])})
                else:
                    new_dic.update({key: value})
            return new_dic

        return hash_class.encode(list(values))

    return _decode(hash_class, values[0])
