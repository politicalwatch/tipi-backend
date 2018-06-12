def get_unique_values(model, field):
    values = model.objects().distinct(field)
    if '' in values:
        values.remove('')
    return sorted(values)
